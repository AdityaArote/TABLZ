"""OrderItem model — individual line items with price snapshot."""

import uuid

from sqlalchemy import SmallInteger, Text, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    unit_price_at_order: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    item_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem")
