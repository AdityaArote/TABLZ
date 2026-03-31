"""
TABLZ — Orders router: order CRUD, status updates, bill finalization.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_restaurant, get_current_session
from app.schemas.order import (
    OrderCreate,
    OrderStatusUpdate,
    OrderResponse,
    QrSessionRequest,
    QrSessionResponse,
)
from app.schemas.common import SuccessResponse
from app.services.order_service import OrderService
from app.services.session_service import SessionService
from app.models.restaurant import Restaurant
from app.models.customer_session import CustomerSession
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["Orders"])


# ─── QR Session (placed under /auth but grouped here for context) ───

@router.post("/auth/qr-session", status_code=201, tags=["Authentication"])
async def create_qr_session(
    response: Response,
    body: QrSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a customer session from QR scan."""
    result = await SessionService.create_qr_session(
        db=db,
        qr_code_token=body.qr_code_token,
        device_fingerprint=body.device_fingerprint,
    )

    # Set session token as HttpOnly cookie
    response.set_cookie(
        key="session_token",
        value=result["session_token"],
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="strict",
        max_age=4 * 3600,  # 4 hours
        path="/",
    )

    return SuccessResponse(
        success=True,
        data={
            "table_id": result["table_id"],
            "table_number": result["table_number"],
            "restaurant_name": result["restaurant_name"],
            "is_table_owner": result["is_table_owner"],
        },
    )


# ─── Customer-facing order endpoints ───

@router.post("/orders", status_code=201)
async def create_order(
    body: OrderCreate,
    session: CustomerSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """Place a new order (customer session required)."""
    order = await OrderService.create_order(
        db=db,
        restaurant_id=session.restaurant_id,
        table_id=session.table_id,
        session_id=session.id,
        items_data=[item.model_dump() for item in body.items],
        special_requests=body.special_requests,
        idempotency_key=idempotency_key,
    )
    return SuccessResponse(
        success=True,
        data=OrderResponse.model_validate(order),
    )


# ─── Admin/staff order management ───

@router.get("/orders")
async def list_orders(
    status: str | None = Query(None),
    table_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """List orders with filters (admin)."""
    result = await OrderService.list_orders(
        db=db,
        restaurant_id=restaurant.id,
        status=status,
        table_id=table_id,
        page=page,
        limit=limit,
    )
    return SuccessResponse(
        success=True,
        data={
            "orders": [OrderResponse.model_validate(o) for o in result["orders"]],
            "total": result["total"],
            "page": result["page"],
            "limit": result["limit"],
        },
    )


@router.get("/orders/{order_id}")
async def get_order(
    order_id: UUID,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Get a single order (admin)."""
    order = await OrderService.get_order(db, restaurant.id, order_id)
    return SuccessResponse(
        success=True,
        data=OrderResponse.model_validate(order),
    )


@router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: UUID,
    body: OrderStatusUpdate,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Update order status (admin/chef). State machine enforced."""
    order = await OrderService.update_status(
        db=db,
        restaurant_id=restaurant.id,
        order_id=order_id,
        new_status=body.status,
        actor_id=restaurant.admin_id,
    )
    return SuccessResponse(
        success=True,
        data=OrderResponse.model_validate(order),
    )


@router.post("/orders/{order_id}/finalize")
async def finalize_bill(
    order_id: UUID,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Finalize an order bill — generate barcode, lock order."""
    order = await OrderService.finalize_bill(
        db=db,
        restaurant_id=restaurant.id,
        order_id=order_id,
        actor_id=restaurant.admin_id,
    )
    return SuccessResponse(
        success=True,
        data={
            "order_id": str(order.id),
            "barcode_token": order.barcode_token,
            "total_amount": order.total_amount,
            "tax_amount": order.tax_amount,
            "finalized_at": order.finalized_at.isoformat() if order.finalized_at else None,
        },
    )
