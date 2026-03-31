"""
TABLZ — TableService: creation, QR generation, status lifecycle, cleaning flow.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.table import Table
from app.models.audit_log import AuditLog
from app.core.security import generate_qr_token
from app.core.errors import AppException, ErrorCode
from app.config import settings

# Tier limits for tables
TIER_TABLE_LIMITS = {
    "free": 10,
    "premium": 30,
    "vip": 75,
    "luxury": None,  # unlimited
}

# Valid status transitions
VALID_TABLE_TRANSITIONS = {
    "available": ["occupied", "reserved", "cleaning"],
    "occupied": ["cleaning", "available"],
    "cleaning": ["available"],
    "reserved": ["occupied", "available"],
    "merged": ["available"],
}


class TableService:

    @staticmethod
    async def list_tables(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
    ) -> list[Table]:
        """List all tables for a restaurant."""
        result = await db.execute(
            select(Table)
            .where(Table.restaurant_id == restaurant_id)
            .order_by(Table.table_number)
        )
        return result.scalars().all()

    @staticmethod
    async def get_table(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        table_id: uuid.UUID,
    ) -> Table:
        """Get a single table (restaurant-scoped). Returns 404 on cross-restaurant."""
        result = await db.execute(
            select(Table).where(
                Table.id == table_id,
                Table.restaurant_id == restaurant_id,
            )
        )
        table = result.scalar_one_or_none()
        if not table:
            raise AppException(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Table not found",
                http_status=404,
            )
        return table

    @staticmethod
    async def create_table(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        subscription_tier: str,
        table_number: int,
        max_capacity: int = 4,
        is_expandable: bool = False,
        actor_id: str = "",
    ) -> Table:
        """Create a table with QR code token, enforcing tier limits."""
        # Check tier limit
        max_tables = TIER_TABLE_LIMITS.get(subscription_tier)
        if max_tables is not None:
            count_result = await db.execute(
                select(func.count(Table.id)).where(
                    Table.restaurant_id == restaurant_id,
                )
            )
            current_count = count_result.scalar() or 0
            if current_count >= max_tables:
                raise AppException(
                    code=ErrorCode.SUBSCRIPTION_LIMIT_EXCEEDED,
                    message=f"Table limit reached ({max_tables} for {subscription_tier} tier)",
                    http_status=402,
                    suggestion="Upgrade your subscription to add more tables",
                )

        # Check duplicate table number
        existing = await db.execute(
            select(Table).where(
                Table.restaurant_id == restaurant_id,
                Table.table_number == table_number,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Table number {table_number} already exists",
                http_status=409,
            )

        # Generate QR token and URL
        qr_token = generate_qr_token()
        qr_url = f"{settings.BASE_URL}/scan/{qr_token}"

        table = Table(
            id=uuid.uuid4(),
            restaurant_id=restaurant_id,
            table_number=table_number,
            max_capacity=max_capacity,
            is_expandable=is_expandable,
            qr_code_token=qr_token,
            qr_code_url=qr_url,
        )
        db.add(table)

        # Audit
        audit = AuditLog(
            restaurant_id=restaurant_id,
            actor_type="admin",
            actor_id=actor_id,
            action="table.created",
            resource_type="table",
            resource_id=table.id,
        )
        db.add(audit)

        await db.commit()
        await db.refresh(table)
        return table

    @staticmethod
    async def update_status(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        table_id: uuid.UUID,
        new_status: str,
        actor_id: str = "",
    ) -> Table:
        """Update table status with transition validation."""
        table = await TableService.get_table(db, restaurant_id, table_id)

        allowed = VALID_TABLE_TRANSITIONS.get(table.status, [])
        if new_status not in allowed:
            raise AppException(
                code=ErrorCode.ORDER_INVALID_TRANSITION,
                message=f"Cannot transition table from '{table.status}' to '{new_status}'",
                http_status=409,
                suggestion=f"Valid transitions from '{table.status}': {allowed}",
            )

        old_status = table.status
        table.status = new_status

        # Track cleaning
        if new_status == "cleaning":
            table.last_cleaned_at = datetime.now(timezone.utc)

        # Clear session on table reset
        if new_status == "available":
            table.owner_session_id = None
            table.merged_into_table_id = None

        audit = AuditLog(
            restaurant_id=restaurant_id,
            actor_type="admin",
            actor_id=actor_id,
            action="table.status_changed",
            resource_type="table",
            resource_id=table.id,
            metadata_json={"old_status": old_status, "new_status": new_status},
        )
        db.add(audit)

        await db.commit()
        await db.refresh(table)
        return table

    @staticmethod
    async def mark_cleaning(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        table_id: uuid.UUID,
        actor_id: str = "",
    ) -> Table:
        """Shorthand: set table to 'cleaning' status."""
        return await TableService.update_status(
            db, restaurant_id, table_id, "cleaning", actor_id
        )

    @staticmethod
    async def get_qr_info(
        db: AsyncSession,
        restaurant_id: uuid.UUID,
        table_id: uuid.UUID,
    ) -> dict:
        """Get QR info for a table."""
        table = await TableService.get_table(db, restaurant_id, table_id)
        return {
            "qr_image_url": table.qr_code_url,
            "qr_code_token": table.qr_code_token,
            "table_number": table.table_number,
        }

    @staticmethod
    async def lookup_by_qr_token(
        db: AsyncSession,
        qr_token: str,
    ) -> Table | None:
        """Look up a table by its QR token (used during scan). No restaurant scoping here — token is globally unique."""
        result = await db.execute(
            select(Table).where(Table.qr_code_token == qr_token)
        )
        return result.scalar_one_or_none()
