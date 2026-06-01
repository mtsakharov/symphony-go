"""Unit tests for the video asset service."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session, sessionmaker

from app.assets.models import VideoAsset
from app.assets.pipeline import VideoProcessingFailure, VideoProcessingResult
from app.assets.repository import VideoAssetRepository
from app.assets.schemas import VideoAssetUploadComplete
from app.assets.service import VideoAssetProcessor, VideoAssetService


class SuccessfulVideoPipeline:
    """Pipeline double that returns fixed metadata."""

    def transcode(self, asset: VideoAsset) -> VideoProcessingResult:
        return VideoProcessingResult(
            playback_metadata={"playback_url": f"{asset.source_key}.m3u8"},
            poster_metadata={"url": f"{asset.source_key}.jpg"},
            thumbnail_metadata={"url": f"{asset.source_key}.thumb.jpg"},
        )


class FailingVideoPipeline:
    """Pipeline double that raises a machine-readable failure."""

    def transcode(self, asset: VideoAsset) -> VideoProcessingResult:
        raise VideoProcessingFailure("transcode_failed")


def build_service(
    db_session_factory: sessionmaker[Session],
    *,
    failing: bool = False,
) -> VideoAssetService:
    """Create a service with an injectable pipeline double."""

    repository = VideoAssetRepository()
    processor = VideoAssetProcessor(
        repository=repository,
        pipeline=FailingVideoPipeline() if failing else SuccessfulVideoPipeline(),
        session_factory=db_session_factory,
    )
    return VideoAssetService(repository=repository, processor=processor)


async def run_background_tasks(background_tasks: BackgroundTasks) -> None:
    """Execute scheduled background tasks."""

    await background_tasks()


def load_asset(session: Session, asset_id: UUID) -> VideoAsset:
    """Load a persisted asset from the database."""

    asset = session.get(VideoAsset, asset_id)
    assert asset is not None
    return asset


@pytest.mark.asyncio
async def test_create_video_asset_processes_ready_state(
    db_session_factory: sessionmaker[Session],
) -> None:
    """The service should persist ready metadata after successful processing."""

    service = build_service(db_session_factory)
    background_tasks = BackgroundTasks()

    with db_session_factory() as session:
        response = service.create_video_asset(
            session,
            VideoAssetUploadComplete(
                source_key="uploads/videos/example.mp4",
                file_name="example.mp4",
                mime_type="video/mp4",
            ),
            background_tasks,
        )

    await run_background_tasks(background_tasks)

    with db_session_factory() as session:
        asset = load_asset(session, response.id)
        assert asset.status == "ready"
        assert asset.is_playable is True
        assert asset.failure_reason is None
        assert asset.playback_metadata == {"playback_url": "uploads/videos/example.mp4.m3u8"}
        assert asset.poster_metadata == {"url": "uploads/videos/example.mp4.jpg"}
        assert asset.thumbnail_metadata == {"url": "uploads/videos/example.mp4.thumb.jpg"}


@pytest.mark.asyncio
async def test_create_video_asset_processes_failed_state(
    db_session_factory: sessionmaker[Session],
) -> None:
    """The service should persist a failed non-playable asset when transcoding fails."""

    service = build_service(db_session_factory, failing=True)
    background_tasks = BackgroundTasks()

    with db_session_factory() as session:
        response = service.create_video_asset(
            session,
            VideoAssetUploadComplete(
                source_key="uploads/videos/example.mp4",
                file_name="example.mp4",
                mime_type="video/mp4",
            ),
            background_tasks,
        )

    await run_background_tasks(background_tasks)

    with db_session_factory() as session:
        asset = load_asset(session, response.id)
        assert asset.status == "failed"
        assert asset.is_playable is False
        assert asset.failure_reason == "transcode_failed"
        assert asset.playback_metadata is None
        assert asset.poster_metadata is None
        assert asset.thumbnail_metadata is None
