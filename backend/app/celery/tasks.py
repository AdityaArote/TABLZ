"""
TABLZ — Celery background tasks.
"""

import asyncio
from datetime import datetime, timezone

from app.celery.celery_app import celery_app


@celery_app.task(name="app.celery.tasks.reset_daily_specials")
def reset_daily_specials():
    """
    Reset all daily specials at midnight.
    Runs via Celery Beat schedule.
    """
    asyncio.run(_reset_daily_specials_async())


async def _reset_daily_specials_async():
    """Async implementation of daily specials reset."""
    from sqlalchemy import update
    from app.database import async_session_factory
    from app.models.menu_item import MenuItem
    from app.models.audit_log import AuditLog

    async with async_session_factory() as db:
        # Reset all daily specials
        result = await db.execute(
            update(MenuItem)
            .where(MenuItem.is_daily_special == True)
            .values(is_daily_special=False)
            .returning(MenuItem.restaurant_id)
        )
        affected_restaurants = set(row[0] for row in result.fetchall())

        # Audit log
        for restaurant_id in affected_restaurants:
            audit = AuditLog(
                restaurant_id=restaurant_id,
                actor_type="system",
                actor_id="celery:reset_daily_specials",
                action="menu_item.daily_specials_reset",
            )
            db.add(audit)

        await db.commit()
        return f"Reset daily specials for {len(affected_restaurants)} restaurants"


@celery_app.task(name="app.celery.tasks.cleanup_expired_sessions")
def cleanup_expired_sessions():
    """Clean up expired customer sessions."""
    asyncio.run(_cleanup_sessions_async())


async def _cleanup_sessions_async():
    """Async implementation of session cleanup."""
    from sqlalchemy import update
    from app.database import async_session_factory
    from app.models.customer_session import CustomerSession

    async with async_session_factory() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            update(CustomerSession)
            .where(
                CustomerSession.expires_at < now,
                CustomerSession.invalidated_at.is_(None),
            )
            .values(invalidated_at=now)
        )
        await db.commit()
        return f"Invalidated {result.rowcount} expired sessions"
