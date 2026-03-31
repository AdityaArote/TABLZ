"""TaxConfiguration model — per-restaurant tax rules."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaxConfiguration(Base):
    __tablename__ = "tax_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rate_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    applies_to: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
