"""Pydantic schemas for posts and attached video assets."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MediaType(StrEnum):
    """Supported media types for posts."""

    VIDEO = "video"


class VideoProcessingStatus(StrEnum):
    """Supported video processing states."""

    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VideoAsset(BaseModel):
    """Single attached video asset metadata."""

    media_type: MediaType = MediaType.VIDEO
    upload_ref: str | None = Field(default=None, max_length=2048)
    asset_ref: str | None = Field(default=None, max_length=2048)
    processing_status: VideoProcessingStatus
    playback_ref: str | None = Field(default=None, max_length=2048)
    poster_ref: str | None = Field(default=None, max_length=2048)
    duration_ms: int | None = Field(default=None, ge=0)
    failure_reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_asset(self) -> VideoAsset:
        """Validate dependent video asset fields."""

        if self.upload_ref is None and self.asset_ref is None:
            raise ValueError("video assets require an upload_ref or asset_ref")
        if self.processing_status == VideoProcessingStatus.FAILED and self.failure_reason is None:
            raise ValueError("failed video assets require a failure_reason")
        return self


class PostResponse(BaseModel):
    """Serialized post returned by downstream API layers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    body: str
    video_asset: VideoAsset | None = None
    created_at: datetime
    updated_at: datetime
