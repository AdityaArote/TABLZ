"""AuditLog model — immutable, append-only audit trail."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=True
    )
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
