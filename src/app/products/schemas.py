"""Pydantic schemas for product endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ProductNameField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class ProductResponse(BaseModel):
    """Serialized product returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: ProductNameField
    price: Decimal
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    """Paginated products list response."""

    items: list[ProductResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
