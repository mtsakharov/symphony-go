"""Pydantic schemas for post endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.posts.models import MediaAssetType, MediaState, PostType, UploadStatus

CaptionField = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2200)]


class PostCreate(BaseModel):
    """Payload for creating a post."""

    post_type: PostType
    caption: CaptionField | None = None
    asset_ids: list[UUID] = Field(default_factory=list)


class MediaAssetResponse(BaseModel):
    """Serialized media asset returned with a post."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_type: MediaAssetType
    upload_status: UploadStatus


class PostResponse(BaseModel):
    """Serialized post returned by the API."""

    id: UUID
    post_type: PostType
    caption: str
    media_state: MediaState
    assets: list[MediaAssetResponse]
    created_at: datetime
    updated_at: datetime

