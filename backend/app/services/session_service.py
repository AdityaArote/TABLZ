"""
TABLZ — SessionService: QR-based customer session creation and management.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_session import CustomerSession
from app.models.table import Table
from app.models.restaurant import Restaurant
from app.models.audit_log import AuditLog
from app.core.security import generate_session_token
from app.core.errors import AppException, ErrorCode


class SessionService:

    @staticmethod
    async def create_qr_session(
        db: AsyncSession,
        qr_code_token: str,
        device_fingerprint: str | None = None,
    ) -> dict:
        """
        Create a customer session from QR scan.
        - No login required
        - First scanner = table owner
        - 4-hour TTL
        - Updates table status to 'occupied'
        """
        # Look up table by QR token
        result = await db.execute(
            select(Table).where(Table.qr_code_token == qr_code_token)
        )
        table = result.scalar_one_or_none()

        if not table:
            raise AppException(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Invalid QR code",
                http_status=404,
                suggestion="The QR code may have been regenerated",
            )

        # Get restaurant info
        restaurant_result = await db.execute(
            select(Restaurant).where(Restaurant.id == table.restaurant_id)
        )
        restaurant = restaurant_result.scalar_one_or_none()

        if not restaurant or not restaurant.is_active:
            raise AppException(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Restaurant not found",
                http_status=404,
            )

        # Check if table is in a scannable state
        if table.status == "cleaning":
            raise AppException(
                code=ErrorCode.VALIDATION_ERROR,
                message="This table is currently being cleaned",
                http_status=400,
                suggestion="Please ask staff for assistance",
            )

        # Determine ownership
        is_owner = table.status == "available"

        # Create session
        session_token = generate_session_token()
        now = datetime.now(timezone.utc)

        session = CustomerSession(
            id=uuid.uuid4(),
            table_id=table.id,
            restaurant_id=table.restaurant_id,
            session_token=session_token,
            is_table_owner=is_owner,
            device_fingerprint=device_fingerprint,
            created_at=now,
            expires_at=now + timedelta(hours=4),
        )
        db.add(session)

        # Update table status
        if is_owner:
            table.status = "occupied"
            table.owner_session_id = session.id

        # Audit
        audit = AuditLog(
            restaurant_id=table.restaurant_id,
            actor_type="customer",
            actor_id=str(session.id),
            action="session.created",
            resource_type="customer_session",
            resource_id=session.id,
            metadata_json={
                "table_number": table.table_number,
                "is_owner": is_owner,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(session)

        return {
            "session_token": session_token,
            "table_id": str(table.id),
            "table_number": table.table_number,
            "restaurant_name": restaurant.name,
            "restaurant_id": str(restaurant.id),
            "is_table_owner": is_owner,
        }
