"""Posts CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.posts.exceptions import PostNotFoundError
from app.posts.schemas import (
    DeletePostResponse,
    PostCreate,
    PostListResponse,
    PostResponse,
    PostUpdate,
)
from app.posts.service import PostService

router = APIRouter()


def get_post_service() -> PostService:
    """Return a posts service instance."""

    return PostService()


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create post",
    description="Create a new post.",
    operation_id="createPost",
)
def create_post(
    payload: PostCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Create a post."""

    return service.create_post(session, payload)


@router.get(
    "",
    response_model=PostListResponse,
    summary="List posts",
    description="Return a paginated list of posts.",
    operation_id="listPosts",
)
def list_posts(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> PostListResponse:
    """List posts."""

    return service.list_posts(session, page=page, limit=limit)


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Get post",
    description="Return a post by id.",
    operation_id="getPostById",
)
def get_post(
    post_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Get a post by id."""

    try:
        return service.get_post(session, post_id)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
    summary="Update post",
    description="Apply partial updates to a post.",
    operation_id="updatePost",
)
def update_post(
    post_id: UUID,
    payload: PostUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Update a post."""

    try:
        return service.update_post(session, post_id, payload)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{post_id}",
    response_model=DeletePostResponse,
    summary="Delete post",
    description="Delete a post by id.",
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
    return DeletePostResponse(message="Post deleted successfully")
