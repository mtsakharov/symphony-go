"""Service layer for video upload initiation."""

from __future__ import annotations

import re
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.video_uploads.exceptions import VideoUploadValidationError
from app.video_uploads.models import VideoUpload
from app.video_uploads.repository import VideoUploadRepository
from app.video_uploads.schemas import (
    VideoAssetInput,
    VideoAssetResponse,
    VideoUploadCreateRequest,
    VideoUploadFailureCode,
    VideoUploadResponse,
    VideoUploadStatus,
)


class VideoUploadService:
    """Business logic for creating validated video upload intents."""

    def __init__(
        self,
        repository: VideoUploadRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository or VideoUploadRepository()
        self.settings = settings or get_settings()

    def initiate_upload(
        self,
        session: Session,
        payload: VideoUploadCreateRequest,
    ) -> VideoUploadResponse:
        """Validate the request and persist a pending upload intent."""

        if len(payload.assets) != 1:
            raise VideoUploadValidationError(
                VideoUploadFailureCode.INVALID_ASSET_COUNT,
                "Exactly one video asset is required",
            )

        asset = payload.assets[0]
        self._validate_asset(asset)
        upload_id = uuid4()

        upload = VideoUpload(
            id=upload_id,
            filename=asset.filename,
            mime_type=asset.mime_type,
            codec=asset.codec,
            file_size_bytes=asset.file_size_bytes,
            duration_seconds=asset.duration_seconds,
            status=VideoUploadStatus.PENDING_UPLOAD.value,
            upload_path=self._build_upload_path(upload_id, asset.filename),
        )

        self.repository.create(session, upload=upload)
        session.commit()
        session.refresh(upload)
        return self._build_response(upload)

    def _validate_asset(self, asset: VideoAssetInput) -> None:
        """Enforce the configured MIME type, codec, size, and duration limits."""

        allowed_mime_types = set(self.settings.video_upload_allowed_mime_types)
        allowed_codecs = set(self.settings.video_upload_allowed_codecs)
        if asset.mime_type not in allowed_mime_types or asset.codec not in allowed_codecs:
            raise VideoUploadValidationError(
                VideoUploadFailureCode.UNSUPPORTED_FORMAT,
                "Video format is not supported",
            )

        if asset.file_size_bytes > self.settings.video_upload_max_size_bytes:
            raise VideoUploadValidationError(
                VideoUploadFailureCode.FILE_TOO_LARGE,
                "Video file exceeds the configured size limit",
            )

        if asset.duration_seconds > self.settings.video_upload_max_duration_seconds:
            raise VideoUploadValidationError(
                VideoUploadFailureCode.DURATION_TOO_LONG,
                "Video duration exceeds the configured limit",
            )

    def _build_upload_path(self, upload_id: object, filename: str) -> str:
        """Return a deterministic object path for the reserved upload slot."""

        sanitized_filename = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-") or "video"
        return (
            f"{self.settings.video_upload_storage_prefix.rstrip('/')}/"
            f"{upload_id}/{sanitized_filename}"
        )

    def _build_response(self, upload: VideoUpload) -> VideoUploadResponse:
        """Convert a persisted model into the API response shape."""

        return VideoUploadResponse(
            id=upload.id,
            status=VideoUploadStatus(upload.status),
            upload_path=upload.upload_path,
            created_at=upload.created_at,
            asset=VideoAssetResponse(
                filename=upload.filename,
                mime_type=upload.mime_type,
                codec=upload.codec,
                file_size_bytes=upload.file_size_bytes,
                duration_seconds=upload.duration_seconds,
            ),
        )
