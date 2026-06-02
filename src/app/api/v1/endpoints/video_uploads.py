"""Video upload lifecycle endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.media.exceptions import (
    MediaAssetNotFoundError,
    MediaLifecycleError,
    VideoUploadValidationError,
)
from app.media.schemas import (
    VideoUploadCreateRequest,
    VideoUploadErrorDetail,
    VideoUploadErrorResponse,
    VideoUploadResponse,
)
from app.media.service import MediaService

router = APIRouter()


def get_media_service() -> MediaService:
    """Return a media service instance."""

    return MediaService()


@router.post(
    "",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "The upload request failed server-side validation.",
            "model": VideoUploadErrorResponse,
        }
    },
    summary="Initiate video upload",
    description="Reserve a validated video upload slot without creating a visible post.",
    operation_id="initiateVideoUpload",
)
def initiate_video_upload(
    payload: VideoUploadCreateRequest,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[MediaService, Depends(get_media_service)],
) -> VideoUploadResponse:
    """Create a pending upload intent for a video asset."""

    try:
        return service.initiate_video_upload(session, payload)
    except VideoUploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=VideoUploadErrorDetail(code=exc.code, message=str(exc)).model_dump(),
        ) from exc


@router.post(
    "/{upload_id}/complete",
    response_model=VideoUploadResponse,
    summary="Complete video upload",
    description="Mark a pending upload as completed and ready for post creation.",
    operation_id="completeVideoUpload",
)
def complete_video_upload(
    upload_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[MediaService, Depends(get_media_service)],
) -> VideoUploadResponse:
    """Complete a reserved video upload."""

    try:
        return service.complete_video_upload(session, upload_id)
    except MediaAssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MediaLifecycleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

