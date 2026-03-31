"""Table model — restaurant tables with QR codes and status tracking."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, SmallInteger, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Table(Base):
    __tablename__ = "tables"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "table_number", name="uq_restaurant_table_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    table_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available"
    )
    owner_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_sessions.id"), nullable=True
    )
    merged_into_table_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tables.id"), nullable=True
    )
    is_expandable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    qr_code_token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    qr_code_url: Mapped[str] = mapped_column(Text, nullable=False)
    max_capacity: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=4)
    last_cleaned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    restaurant = relationship("Restaurant", back_populates="tables")
    customer_sessions = relationship("CustomerSession", back_populates="table", foreign_keys="[CustomerSession.table_id]")
