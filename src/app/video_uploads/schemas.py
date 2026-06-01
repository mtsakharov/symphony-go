"""Pydantic schemas for video upload initiation."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

FilenameField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
FormatField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class VideoUploadStatus(StrEnum):
    """Persisted lifecycle states for upload initiation."""

    PENDING_UPLOAD = "pending_upload"


class VideoUploadFailureCode(StrEnum):
    """Machine-readable validation failure reasons."""

    INVALID_ASSET_COUNT = "invalid_asset_count"
    UNSUPPORTED_FORMAT = "unsupported_format"
    FILE_TOO_LARGE = "file_too_large"
    DURATION_TOO_LONG = "duration_too_long"


class VideoAssetInput(BaseModel):
    """Metadata required to initiate an upload for a single video asset."""

    filename: FilenameField
    mime_type: FormatField
    codec: FormatField
    file_size_bytes: int = Field(gt=0)
    duration_seconds: float = Field(gt=0)

    @field_validator("mime_type", "codec")
    @classmethod
    def _normalize_format_value(cls, value: str) -> str:
        """Normalize format values for case-insensitive comparisons."""

        return value.lower()


class VideoUploadCreateRequest(BaseModel):
    """API payload for creating a new upload intent."""

    assets: list[VideoAssetInput]


class VideoAssetResponse(BaseModel):
    """Serialized asset metadata returned with an upload intent."""

    filename: str
    mime_type: str
    codec: str
    file_size_bytes: int
    duration_seconds: float


class VideoUploadResponse(BaseModel):
    """Serialized upload intent returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: VideoUploadStatus
    upload_path: str
    created_at: datetime
    asset: VideoAssetResponse


class VideoUploadErrorDetail(BaseModel):
    """Machine-readable validation error payload."""

    code: VideoUploadFailureCode
    message: str


class VideoUploadErrorResponse(BaseModel):
    """HTTP error envelope for validation failures."""

    detail: VideoUploadErrorDetail
