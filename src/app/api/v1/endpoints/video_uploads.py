"""Video upload initiation endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.video_uploads.exceptions import VideoUploadValidationError
from app.video_uploads.schemas import (
    VideoUploadCreateRequest,
    VideoUploadErrorDetail,
    VideoUploadErrorResponse,
    VideoUploadResponse,
)
from app.video_uploads.service import VideoUploadService

router = APIRouter()


def get_video_upload_service() -> VideoUploadService:
    """Return a video upload service instance."""

    return VideoUploadService()


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
    description="Reserve a single validated video upload slot without creating a post.",
    operation_id="initiateVideoUpload",
)
def initiate_video_upload(
    payload: VideoUploadCreateRequest,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[VideoUploadService, Depends(get_video_upload_service)],
) -> VideoUploadResponse:
    """Create a pending upload intent for exactly one validated video asset."""

    try:
        return service.initiate_upload(session, payload)
    except VideoUploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=VideoUploadErrorDetail(code=exc.code, message=str(exc)).model_dump(),
        ) from exc
