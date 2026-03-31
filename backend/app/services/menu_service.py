"""
TABLZ — MenuService: CRUD, soft-delete, sanitization, availability toggle, tier limits.
"""

import uuid
from datetime import datetime, timezone

import bleach
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.menu_item import MenuItem
from app.models.audit_log import AuditLog
from app.core.errors import AppException, ErrorCode

# Tier limits for menu items
TIER_MENU_LIMITS = {
    "free": 50,
    "premium": 200,
    "vip": 500,
    "luxury": None,  # unlimited
}


class MenuService:

    @staticmethod
    def _sanitize(text: str | None) -> str | None:
        """Sanitize HTML input via bleach."""
        if text is None:
            return None
        return bleach.clean(text, tags=[], strip=True).strip()

    @staticmethod
    async def list_items(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        category: str | None = None,
        dietary_type: str | None = None,
        cuisine: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List menu items with optional filters and pagination."""
        query = select(MenuItem).where(
            MenuItem.restaurant_id == restaurant_id,
            MenuItem.is_deleted == False,
        )

        if category:
            query = query.where(MenuItem.category == category)
        if dietary_type:
            query = query.where(MenuItem.dietary_type == dietary_type)
        if cuisine:
            query = query.where(MenuItem.cuisine == cuisine)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(MenuItem.name)
        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
        }

    @staticmethod
    async def get_item(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        item_id: uuid.UUID,
    ) -> MenuItem:
        """Get a single menu item by ID (restaurant-scoped)."""
        result = await db.execute(
            select(MenuItem).where(
                MenuItem.id == item_id,
                MenuItem.restaurant_id == restaurant_id,
                MenuItem.is_deleted == False,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise AppException(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Menu item not found",
                http_status=404,
            )
        return item

    @staticmethod
    async def create_item(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        subscription_tier: str,
        data: dict,
        actor_id: str,
    ) -> MenuItem:
        """Create a menu item with tier limit enforcement and input sanitization."""
        # Check tier limit
        max_items = TIER_MENU_LIMITS.get(subscription_tier)
        if max_items is not None:
            count_result = await db.execute(
                select(func.count(MenuItem.id)).where(
                    MenuItem.restaurant_id == restaurant_id,
                    MenuItem.is_deleted == False,
                )
            )
            current_count = count_result.scalar() or 0
            if current_count >= max_items:
                raise AppException(
                    code=ErrorCode.SUBSCRIPTION_LIMIT_EXCEEDED,
                    message=f"Menu item limit reached ({max_items} for {subscription_tier} tier)",
                    http_status=402,
                    suggestion="Upgrade your subscription to add more items",
                )

        # Sanitize text inputs
        item = MenuItem(
            id=uuid.uuid4(),
            restaurant_id=restaurant_id,
            name=MenuService._sanitize(data["name"]),
            description=MenuService._sanitize(data.get("description")),
            price=data["price"],
            category=data["category"],
            cuisine=MenuService._sanitize(data.get("cuisine")),
            dietary_type=data["dietary_type"],
            is_daily_special=data.get("is_daily_special", False),
            is_weekly_special=data.get("is_weekly_special", False),
            prep_time_minutes=data.get("prep_time_minutes", 15),
        )
        db.add(item)

        # Audit log
        audit = AuditLog(
            restaurant_id=restaurant_id,
            actor_type="admin",
            actor_id=actor_id,
            action="menu_item.created",
            resource_type="menu_item",
            resource_id=item.id,
        )
        db.add(audit)

        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def update_item(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        item_id: uuid.UUID,
        data: dict,
        actor_id: str,
    ) -> MenuItem:
        """Update a menu item (partial update)."""
        item = await MenuService.get_item(db, restaurant_id, item_id)

        # Apply updates with sanitization
        for field, value in data.items():
            if value is not None:
                if field in ("name", "description", "cuisine"):
                    value = MenuService._sanitize(value)
                setattr(item, field, value)

        # Audit
        audit = AuditLog(
            restaurant_id=restaurant_id,
            actor_type="admin",
            actor_id=actor_id,
            action="menu_item.updated",
            resource_type="menu_item",
            resource_id=item.id,
        )
        db.add(audit)

        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def toggle_availability(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        item_id: uuid.UUID,
        is_available: bool,
        actor_id: str,
    ) -> MenuItem:
        """Toggle item availability (86'd / back in stock)."""
        item = await MenuService.get_item(db, restaurant_id, item_id)
        item.is_available = is_available

        audit = AuditLog(
            restaurant_id=restaurant_id,
            actor_type="admin",
            actor_id=actor_id,
            action=f"menu_item.{'enabled' if is_available else 'disabled'}",
            resource_type="menu_item",
            resource_id=item.id,
        )
        db.add(audit)

        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def soft_delete(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        item_id: uuid.UUID,
        actor_id: str,
    ) -> None:
        """Soft-delete a menu item (set is_deleted = True)."""
        item = await MenuService.get_item(db, restaurant_id, item_id)
        item.is_deleted = True
        item.deleted_at = datetime.now(timezone.utc)

        audit = AuditLog(
            restaurant_id=restaurant_id,
            actor_type="admin",
            actor_id=actor_id,
            action="menu_item.deleted",
            resource_type="menu_item",
            resource_id=item.id,
        )
        db.add(audit)

        await db.commit()
