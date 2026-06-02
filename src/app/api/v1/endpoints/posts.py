"""Posts CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.posts.exceptions import PostAuthorNotFoundError, PostIndexSyncError, PostNotFoundError
from app.posts.schemas import DeletePostResponse, PostCreate, PostUpdate, PostWithIndexResponse
from app.posts.service import PostService

router = APIRouter()


def get_post_service() -> PostService:
    """Return a posts service instance."""

    return PostService()


@router.post(
    "",
    response_model=PostWithIndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create post",
    description="Create a new post and synchronize its index record.",
    operation_id="createPost",
)
def create_post(
    payload: PostCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostWithIndexResponse:
    """Create a post."""

    try:
        return service.create_post(session, payload)
    except PostAuthorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PostIndexSyncError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get(
    "/{post_id}",
    response_model=PostWithIndexResponse,
    summary="Get post",
    description="Return a post by id, including its current index state.",
    operation_id="getPostById",
)
def get_post(
    post_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostWithIndexResponse:
    """Get a post by id."""

    try:
        return service.get_post(session, post_id)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/{post_id}",
    response_model=PostWithIndexResponse,
    summary="Update post",
    description="Apply partial updates to a post and refresh its index record.",
    operation_id="updatePost",
)
def update_post(
    post_id: UUID,
    payload: PostUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostWithIndexResponse:
    """Update a post."""

    try:
        return service.update_post(session, post_id, payload)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PostIndexSyncError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{post_id}",
    response_model=DeletePostResponse,
    summary="Delete post",
    description="Delete a post and invalidate its index record.",
    operation_id="deletePost",
)
def delete_post(
    post_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> DeletePostResponse:
    """Delete a post."""

    try:
        service.delete_post(session, post_id)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PostIndexSyncError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return DeletePostResponse(message="Post deleted successfully")
