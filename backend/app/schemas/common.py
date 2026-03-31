"""
TABLZ — Common Pydantic schemas used across all endpoints.
"""

from typing import Any
from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: str = ""


class ErrorDetail(BaseModel):
    code: str
    message: str
    suggestion: str = ""
    http_status: int
    request_id: str
    timestamp: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class PaginatedResponse(BaseModel):
    success: bool = True
    data: dict
