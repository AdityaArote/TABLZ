"""
TABLZ — Pydantic schemas for table endpoints.
"""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class TableCreate(BaseModel):
    table_number: int = Field(..., ge=1, le=999)
    max_capacity: int = Field(4, ge=1, le=50)
    is_expandable: bool = False


class TableResponse(BaseModel):
    id: UUID
    table_number: int
    status: str
    max_capacity: int
    is_expandable: bool
    qr_code_token: str
    qr_code_url: str
    last_cleaned_at: datetime | None

    model_config = {"from_attributes": True}


class TableStatusUpdate(BaseModel):
    status: str  # validated in service layer


class TableMergeRequest(BaseModel):
    merge_with_table_id: UUID
