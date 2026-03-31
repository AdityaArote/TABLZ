"""
TABLZ — Pydantic schemas for menu endpoints.
"""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


class MenuItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    price: float = Field(..., gt=0)
    category: Literal["appetizer", "main", "dessert", "beverage", "side"]
    cuisine: str | None = Field(None, max_length=100)
    dietary_type: Literal["vegetarian", "non_vegetarian", "vegan", "contains_nuts"]
    is_daily_special: bool = False
    is_weekly_special: bool = False
    prep_time_minutes: int = Field(15, ge=1, le=180)


class MenuItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    price: float | None = Field(None, gt=0)
    category: Literal["appetizer", "main", "dessert", "beverage", "side"] | None = None
    cuisine: str | None = Field(None, max_length=100)
    dietary_type: Literal["vegetarian", "non_vegetarian", "vegan", "contains_nuts"] | None = None
    is_daily_special: bool | None = None
    is_weekly_special: bool | None = None
    prep_time_minutes: int | None = Field(None, ge=1, le=180)


class MenuItemAvailability(BaseModel):
    is_available: bool


class MenuItemResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    price: float
    category: str
    cuisine: str | None
    dietary_type: str
    is_daily_special: bool
    is_weekly_special: bool
    is_available: bool
    image_url: str | None
    prep_time_minutes: int

    model_config = {"from_attributes": True}
