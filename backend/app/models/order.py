"""Order model — orders with server-enforced status state machine."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Text, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Valid status transitions (server-enforced state machine)
VALID_ORDER_TRANSITIONS = {
    "pending": ["received", "cancelled"],
    "received": ["preparing", "cancelled"],
    "preparing": ["ready", "cancelled"],
    "ready": ["served", "cancelled"],
    "served": [],
    "cancelled": [],
}


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tables.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_sessions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    special_requests: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    is_finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    barcode_token: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True
    )
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    restaurant = relationship("Restaurant", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", lazy="selectin")

    def can_transition_to(self, new_status: str) -> bool:
        """Check if a status transition is valid."""
        return new_status in VALID_ORDER_TRANSITIONS.get(self.status, [])
