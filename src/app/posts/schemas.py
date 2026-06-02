"""Pydantic schemas for post endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.posts.models import PostType, VideoProcessingStatus


class MediaAssetResponse(BaseModel):
    """Renderable metadata for a derived image asset."""

    url: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class VideoMediaResponse(BaseModel):
    """Video metadata shared by feed and detail responses."""

    status: VideoProcessingStatus
    is_playable: bool
    caption: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    poster: MediaAssetResponse | None = None
    thumbnail: MediaAssetResponse | None = None
    playback_reference: str | None = None
    failure_reason: str | None = None


class PostResponse(BaseModel):
    """Serialized post returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_type: PostType
    body: str
    video_media: VideoMediaResponse | None = None
    created_at: datetime
    updated_at: datetime


class PostDetailResponse(PostResponse):
    """Detailed post response payload."""


class FeedResponse(BaseModel):
    """Paginated feed response."""

    items: list[PostResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
