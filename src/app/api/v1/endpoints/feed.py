"""User feed read endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.feed.schemas import FeedItemListResponse
from app.feed.service import FeedService
from app.users.exceptions import UserNotFoundError

router = APIRouter()


def get_feed_service() -> FeedService:
    """Return a feed service instance."""

    return FeedService()


@router.get(
    "/{user_id}/feed",
    response_model=FeedItemListResponse,
    summary="List user feed",
    description="Return a paginated feed for a specific user.",
    operation_id="listUserFeed",
)
def list_user_feed(
    user_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[FeedService, Depends(get_feed_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> FeedItemListResponse:
    """List feed items for a user."""

    try:
        return service.list_user_feed(session, user_id, page=page, limit=limit)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
