"""Pydantic schemas for posts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.media.schemas import MediaAssetResponse
from app.posts.models import PostType


class PostCreate(BaseModel):
    """Request body for creating a video post."""

    post_type: PostType = PostType.VIDEO
    caption: str = Field(default="", max_length=2200)
    asset_ids: list[UUID] = Field(min_length=1, max_length=1)


class PostResponse(BaseModel):
    """Serialized post response."""

    id: UUID
    post_type: PostType
    caption: str
    assets: list[MediaAssetResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

