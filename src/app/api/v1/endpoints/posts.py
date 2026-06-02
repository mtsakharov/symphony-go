"""Post lifecycle endpoints."""

from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import get_db_session, get_session_factory
from app.posts.exceptions import (
    PostNotFoundError,
    PostValidationError,
    VideoUploadNotFoundError,
    VideoUploadValidationError,
)
from app.posts.pipeline import DeterministicVideoTranscodePipeline, VideoTranscodePipeline
from app.posts.repository import PostRepository
from app.posts.schemas import (
    PostCreate,
    PostResponse,
    VideoUploadCompleteRequest,
    VideoUploadCreateRequest,
    VideoUploadErrorDetail,
    VideoUploadErrorResponse,
    VideoUploadResponse,
)
from app.posts.service import PostService, VideoAssetProcessor
from app.users.exceptions import UserNotFoundError
from app.users.repository import UserRepository

router = APIRouter()


def get_post_session_factory(request: Request) -> sessionmaker[Session]:
    """Return the session factory used by background processing."""

    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        return get_session_factory()
    return cast(sessionmaker[Session], session_factory)


def get_video_pipeline(request: Request) -> VideoTranscodePipeline:
    """Return the configured transcode pipeline."""

    pipeline = getattr(request.app.state, "video_pipeline", None)
    if pipeline is None:
        pipeline = DeterministicVideoTranscodePipeline()
        request.app.state.video_pipeline = pipeline
    return cast(VideoTranscodePipeline, pipeline)


def get_post_service(request: Request) -> PostService:
    """Return a post service bound to the current app dependencies."""

    repository = PostRepository()
    processor = VideoAssetProcessor(
        repository=repository,
        pipeline=get_video_pipeline(request),
        session_factory=get_post_session_factory(request),
    )
    return PostService(
        repository=repository,
        user_repository=UserRepository(),
        processor=processor,
    )


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create post",
    description="Create a text post or a draft video post shell.",
    operation_id="createPost",
)
def create_post(
    payload: PostCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Create a post shell."""

    try:
        return service.create_post(session, payload)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PostValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{post_id}/video-uploads",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "The upload request failed server-side validation.",
            "model": VideoUploadErrorResponse,
        }
    },
    summary="Initiate video upload",
    description="Reserve a validated upload slot for a draft video post.",
    operation_id="initiateVideoUpload",
)
def initiate_video_upload(
    post_id: UUID,
    payload: VideoUploadCreateRequest,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> VideoUploadResponse:
    """Reserve a pending upload intent for a video post."""

    try:
        return service.initiate_video_upload(session, post_id=post_id, payload=payload)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except VideoUploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=VideoUploadErrorDetail(code=exc.code, message=str(exc)).model_dump(),
        ) from exc
    except PostValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{post_id}/video-uploads/{upload_id}/complete",
    response_model=PostResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Finalize video upload",
    description="Persist a processing video asset and trigger asynchronous transcoding.",
    operation_id="completeVideoUpload",
)
def complete_video_upload(
    post_id: UUID,
    upload_id: UUID,
    payload: VideoUploadCompleteRequest,
    background_tasks: BackgroundTasks,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Finalize a post upload and enqueue asset processing."""

    try:
        return service.complete_video_upload(
            session,
            background_tasks,
            post_id=post_id,
            upload_id=upload_id,
            payload=payload,
        )
    except (PostNotFoundError, VideoUploadNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PostValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Get post detail",
    description="Return the current post and video asset lifecycle state.",
    operation_id="getPostById",
)
def get_post(
    post_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Return a post detail response."""

    try:
        return service.get_post(session, post_id)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
