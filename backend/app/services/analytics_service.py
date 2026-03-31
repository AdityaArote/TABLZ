"""
TABLZ — AnalyticsService: revenue summary, popular items, occupancy metrics.
Tier-enforced date ranges.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.menu_item import MenuItem
from app.models.table import Table
from app.core.errors import AppException, ErrorCode

# Tier-enforced date range limits (in days)
TIER_DATE_RANGE = {
    "free": 7,
    "premium": 90,
    "vip": 365,
    "luxury": None,  # unlimited
}


class AnalyticsService:

    @staticmethod
    async def get_summary(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        subscription_tier: str = "free",
    ) -> dict:
        """Get revenue summary with tier-enforced date ranges."""
        # Enforce date range
        now = datetime.now(timezone.utc)
        max_days = TIER_DATE_RANGE.get(subscription_tier)

        if start_date is None:
            start_date = now - timedelta(days=7)
        if end_date is None:
            end_date = now

        if max_days is not None:
            earliest_allowed = now - timedelta(days=max_days)
            if start_date < earliest_allowed:
                start_date = earliest_allowed

        # Revenue + order count
        revenue_query = select(
            func.coalesce(func.sum(Order.total_amount), 0).label("total_revenue"),
            func.count(Order.id).label("order_count"),
        ).where(
            Order.restaurant_id == restaurant_id,
            Order.placed_at >= start_date,
            Order.placed_at <= end_date,
            Order.status != "cancelled",
        )

        result = await db.execute(revenue_query)
        row = result.one()

        total_revenue = float(row.total_revenue)
        order_count = row.order_count
        avg_order_value = total_revenue / order_count if order_count > 0 else 0

        return {
            "daily_revenue": total_revenue,
            "order_count": order_count,
            "avg_order_value": round(avg_order_value, 2),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        }

    @staticmethod
    async def get_popular_items(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        days: int = 7,
        limit: int = 10,
    ) -> list[dict]:
        """Get top items by order count."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(
                MenuItem.id,
                MenuItem.name,
                MenuItem.category,
                func.count(OrderItem.id).label("order_count"),
                func.sum(OrderItem.unit_price_at_order * OrderItem.quantity).label("revenue"),
            )
            .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.restaurant_id == restaurant_id,
                Order.placed_at >= since,
                Order.status != "cancelled",
            )
            .group_by(MenuItem.id, MenuItem.name, MenuItem.category)
            .order_by(func.count(OrderItem.id).desc())
            .limit(limit)
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "id": str(row.id),
                "name": row.name,
                "category": row.category,
                "order_count": row.order_count,
                "revenue": float(row.revenue or 0),
            }
            for row in rows
        ]

    @staticmethod
    async def get_occupancy(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
    ) -> dict:
        """Get current table occupancy rate."""
        total_result = await db.execute(
            select(func.count(Table.id)).where(
                Table.restaurant_id == restaurant_id,
            )
        )
        total_tables = total_result.scalar() or 0

        occupied_result = await db.execute(
            select(func.count(Table.id)).where(
                Table.restaurant_id == restaurant_id,
                Table.status == "occupied",
            )
        )
        occupied_tables = occupied_result.scalar() or 0

        occupancy_pct = (occupied_tables / total_tables * 100) if total_tables > 0 else 0

        return {
            "total_tables": total_tables,
            "occupied_tables": occupied_tables,
            "occupancy_rate_pct": round(occupancy_pct, 1),
        }
