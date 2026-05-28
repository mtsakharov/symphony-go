"""Media upload and management endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.media.exceptions import (
    EmptyMediaFileError,
    FileTooLargeError,
    InvalidMediaFilenameError,
    MediaNotFoundError,
    MediaStorageError,
    UnsupportedMediaTypeError,
)
from app.media.schemas import DeleteMediaResponse, ErrorResponse, MediaListResponse, MediaResponse
from app.media.service import MediaService
from app.media.storage import LocalMediaStorage, MediaStorage

router = APIRouter()


def get_media_storage(
    settings: Annotated[Settings, Depends(get_settings)],
) -> MediaStorage:
    """Return the configured media storage implementation."""

    return LocalMediaStorage(
        storage_dir=settings.media_storage_dir,
        public_url_prefix=settings.media_public_url_prefix,
    )


def get_media_service(
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[MediaStorage, Depends(get_media_storage)],
) -> MediaService:
    """Return a media service instance."""

    return MediaService(settings=settings, storage=storage)


@router.post(
    "/upload",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload media",
    description=(
        "Upload a media asset using multipart form data. The `file` field must contain a "
        "supported image or PDF payload and is validated against configured size limits."
    ),
    operation_id="uploadMedia",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid upload payload.",
            "content": {
                "application/json": {
                    "example": {"detail": "Uploaded file must include a valid filename"}
                }
            },
        },
        413: {
            "model": ErrorResponse,
            "description": "Uploaded file exceeds the configured limit.",
            "content": {
                "application/json": {
                    "example": {"detail": "File exceeds the maximum allowed size of 1024 bytes"}
                }
            },
        },
        415: {
            "model": ErrorResponse,
            "description": "Unsupported file content type.",
            "content": {
                "application/json": {"example": {"detail": "Unsupported media type"}}
            },
        },
        500: {
            "model": ErrorResponse,
            "description": "Media storage or persistence failure.",
            "content": {
                "application/json": {"example": {"detail": "Failed to store uploaded file"}}
            },
        },
    },
)
async def upload_media(
    file: Annotated[
        UploadFile,
        File(
            description=(
                "Binary file payload. Example multipart form field: "
                "`file=@photo.png;type=image/png`."
            )
        ),
    ],
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[MediaService, Depends(get_media_service)],
) -> MediaResponse:
    """Upload a media file and store its metadata."""

    try:
        return await service.create_media(session, file)
    except UnsupportedMediaTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except (EmptyMediaFileError, InvalidMediaFilenameError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except MediaStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=MediaListResponse,
    summary="List media",
    description="Return a paginated list of uploaded media metadata.",
    operation_id="listMedia",
)
def list_media(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[MediaService, Depends(get_media_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> MediaListResponse:
    """List uploaded media."""

    return service.list_media(session, page=page, limit=limit)


@router.get(
    "/{media_id}",
    response_model=MediaResponse,
    summary="Get media metadata",
    description="Return media metadata by id.",
    operation_id="getMediaById",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Media record was not found.",
            "content": {"application/json": {"example": {"detail": "Media not found"}}},
        }
    },
)
def get_media(
    media_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[MediaService, Depends(get_media_service)],
) -> MediaResponse:
    """Return media metadata by id."""

    try:
        return service.get_media(session, media_id)
    except MediaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{media_id}",
    response_model=DeleteMediaResponse,
    summary="Delete media",
    description="Delete a media record and its stored file.",
    operation_id="deleteMedia",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Media record was not found.",
            "content": {"application/json": {"example": {"detail": "Media not found"}}},
        },
        500: {
            "model": ErrorResponse,
            "description": "Media storage cleanup failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to delete stored file"}}
            },
        },
    },
)
async def delete_media(
    media_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[MediaService, Depends(get_media_service)],
) -> DeleteMediaResponse:
    """Delete media by id."""

    try:
        await service.delete_media(session, media_id)
    except MediaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MediaStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return DeleteMediaResponse(message="Media deleted successfully")
