"""Pydantic schemas for media lifecycle flows."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.media.models import MediaAssetRole, MediaAssetType, MediaLifecycleState


class VideoUploadFailureCode(StrEnum):
    """Machine-readable video upload validation failures."""

    INVALID_ASSET_COUNT = "invalid_asset_count"
    UNSUPPORTED_FORMAT = "unsupported_format"
    FILE_TOO_LARGE = "file_too_large"
    DURATION_TOO_LONG = "duration_too_long"


class VideoAssetInput(BaseModel):
    """Validated client metadata for a video upload."""

    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=255)
    codec: str = Field(min_length=1, max_length=100)
    file_size_bytes: int = Field(gt=0)
    duration_seconds: float = Field(gt=0)


class VideoUploadCreateRequest(BaseModel):
    """Request body for reserving a video upload slot."""

    assets: list[VideoAssetInput]


class VideoUploadAssetResponse(BaseModel):
    """Serialized metadata for a video upload asset."""

    filename: str
    mime_type: str
    codec: str | None
    file_size_bytes: int | None
    duration_seconds: float | None


class VideoUploadResponse(BaseModel):
    """Response returned for video upload initiation and completion."""

    id: UUID
    status: MediaLifecycleState
    upload_path: str
    cleanup_after: datetime | None
    created_at: datetime
    updated_at: datetime
    asset: VideoUploadAssetResponse


class VideoUploadErrorDetail(BaseModel):
    """Structured validation failure details."""

    code: VideoUploadFailureCode
    message: str


class VideoUploadErrorResponse(BaseModel):
    """Error envelope for upload validation failures."""

    detail: VideoUploadErrorDetail


class MediaAssetResponse(BaseModel):
    """Serialized representation of an attached media asset."""

    id: UUID
    media_type: MediaAssetType
    asset_role: MediaAssetRole
    lifecycle_state: MediaLifecycleState
    filename: str
    mime_type: str
    storage_path: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CleanupSummary(BaseModel):
    """Summary of a cleanup run."""

    processed: int
    failed: int

