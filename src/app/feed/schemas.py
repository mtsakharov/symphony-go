"""Pydantic schemas for feed endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FeedItemResponse(BaseModel):
    """Serialized feed item returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    body: str
    created_at: datetime


class FeedItemListResponse(BaseModel):
    """Paginated feed items response."""

    items: list[FeedItemResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
