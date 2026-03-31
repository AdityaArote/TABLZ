"""
TABLZ — OrderService: order creation with idempotency, price snapshotting,
server-enforced state machine, bill finalization.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import bleach
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, VALID_ORDER_TRANSITIONS
from app.models.order_item import OrderItem
from app.models.menu_item import MenuItem
from app.models.customer_session import CustomerSession
from app.models.audit_log import AuditLog
from app.core.security import generate_barcode_token
from app.core.errors import AppException, ErrorCode
from app.core.rate_limit import check_idempotency_key, set_idempotency_key


class OrderService:

    @staticmethod
    def _sanitize(text: str | None) -> str | None:
        if text is None:
            return None
        return bleach.clean(text, tags=[], strip=True).strip()

    @staticmethod
    async def create_order(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        table_id: uuid.UUID,
        session_id: uuid.UUID,
        items_data: list[dict],
        special_requests: str | None = None,
        idempotency_key: str | None = None,
    ) -> Order:
        """
        Create an order with:
        - Idempotency key support (returns existing order on duplicate)
        - Price snapshot at order time
        - Cross-restaurant item injection blocked
        - Input sanitization
        """
        # Check idempotency
        if idempotency_key:
            existing_order_id = await check_idempotency_key(idempotency_key)
            if existing_order_id:
                result = await db.execute(
                    select(Order).where(Order.id == uuid.UUID(existing_order_id))
                )
                existing = result.scalar_one_or_none()
                if existing:
                    return existing

        # Validate and snapshot all menu items
        order_items = []
        total_amount = Decimal("0")

        for item_data in items_data:
            menu_item_id = item_data["menu_item_id"]
            quantity = item_data["quantity"]

            # Fetch menu item — MUST belong to same restaurant
            result = await db.execute(
                select(MenuItem).where(
                    MenuItem.id == menu_item_id,
                    MenuItem.restaurant_id == restaurant_id,
                    MenuItem.is_deleted == False,
                    MenuItem.is_available == True,
                )
            )
            menu_item = result.scalar_one_or_none()

            if not menu_item:
                raise AppException(
                    code=ErrorCode.RESOURCE_NOT_FOUND,
                    message=f"Menu item {menu_item_id} not found or unavailable",
                    http_status=404,
                )

            # Snapshot price at order time
            unit_price = Decimal(str(menu_item.price))
            line_total = unit_price * quantity
            total_amount += line_total

            order_items.append(OrderItem(
                id=uuid.uuid4(),
                menu_item_id=menu_item.id,
                quantity=quantity,
                unit_price_at_order=float(unit_price),
                item_notes=OrderService._sanitize(item_data.get("item_notes")),
            ))

        # Create order
        order = Order(
            id=uuid.uuid4(),
            restaurant_id=restaurant_id,
            table_id=table_id,
            session_id=session_id,
            status="pending",
            special_requests=OrderService._sanitize(special_requests),
            total_amount=float(total_amount),
            tax_amount=0,  # Tax computed separately if tax_config exists
        )

        # Attach items
        for oi in order_items:
            oi.order_id = order.id

        db.add(order)
        db.add_all(order_items)

        # Audit
        audit = AuditLog(
            restaurant_id=restaurant_id,
            actor_type="customer",
            actor_id=str(session_id),
            action="order.created",
            resource_type="order",
            resource_id=order.id,
            metadata_json={"item_count": len(order_items), "total": float(total_amount)},
        )
        db.add(audit)

        await db.commit()
        await db.refresh(order)

        # Store idempotency key
        if idempotency_key:
            await set_idempotency_key(idempotency_key, str(order.id))

        return order

    @staticmethod
    async def get_order(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        order_id: uuid.UUID,
    ) -> Order:
        """Get a single order (restaurant-scoped)."""
        result = await db.execute(
            select(Order).where(
                Order.id == order_id,
                Order.restaurant_id == restaurant_id,
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise AppException(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Order not found",
                http_status=404,
            )
        return order

    @staticmethod
    async def list_orders(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        status: str | None = None,
        table_id: uuid.UUID | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List orders with filters."""
        from sqlalchemy import func

        query = select(Order).where(Order.restaurant_id == restaurant_id)

        if status:
            query = query.where(Order.status == status)
        if table_id:
            query = query.where(Order.table_id == table_id)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Order.placed_at.desc())
        result = await db.execute(query)
        orders = result.scalars().all()

        return {"orders": orders, "total": total, "page": page, "limit": limit}

    @staticmethod
    async def update_status(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        order_id: uuid.UUID,
        new_status: str,
        actor_id: str = "",
        actor_type: str = "admin",
    ) -> Order:
        """Update order status with state machine validation."""
        order = await OrderService.get_order(db, restaurant_id, order_id)

        if not order.can_transition_to(new_status):
            allowed = VALID_ORDER_TRANSITIONS.get(order.status, [])
            raise AppException(
                code=ErrorCode.ORDER_INVALID_TRANSITION,
                message=f"Cannot transition order from '{order.status}' to '{new_status}'",
                http_status=409,
                suggestion=f"Valid transitions: {allowed}",
            )

        old_status = order.status
        order.status = new_status

        audit = AuditLog(
            restaurant_id=restaurant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action="order.status_changed",
            resource_type="order",
            resource_id=order.id,
            metadata_json={"old_status": old_status, "new_status": new_status},
        )
        db.add(audit)

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def finalize_bill(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        order_id: uuid.UUID,
        actor_id: str = "",
    ) -> Order:
        """Finalize an order bill — generate barcode, lock modifications."""
        order = await OrderService.get_order(db, restaurant_id, order_id)

        if order.is_finalized:
            raise AppException(
                code=ErrorCode.ORDER_INVALID_TRANSITION,
                message="Order is already finalized",
                http_status=409,
            )

        if order.status not in ("served", "ready"):
            raise AppException(
                code=ErrorCode.ORDER_INVALID_TRANSITION,
                message="Order must be 'served' or 'ready' before finalization",
                http_status=409,
            )

        order.is_finalized = True
        order.barcode_token = generate_barcode_token()
        order.finalized_at = datetime.now(timezone.utc)

        audit = AuditLog(
            restaurant_id=restaurant_id,
            actor_type="admin",
            actor_id=actor_id,
            action="order.finalized",
            resource_type="order",
            resource_id=order.id,
            metadata_json={"barcode_token": order.barcode_token},
        )
        db.add(audit)

        await db.commit()
        await db.refresh(order)
        return order
