"""Pydantic schemas for the video-post lifecycle API."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.posts.models import PostStatus, PostType, VideoAssetStatus, VideoUploadStatus

CaptionField = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2200)]
FilenameField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
FormatField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class VideoUploadFailureCode(StrEnum):
    """Machine-readable upload-validation errors."""

    INVALID_ASSET_COUNT = "invalid_asset_count"
    UNSUPPORTED_FORMAT = "unsupported_format"
    UNSUPPORTED_AUDIO_CODEC = "unsupported_audio_codec"
    FILE_TOO_LARGE = "file_too_large"
    DURATION_TOO_LONG = "duration_too_long"


class PostCreate(BaseModel):
    """Payload for creating a post shell."""

    user_id: UUID
    post_type: PostType
    caption: CaptionField | None = None


class VideoAssetInput(BaseModel):
    """Metadata required to reserve a single upload slot."""

    filename: FilenameField
    mime_type: FormatField
    video_codec: FormatField
    audio_codec: FormatField
    file_size_bytes: int = Field(gt=0)
    duration_seconds: float = Field(gt=0)

    @field_validator("mime_type", "video_codec", "audio_codec")
    @classmethod
    def normalize_format_values(cls, value: str) -> str:
        """Normalize format values for case-insensitive validation."""

        return value.lower()


class VideoUploadCreateRequest(BaseModel):
    """Upload-initiation request."""

    assets: list[VideoAssetInput]


class VideoUploadAssetResponse(BaseModel):
    """Serialized input asset metadata."""

    filename: str
    mime_type: str
    video_codec: str
    audio_codec: str
    file_size_bytes: int
    duration_seconds: float


class VideoUploadResponse(BaseModel):
    """Serialized upload intent."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: VideoUploadStatus
    upload_path: str
    created_at: datetime
    asset: VideoUploadAssetResponse


class VideoUploadErrorDetail(BaseModel):
    """Machine-readable validation-error payload."""

    code: VideoUploadFailureCode
    message: str


class VideoUploadErrorResponse(BaseModel):
    """HTTP validation envelope."""

    detail: VideoUploadErrorDetail


class VideoUploadCompleteRequest(BaseModel):
    """Upload-finalization payload."""

    source_key: str = Field(min_length=1, max_length=512)


class VideoAssetResponse(BaseModel):
    """Serialized processed asset state."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    upload_id: UUID
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


class PostResponse(BaseModel):
    """Serialized post detail or feed item."""

    id: UUID
    user_id: UUID
    post_type: PostType
    caption: str
    status: PostStatus
    video_asset: VideoAssetResponse | None
    created_at: datetime
    updated_at: datetime


class PostListResponse(BaseModel):
    """Paginated feed response."""

    items: list[PostResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
