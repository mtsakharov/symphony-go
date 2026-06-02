"""Endpoints for per-user post indexing."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db_session
from app.post_indexing.schemas import PostIndexingSummary
from app.post_indexing.service import UserPostIndexingService

router = APIRouter()


def get_post_indexing_service() -> UserPostIndexingService:
    """Return a post indexing service instance."""

    settings = get_settings()
    return UserPostIndexingService(
        max_chunk_size=settings.post_index_chunk_size,
    )


@router.post(
    "/{user_id}/posts/index",
    response_model=PostIndexingSummary,
    status_code=status.HTTP_200_OK,
    summary="Index a user's posts",
    description="Index the eligible posts owned by a single user.",
    operation_id="indexUserPosts",
)
def index_user_posts(
    user_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[UserPostIndexingService, Depends(get_post_indexing_service)],
) -> PostIndexingSummary:
    """Trigger per-user post indexing."""

    return service.index_user_posts(session, user_id)
