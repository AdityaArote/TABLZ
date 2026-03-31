"""Restaurant model — core tenant entity for TABLZ multi-tenancy."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    admin_id: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default="free"
    )
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Kolkata")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ─── For auth: email verification + refresh tokens ───
    email_verification_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email_verification_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refresh_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    tables = relationship("Table", back_populates="restaurant", lazy="selectin")
    menu_items = relationship("MenuItem", back_populates="restaurant", lazy="selectin")
    orders = relationship("Order", back_populates="restaurant", lazy="selectin")
