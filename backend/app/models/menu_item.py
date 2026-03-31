"""MenuItem model — menu items with soft-delete and special flags."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, SmallInteger, Text, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    cuisine: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dietary_type: Mapped[str] = mapped_column(String(30), nullable=False)
    is_daily_special: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_weekly_special: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    prep_time_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=15)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="menu_items")
