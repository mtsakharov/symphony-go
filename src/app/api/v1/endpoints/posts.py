"""Feed and post detail endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.posts.exceptions import PostNotFoundError
from app.posts.schemas import FeedResponse, PostDetailResponse
from app.posts.service import PostService

router = APIRouter()


def get_post_service() -> PostService:
    """Return a posts service instance."""

    return PostService()


@router.get(
    "/feed",
    response_model=FeedResponse,
    summary="List feed",
    description="Return a paginated feed of posts including additive video metadata.",
    operation_id="listFeed",
)
def list_feed(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> FeedResponse:
    """List feed posts."""

    return service.list_feed(session, page=page, limit=limit)


@router.get(
    "/posts/{post_id}",
    response_model=PostDetailResponse,
    summary="Get post",
    description="Return a single post including additive video metadata.",
    operation_id="getPostById",
)
def get_post(
    post_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostDetailResponse:
    """Get a post by id."""

    try:
        return service.get_post(session, post_id)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
