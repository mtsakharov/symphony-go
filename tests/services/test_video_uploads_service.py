"""Unit tests for the video upload service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.video_uploads.exceptions import VideoUploadValidationError
from app.video_uploads.models import VideoUpload
from app.video_uploads.repository import VideoUploadRepository
from app.video_uploads.schemas import (
    VideoAssetInput,
    VideoUploadCreateRequest,
    VideoUploadFailureCode,
)
from app.video_uploads.service import VideoUploadService


def build_settings() -> Settings:
    """Return test settings with explicit video upload limits."""

    return Settings(
        database_url="sqlite:///./test.db",
        video_upload_allowed_mime_types=("video/mp4",),
        video_upload_allowed_codecs=("h264",),
        video_upload_max_size_bytes=100_000_000,
        video_upload_max_duration_seconds=180,
        video_upload_storage_prefix="video-uploads",
    )


def build_request(**asset_overrides: object) -> VideoUploadCreateRequest:
    """Return a valid upload initiation payload."""

    asset = {
        "filename": "clip.mp4",
        "mime_type": "video/mp4",
        "codec": "h264",
        "file_size_bytes": 5_000_000,
        "duration_seconds": 45,
    }
    asset.update(asset_overrides)
    return VideoUploadCreateRequest(assets=[VideoAssetInput.model_validate(asset)])


def test_initiate_upload_creates_pending_record() -> None:
    """The service should persist and serialize a pending upload intent."""

    repository = Mock(spec=VideoUploadRepository)
    service = VideoUploadService(repository=repository, settings=build_settings())
    session = Mock()

    def assign_persisted_fields(_: Mock, *, upload: VideoUpload) -> None:
        upload.id = uuid4()
        now = datetime.now(UTC)
        upload.created_at = now
        upload.updated_at = now

    repository.create.side_effect = assign_persisted_fields

    response = service.initiate_upload(session, build_request())

    assert response.status.value == "pending_upload"
    assert response.upload_path.startswith("video-uploads/")
    assert response.upload_path.endswith("/clip.mp4")
    assert response.asset.mime_type == "video/mp4"
    assert response.asset.codec == "h264"
    session.commit.assert_called_once()
    session.refresh.assert_called_once()


@pytest.mark.parametrize(
    ("asset_overrides", "expected_code"),
    [
        (
            {"mime_type": "video/quicktime", "codec": "hevc"},
            VideoUploadFailureCode.UNSUPPORTED_FORMAT,
        ),
        ({"file_size_bytes": 100_000_001}, VideoUploadFailureCode.FILE_TOO_LARGE),
        ({"duration_seconds": 181}, VideoUploadFailureCode.DURATION_TOO_LONG),
    ],
)
def test_initiate_upload_rejects_invalid_assets(
    asset_overrides: dict[str, object],
    expected_code: VideoUploadFailureCode,
) -> None:
    """Invalid assets should fail before persistence."""

    repository = Mock(spec=VideoUploadRepository)
    service = VideoUploadService(repository=repository, settings=build_settings())
    session = Mock()

    with pytest.raises(VideoUploadValidationError) as exc_info:
        service.initiate_upload(session, build_request(**asset_overrides))

    assert exc_info.value.code is expected_code
    repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_initiate_upload_rejects_more_than_one_asset() -> None:
    """The service should enforce the single-asset contract."""

    repository = Mock(spec=VideoUploadRepository)
    service = VideoUploadService(repository=repository, settings=build_settings())
    session = Mock()
    request = VideoUploadCreateRequest(
        assets=[
            VideoAssetInput(
                filename="clip.mp4",
                mime_type="video/mp4",
                codec="h264",
                file_size_bytes=5_000_000,
                duration_seconds=45,
            ),
            VideoAssetInput(
                filename="clip-2.mp4",
                mime_type="video/mp4",
                codec="h264",
                file_size_bytes=5_000_000,
                duration_seconds=45,
            ),
        ]
    )

    with pytest.raises(VideoUploadValidationError) as exc_info:
        service.initiate_upload(session, request)

    assert exc_info.value.code is VideoUploadFailureCode.INVALID_ASSET_COUNT
