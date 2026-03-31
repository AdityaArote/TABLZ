"""
TABLZ — Analytics router: revenue, popular items, occupancy.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_restaurant
from app.schemas.common import SuccessResponse
from app.services.analytics_service import AnalyticsService
from app.models.restaurant import Restaurant

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/summary")
async def get_summary(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Revenue + order summary (tier-limited date range)."""
    data = await AnalyticsService.get_summary(
        db=db,
        restaurant_id=restaurant.id,
        start_date=start_date,
        end_date=end_date,
        subscription_tier=restaurant.subscription_tier,
    )
    return SuccessResponse(success=True, data=data)


@router.get("/popular-items")
async def get_popular_items(
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Top items by order count."""
    data = await AnalyticsService.get_popular_items(
        db=db,
        restaurant_id=restaurant.id,
        days=days,
        limit=limit,
    )
    return SuccessResponse(success=True, data=data)


@router.get("/occupancy")
async def get_occupancy(
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Current table occupancy rate."""
    data = await AnalyticsService.get_occupancy(
        db=db,
        restaurant_id=restaurant.id,
    )
    return SuccessResponse(success=True, data=data)
