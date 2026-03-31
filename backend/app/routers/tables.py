"""
TABLZ — Tables router: creation, status management, QR info, cleaning flow.
All endpoints scoped by restaurant_id from JWT.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_restaurant
from app.schemas.table import TableCreate, TableResponse
from app.schemas.common import SuccessResponse
from app.services.table_service import TableService
from app.models.restaurant import Restaurant

router = APIRouter(prefix="/api/v1/tables", tags=["Tables"])


@router.get("")
async def list_tables(
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """List all tables."""
    tables = await TableService.list_tables(db, restaurant.id)
    return SuccessResponse(
        success=True,
        data=[TableResponse.model_validate(t) for t in tables],
    )


@router.get("/{table_id}")
async def get_table(
    table_id: UUID,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Get a single table."""
    table = await TableService.get_table(db, restaurant.id, table_id)
    return SuccessResponse(
        success=True,
        data=TableResponse.model_validate(table),
    )


@router.post("", status_code=201)
async def create_table(
    body: TableCreate,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Create a table with QR code (tier-limited)."""
    table = await TableService.create_table(
        db=db,
        restaurant_id=restaurant.id,
        subscription_tier=restaurant.subscription_tier,
        table_number=body.table_number,
        max_capacity=body.max_capacity,
        is_expandable=body.is_expandable,
        actor_id=restaurant.admin_id,
    )
    return SuccessResponse(
        success=True,
        data=TableResponse.model_validate(table),
    )


@router.post("/{table_id}/clean")
async def mark_table_cleaning(
    table_id: UUID,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Mark a table as cleaning."""
    table = await TableService.mark_cleaning(
        db=db,
        restaurant_id=restaurant.id,
        table_id=table_id,
        actor_id=restaurant.admin_id,
    )
    return SuccessResponse(
        success=True,
        data=TableResponse.model_validate(table),
    )


@router.get("/{table_id}/qr")
async def get_table_qr(
    table_id: UUID,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Get QR code info for a table."""
    qr_info = await TableService.get_qr_info(db, restaurant.id, table_id)
    return SuccessResponse(success=True, data=qr_info)
