"""Service layer for media lifecycle and cleanup."""

from __future__ import annotations

import re
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.media.exceptions import (
    MediaAssetNotFoundError,
    MediaLifecycleError,
    VideoUploadValidationError,
)
from app.media.models import (
    MediaAsset,
    MediaAssetRole,
    MediaAssetType,
    MediaLifecycleState,
    utc_now,
)
from app.media.repository import MediaRepository
from app.media.schemas import (
    CleanupSummary,
    VideoAssetInput,
    VideoUploadCreateRequest,
    VideoUploadFailureCode,
    VideoUploadResponse,
)
from app.media.storage import MediaStorage

LOGGER = get_logger(__name__)
_FILENAME_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class MediaService:
    """Business logic for upload lifecycle transitions."""

    def __init__(
        self,
        repository: MediaRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository or MediaRepository()
        self.settings = settings or get_settings()

    def initiate_video_upload(
        self,
        session: Session,
        payload: VideoUploadCreateRequest,
    ) -> VideoUploadResponse:
        """Validate and persist a pending video upload."""

        if len(payload.assets) != 1:
            raise VideoUploadValidationError(
                VideoUploadFailureCode.INVALID_ASSET_COUNT,
                "Exactly one video asset is required",
            )

        asset_input = payload.assets[0]
        self._validate_video_asset(asset_input)

        upload_id = uuid4()
        asset = MediaAsset(
            id=upload_id,
            media_type=MediaAssetType.VIDEO,
            asset_role=MediaAssetRole.SOURCE,
            lifecycle_state=MediaLifecycleState.PENDING_UPLOAD,
            filename=asset_input.filename,
            mime_type=asset_input.mime_type,
            codec=asset_input.codec,
            file_size_bytes=asset_input.file_size_bytes,
            duration_seconds=asset_input.duration_seconds,
            storage_path=self._build_upload_path(upload_id, asset_input.filename),
            cleanup_after=utc_now()
            + timedelta(seconds=self.settings.media_abandoned_upload_timeout_seconds),
        )
        self.repository.create(session, asset=asset)
        session.commit()
        session.refresh(asset)
        return self._serialize_upload(asset)

    def complete_video_upload(self, session: Session, asset_id: UUID) -> VideoUploadResponse:
        """Mark a reserved upload as completed and ready for post attachment."""

        asset = self.repository.get_by_id(session, asset_id)
        if asset is None:
            raise MediaAssetNotFoundError("Video upload not found")

        if asset.lifecycle_state in {
            MediaLifecycleState.COMPLETED_UPLOAD,
            MediaLifecycleState.ATTACHED,
        }:
            return self._serialize_upload(asset)

        if asset.lifecycle_state is not MediaLifecycleState.PENDING_UPLOAD:
            raise MediaLifecycleError("Video upload cannot be completed from its current state")

        asset.lifecycle_state = MediaLifecycleState.COMPLETED_UPLOAD
        asset.cleanup_after = None
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return self._serialize_upload(asset)

    def create_derived_asset(
        self,
        session: Session,
        *,
        post_id: UUID,
        source_asset_id: UUID,
        filename: str,
        mime_type: str,
        storage_path: str,
        details: dict[str, object] | None = None,
    ) -> MediaAsset:
        """Persist a derived asset owned by an attached source upload."""

        source_asset = self.repository.get_by_id(session, source_asset_id)
        if source_asset is None:
            raise MediaAssetNotFoundError("Source media asset not found")
        if source_asset.post_id != post_id:
            raise MediaLifecycleError("Derived assets must belong to the source asset post")

        asset = MediaAsset(
            media_type=MediaAssetType.VIDEO,
            asset_role=MediaAssetRole.DERIVED,
            lifecycle_state=MediaLifecycleState.ATTACHED,
            filename=filename,
            mime_type=mime_type,
            codec=None,
            file_size_bytes=None,
            duration_seconds=None,
            storage_path=storage_path,
            details=details,
            post_id=post_id,
            source_media_id=source_asset.id,
        )
        self.repository.create(session, asset=asset)
        session.commit()
        session.refresh(asset)
        return asset

    def _validate_video_asset(self, asset: VideoAssetInput) -> None:
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

    def _build_upload_path(self, asset_id: UUID, filename: str) -> str:
        sanitized_filename = _FILENAME_SAFE_PATTERN.sub("-", filename).strip("-") or "video.mp4"
        prefix = self.settings.video_upload_storage_prefix.rstrip("/")
        return f"{prefix}/{asset_id}/{sanitized_filename}"

    def _serialize_upload(self, asset: MediaAsset) -> VideoUploadResponse:
        return VideoUploadResponse(
            id=asset.id,
            status=asset.lifecycle_state,
            upload_path=asset.storage_path,
            cleanup_after=asset.cleanup_after,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            asset={
                "filename": asset.filename,
                "mime_type": asset.mime_type,
                "codec": asset.codec,
                "file_size_bytes": asset.file_size_bytes,
                "duration_seconds": asset.duration_seconds,
            },
        )


class MediaCleanupService:
    """Delete expired abandoned uploads and post-owned assets."""

    def __init__(
        self,
        *,
        repository: MediaRepository | None = None,
        storage: MediaStorage,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository or MediaRepository()
        self.storage = storage
        self.settings = settings or get_settings()

    def run_once(self, session: Session) -> CleanupSummary:
        """Run one cleanup batch and return the result summary."""

        now = utc_now()
        assets = self.repository.list_due_for_cleanup(
            session,
            now=now,
            limit=self.settings.media_cleanup_batch_size,
        )
        processed = 0
        failed = 0

        for asset in assets:
            try:
                self.storage.delete(asset.storage_path)
            except Exception:
                failed += 1
                LOGGER.error(
                    "Media cleanup failed for asset_id=%s storage_path=%s state=%s",
                    asset.id,
                    asset.storage_path,
                    asset.lifecycle_state,
                    exc_info=True,
                )
                continue

            asset.lifecycle_state = MediaLifecycleState.DELETED
            asset.deleted_at = now
            asset.cleanup_after = None
            session.add(asset)
            processed += 1

        session.commit()
        LOGGER.info(
            "Media cleanup batch completed processed=%s failed=%s",
            processed,
            failed,
        )
        return CleanupSummary(processed=processed, failed=failed)
