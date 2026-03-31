"""
TABLZ — Menu router: CRUD, availability toggle, soft-delete.
All endpoints scoped by restaurant_id from JWT.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_restaurant
from app.schemas.menu import (
    MenuItemCreate,
    MenuItemUpdate,
    MenuItemAvailability,
    MenuItemResponse,
)
from app.schemas.common import SuccessResponse
from app.services.menu_service import MenuService
from app.models.restaurant import Restaurant

router = APIRouter(prefix="/api/v1/menu", tags=["Menu"])


@router.get("")
async def list_menu_items(
    category: str | None = Query(None),
    dietary_type: str | None = Query(None),
    cuisine: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """List menu items with optional filters."""
    result = await MenuService.list_items(
        db=db,
        restaurant_id=restaurant.id,
        category=category,
        dietary_type=dietary_type,
        cuisine=cuisine,
        page=page,
        limit=limit,
    )
    return SuccessResponse(
        success=True,
        data={
            "items": [MenuItemResponse.model_validate(i) for i in result["items"]],
            "total": result["total"],
            "page": result["page"],
            "limit": result["limit"],
        },
    )


@router.get("/{item_id}")
async def get_menu_item(
    item_id: UUID,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Get a single menu item."""
    item = await MenuService.get_item(db, restaurant.id, item_id)
    return SuccessResponse(
        success=True,
        data=MenuItemResponse.model_validate(item),
    )


@router.post("", status_code=201)
async def create_menu_item(
    body: MenuItemCreate,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Create a menu item (tier-limited)."""
    item = await MenuService.create_item(
        db=db,
        restaurant_id=restaurant.id,
        subscription_tier=restaurant.subscription_tier,
        data=body.model_dump(),
        actor_id=restaurant.admin_id,
    )
    return SuccessResponse(
        success=True,
        data=MenuItemResponse.model_validate(item),
    )


@router.put("/{item_id}")
async def update_menu_item(
    item_id: UUID,
    body: MenuItemUpdate,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Update a menu item (partial)."""
    item = await MenuService.update_item(
        db=db,
        restaurant_id=restaurant.id,
        item_id=item_id,
        data=body.model_dump(exclude_unset=True),
        actor_id=restaurant.admin_id,
    )
    return SuccessResponse(
        success=True,
        data=MenuItemResponse.model_validate(item),
    )


@router.patch("/{item_id}/availability")
async def toggle_availability(
    item_id: UUID,
    body: MenuItemAvailability,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Toggle item availability."""
    item = await MenuService.toggle_availability(
        db=db,
        restaurant_id=restaurant.id,
        item_id=item_id,
        is_available=body.is_available,
        actor_id=restaurant.admin_id,
    )
    return SuccessResponse(
        success=True,
        data=MenuItemResponse.model_validate(item),
    )


@router.delete("/{item_id}")
async def delete_menu_item(
    item_id: UUID,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a menu item."""
    await MenuService.soft_delete(
        db=db,
        restaurant_id=restaurant.id,
        item_id=item_id,
        actor_id=restaurant.admin_id,
    )
    return SuccessResponse(success=True, message="Menu item deleted")
