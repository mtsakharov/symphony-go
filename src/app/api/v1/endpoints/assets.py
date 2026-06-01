"""Video asset processing endpoints."""

from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, sessionmaker

from app.assets.pipeline import DeterministicVideoTranscodePipeline, VideoTranscodePipeline
from app.assets.repository import VideoAssetRepository
from app.assets.schemas import VideoAssetResponse, VideoAssetUploadComplete
from app.assets.service import VideoAssetNotFoundError, VideoAssetProcessor, VideoAssetService
from app.database.session import get_db_session, get_session_factory

router = APIRouter()


def get_asset_session_factory(request: Request) -> sessionmaker[Session]:
    """Return the session factory used by background processing."""

    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        return get_session_factory()
    return cast(sessionmaker[Session], session_factory)


def get_video_pipeline(request: Request) -> VideoTranscodePipeline:
    """Return the configured video processing pipeline."""

    pipeline = getattr(request.app.state, "video_pipeline", None)
    if pipeline is None:
        pipeline = DeterministicVideoTranscodePipeline()
        request.app.state.video_pipeline = pipeline
    return cast(VideoTranscodePipeline, pipeline)


def get_video_asset_service(request: Request) -> VideoAssetService:
    """Return a video asset service bound to the current app dependencies."""

    repository = VideoAssetRepository()
    processor = VideoAssetProcessor(
        repository=repository,
        pipeline=get_video_pipeline(request),
        session_factory=get_asset_session_factory(request),
    )
    return VideoAssetService(repository=repository, processor=processor)


@router.post(
    "/upload-complete",
    response_model=VideoAssetResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Register completed video upload",
    description="Persist a video asset in processing state and trigger async transcoding.",
    operation_id="registerVideoUploadComplete",
)
def create_video_asset(
    payload: VideoAssetUploadComplete,
    background_tasks: BackgroundTasks,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[VideoAssetService, Depends(get_video_asset_service)],
) -> VideoAssetResponse:
    """Create a new video asset and enqueue processing."""

    return service.create_video_asset(session, payload, background_tasks)


@router.get(
    "/{asset_id}",
    response_model=VideoAssetResponse,
    summary="Get video asset",
    description="Return the current processing state and metadata for a video asset.",
    operation_id="getVideoAssetById",
)
def get_video_asset(
    asset_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[VideoAssetService, Depends(get_video_asset_service)],
) -> VideoAssetResponse:
    """Get a video asset by id."""

    try:
        return service.get_video_asset(session, asset_id)
    except VideoAssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
