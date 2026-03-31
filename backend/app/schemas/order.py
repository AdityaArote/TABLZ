"""
TABLZ — Pydantic schemas for order endpoints.
"""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    menu_item_id: UUID
    quantity: int = Field(..., ge=1, le=50)
    item_notes: str | None = Field(None, max_length=500)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(..., min_length=1)
    special_requests: str | None = Field(None, max_length=1000)


class OrderStatusUpdate(BaseModel):
    status: str  # validated by state machine in service


class OrderItemResponse(BaseModel):
    id: UUID
    menu_item_id: UUID
    quantity: int
    unit_price_at_order: float
    item_notes: str | None

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: UUID
    table_id: UUID
    session_id: UUID
    status: str
    special_requests: str | None
    total_amount: float
    tax_amount: float
    is_finalized: bool
    barcode_token: str | None
    placed_at: datetime
    finalized_at: datetime | None
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class QrSessionRequest(BaseModel):
    qr_code_token: str = Field(..., min_length=1)
    device_fingerprint: str | None = Field(None, max_length=64)


class QrSessionResponse(BaseModel):
    table_id: UUID
    table_number: int
    restaurant_name: str
    is_table_owner: bool
