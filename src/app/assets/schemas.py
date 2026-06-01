"""Pydantic schemas for video assets."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VideoAssetStatus(StrEnum):
    """Supported video asset states."""

    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VideoAssetUploadComplete(BaseModel):
    """Request payload emitted after a video upload completes."""

    source_key: str = Field(min_length=1, max_length=512)
    file_name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=255)

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, value: str) -> str:
        """Ensure the uploaded asset is a video."""

        if not value.startswith("video/"):
            raise ValueError("mime_type must be a video content type")
        return value


class VideoAssetResponse(BaseModel):
    """Serialized video asset state."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_key: str
    file_name: str
    mime_type: str
    status: VideoAssetStatus
    is_playable: bool
    playback_metadata: dict[str, Any] | None
    poster_metadata: dict[str, Any] | None
    thumbnail_metadata: dict[str, Any] | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
