"""Service layer for video assets."""

from __future__ import annotations

from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session, sessionmaker

from app.assets.models import VideoAsset
from app.assets.pipeline import (
    VideoProcessingFailure,
    VideoProcessingResult,
    VideoTranscodePipeline,
)
from app.assets.repository import VideoAssetRepository
from app.assets.schemas import (
    VideoAssetResponse,
    VideoAssetStatus,
    VideoAssetUploadComplete,
)


class VideoAssetNotFoundError(Exception):
    """Raised when a video asset does not exist."""


class VideoAssetProcessor:
    """Apply asynchronous processing transitions for uploaded video assets."""

    def __init__(
        self,
        *,
        repository: VideoAssetRepository,
        pipeline: VideoTranscodePipeline,
        session_factory: sessionmaker[Session],
    ) -> None:
        self.repository = repository
        self.pipeline = pipeline
        self.session_factory = session_factory

    def process_video_asset(self, asset_id: UUID) -> None:
        """Move a video asset from processing to ready or failed."""

        with self.session_factory() as session:
            asset = self.repository.get_by_id(session, asset_id)
            if asset is None:
                return

            try:
                result = self.pipeline.transcode(asset)
            except VideoProcessingFailure as exc:
                self._mark_failed(asset, reason=exc.reason)
            else:
                self._mark_ready(asset, result=result)

            session.add(asset)
            session.commit()

    def _mark_ready(self, asset: VideoAsset, *, result: VideoProcessingResult) -> None:
        """Persist the playable metadata for a successful transcode."""

        asset.status = VideoAssetStatus.READY.value
        asset.is_playable = True
        asset.playback_metadata = result.playback_metadata
        asset.poster_metadata = result.poster_metadata
        asset.thumbnail_metadata = result.thumbnail_metadata
        asset.failure_reason = None

    def _mark_failed(self, asset: VideoAsset, *, reason: str) -> None:
        """Persist an unplayable failed state."""

        asset.status = VideoAssetStatus.FAILED.value
        asset.is_playable = False
        asset.playback_metadata = None
        asset.poster_metadata = None
        asset.thumbnail_metadata = None
        asset.failure_reason = reason


class VideoAssetService:
    """Business logic for creating and reading video assets."""

    def __init__(
        self,
        *,
        repository: VideoAssetRepository,
        processor: VideoAssetProcessor,
    ) -> None:
        self.repository = repository
        self.processor = processor

    def create_video_asset(
        self,
        session: Session,
        payload: VideoAssetUploadComplete,
        background_tasks: BackgroundTasks,
    ) -> VideoAssetResponse:
        """Persist an uploaded video asset and schedule async processing."""

        asset = VideoAsset(
            source_key=payload.source_key,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            status=VideoAssetStatus.PROCESSING.value,
            is_playable=False,
        )
        self.repository.create(session, asset=asset)
        session.commit()
        session.refresh(asset)

        background_tasks.add_task(self.processor.process_video_asset, asset.id)
        return VideoAssetResponse.model_validate(asset)

    def get_video_asset(self, session: Session, asset_id: UUID) -> VideoAssetResponse:
        """Return a serialized video asset by id."""

        asset = self.repository.get_by_id(session, asset_id)
        if asset is None:
            raise VideoAssetNotFoundError("Video asset not found")
        return VideoAssetResponse.model_validate(asset)
