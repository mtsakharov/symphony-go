"""Feed read endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.v1.endpoints.posts import get_post_service
from app.database.session import get_db_session
from app.posts.schemas import PostListResponse
from app.posts.service import PostService
from app.users.exceptions import UserNotFoundError

router = APIRouter()


@router.get(
    "/users/{user_id}/feed",
    response_model=PostListResponse,
    summary="List user feed",
    description="Return a paginated post feed for a specific user.",
    operation_id="listUserFeed",
)
def list_user_feed(
    user_id: UUID,
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> PostListResponse:
    """Return a user's feed."""

    del request
    try:
        return service.list_user_feed(session, user_id=user_id, page=page, limit=limit)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
