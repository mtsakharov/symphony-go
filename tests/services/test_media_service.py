"""Unit tests for media lifecycle services."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.media.exceptions import MediaLifecycleError, VideoUploadValidationError
from app.media.models import (
    MediaAsset,
    MediaAssetRole,
    MediaAssetType,
    MediaLifecycleState,
    utc_now,
)
from app.media.schemas import VideoUploadCreateRequest
from app.media.service import LOGGER, MediaCleanupService, MediaService
from app.media.storage import LocalMediaStorage, MediaStorage


def build_settings(**overrides: object) -> Settings:
    """Return test settings with deterministic lifecycle values."""

    defaults: dict[str, object] = {
        "database_url": "sqlite:///unused.db",
        "media_abandoned_upload_timeout_seconds": 600,
        "media_cleanup_batch_size": 10,
        "media_delete_retention_seconds": 0,
        "video_upload_storage_prefix": "video-uploads",
        "media_storage_dir": ".media",
    }
    defaults.update(overrides)
    return Settings(**cast(dict[str, Any], defaults))


def build_upload_request() -> VideoUploadCreateRequest:
    """Return a valid upload initiation request payload."""

    return VideoUploadCreateRequest(
        assets=[
            {
                "filename": "clip.mp4",
                "mime_type": "video/mp4",
                "codec": "h264",
                "file_size_bytes": 5_000_000,
                "duration_seconds": 45,
            }
        ]
    )


def persist_due_asset(
    session: Session,
    *,
    lifecycle_state: MediaLifecycleState,
    storage_path: str,
    cleanup_after_delta_seconds: int,
) -> MediaAsset:
    """Persist an asset due for cleanup."""

    now = utc_now()
    asset = MediaAsset(
        media_type=MediaAssetType.VIDEO,
        asset_role=MediaAssetRole.SOURCE,
        lifecycle_state=lifecycle_state,
        filename="clip.mp4",
        mime_type="video/mp4",
        codec="h264",
        file_size_bytes=1,
        duration_seconds=1.0,
        storage_path=storage_path,
        cleanup_after=now + timedelta(seconds=cleanup_after_delta_seconds),
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def test_initiate_video_upload_sets_pending_state_and_timeout(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Initiating an upload should create a non-visible pending asset with a timeout."""

    service = MediaService(settings=build_settings(media_abandoned_upload_timeout_seconds=1200))

    with db_session_factory() as session:
        response = service.initiate_video_upload(session, build_upload_request())
        asset = session.get(MediaAsset, response.id)

        assert asset is not None
        assert asset.asset_role is MediaAssetRole.SOURCE
        assert asset.lifecycle_state is MediaLifecycleState.PENDING_UPLOAD
        assert asset.cleanup_after is not None
        assert response.status is MediaLifecycleState.PENDING_UPLOAD
        assert response.upload_path.endswith("/clip.mp4")


def test_complete_video_upload_is_idempotent(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Completing an upload repeatedly should be safe."""

    service = MediaService(settings=build_settings())

    with db_session_factory() as session:
        initiated = service.initiate_video_upload(session, build_upload_request())
        completed = service.complete_video_upload(session, initiated.id)
        repeated = service.complete_video_upload(session, initiated.id)

        assert completed.status is MediaLifecycleState.COMPLETED_UPLOAD
        assert repeated.status is MediaLifecycleState.COMPLETED_UPLOAD


def test_complete_video_upload_rejects_invalid_transition(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Uploads scheduled for deletion cannot be completed again."""

    service = MediaService(settings=build_settings())

    with db_session_factory() as session:
        initiated = service.initiate_video_upload(session, build_upload_request())
        asset = session.get(MediaAsset, initiated.id)
        assert asset is not None
        asset.lifecycle_state = MediaLifecycleState.PENDING_DELETE
        session.add(asset)
        session.commit()

        with pytest.raises(
            MediaLifecycleError,
            match="cannot be completed from its current state",
        ):
            service.complete_video_upload(session, initiated.id)


def test_initiate_video_upload_rejects_invalid_metadata() -> None:
    """Unsupported uploads should fail with a machine-readable error."""

    service = MediaService(
        settings=build_settings(video_upload_allowed_codecs=("h264",)),
    )
    session = Mock()

    with pytest.raises(VideoUploadValidationError, match="Video format is not supported"):
        service.initiate_video_upload(
            session,
            VideoUploadCreateRequest(
                assets=[
                    {
                        "filename": "clip.mov",
                        "mime_type": "video/quicktime",
                        "codec": "hevc",
                        "file_size_bytes": 1,
                        "duration_seconds": 1,
                    }
                ]
            ),
        )


def test_cleanup_service_deletes_expired_abandoned_upload_and_is_retry_safe(
    db_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    """Expired pending uploads should be deleted and reruns should not fail if already gone."""

    storage = LocalMediaStorage(storage_dir=tmp_path)
    service = MediaCleanupService(
        storage=storage,
        settings=build_settings(media_storage_dir=str(tmp_path)),
    )

    with db_session_factory() as session:
        asset = persist_due_asset(
            session,
            lifecycle_state=MediaLifecycleState.PENDING_UPLOAD,
            storage_path="video-uploads/test/clip.mp4",
            cleanup_after_delta_seconds=-1,
        )
        stored_file = storage.resolve_path(asset.storage_path)
        stored_file.parent.mkdir(parents=True, exist_ok=True)
        stored_file.write_bytes(b"junk")

        first_summary = service.run_once(session)
        session.refresh(asset)

        assert first_summary.processed == 1
        assert first_summary.failed == 0
        assert not stored_file.exists()
        assert asset.lifecycle_state is MediaLifecycleState.DELETED

        asset.lifecycle_state = MediaLifecycleState.PENDING_UPLOAD
        asset.cleanup_after = asset.updated_at
        session.add(asset)
        session.commit()

        second_summary = service.run_once(session)
        session.refresh(asset)

        assert second_summary.processed == 1
        assert second_summary.failed == 0
        assert asset.lifecycle_state is MediaLifecycleState.DELETED


def test_cleanup_service_logs_failures_and_leaves_asset_retryable(
    db_session_factory: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Cleanup failures should be logged and the asset should remain pending."""

    class FailingStorage(MediaStorage):
        def delete(self, storage_path: str) -> None:
            raise RuntimeError(f"boom:{storage_path}")

    service = MediaCleanupService(
        storage=FailingStorage(),
        settings=build_settings(),
    )

    with db_session_factory() as session:
        asset = persist_due_asset(
            session,
            lifecycle_state=MediaLifecycleState.PENDING_DELETE,
            storage_path="video-uploads/test/clip.mp4",
            cleanup_after_delta_seconds=-1,
        )
        caplog.set_level(logging.INFO)
        summary = service.run_once(session)
        session.refresh(asset)

        assert summary.processed == 0
        assert summary.failed == 1
        assert asset.lifecycle_state is MediaLifecycleState.PENDING_DELETE
        assert any(
            record.name == LOGGER.name and "Media cleanup failed for asset_id=" in record.message
            for record in caplog.records
        )
