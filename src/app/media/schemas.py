"""Pydantic schemas for media endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.media.models import Media


class ErrorResponse(BaseModel):
    """Structured API error response."""

    detail: str


class MediaResponse(BaseModel):
    """Serialized media record returned by the API."""

    id: UUID
    filename: str
    content_type: str
    size: int = Field(ge=0)
    storage_path: str
    url: str | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, media: Media, *, url: str | None) -> MediaResponse:
        """Build a response model from a database entity and resolved URL."""

        return cls(
            id=media.id,
            filename=media.filename,
            content_type=media.content_type,
            size=media.size,
            storage_path=media.storage_path,
            url=url,
            created_at=media.created_at,
        )


class MediaListResponse(BaseModel):
    """Paginated media list response."""

    items: list[MediaResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)


class DeleteMediaResponse(BaseModel):
    """Delete media response payload."""

    message: str
