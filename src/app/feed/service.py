"""Service layer for feed reads."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.feed.repository import FeedRepository
from app.feed.schemas import FeedItemListResponse, FeedItemResponse
from app.users.exceptions import UserNotFoundError
from app.users.repository import UserRepository


class FeedService:
    """Business logic for user feed lookups."""

    def __init__(
        self,
        repository: FeedRepository | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self.repository = repository or FeedRepository()
        self.user_repository = user_repository or UserRepository()

    def list_user_feed(
        self,
        session: Session,
        user_id: UUID,
        *,
        page: int,
        limit: int,
    ) -> FeedItemListResponse:
        """Return a paginated feed for a user."""

        if self.user_repository.get_by_id(session, user_id) is None:
            raise UserNotFoundError("User not found")

        offset = (page - 1) * limit
        items = self.repository.list_feed_items(
            session,
            user_id=user_id,
            offset=offset,
            limit=limit,
        )
        total = self.repository.count_feed_items(session, user_id=user_id)

        return FeedItemListResponse(
            items=[FeedItemResponse.model_validate(item) for item in items],
            page=page,
            limit=limit,
            total=total,
        )
