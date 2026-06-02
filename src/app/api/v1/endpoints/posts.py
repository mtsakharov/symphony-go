"""Video post endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.posts.exceptions import PostNotFoundError, PostValidationError
from app.posts.schemas import PostCreate, PostResponse
from app.posts.service import PostService

router = APIRouter()


def get_post_service() -> PostService:
    """Return a post service instance."""

    return PostService()


@router.get(
    "",
    response_model=list[PostResponse],
    summary="List posts",
    description="Return visible posts only.",
    operation_id="listPosts",
)
def list_posts(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> list[PostResponse]:
    """Return visible posts."""

    return service.list_posts(session)


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create post",
    description="Create a video post from a completed upload.",
    operation_id="createPost",
)
def create_post(
    payload: PostCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Create a post."""

    try:
        return service.create_post(session, payload)
    except PostValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Get post",
    description="Return a visible post by id.",
    operation_id="getPost",
)
def get_post(
    post_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Get a post."""

    try:
        return service.get_post(session, post_id)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete post",
    description="Hide a video post and schedule its owned media for cleanup.",
    operation_id="deletePost",
)
def delete_post(
    post_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> dict[str, str]:
    """Delete a post."""

    service.delete_post(session, post_id)
    return {"message": "Post deleted successfully"}
