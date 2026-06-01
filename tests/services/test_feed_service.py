"""Unit tests for the feed service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.feed.models import FeedItem
from app.feed.repository import FeedRepository
from app.feed.service import FeedService
from app.users.exceptions import UserNotFoundError
from app.users.models import User
from app.users.repository import UserRepository


def build_user(*, user_id: UUID | None = None, email: str = "user@example.com") -> User:
    """Return a hydrated user model for service tests."""

    now = datetime.now(UTC)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="John",
        last_name="Doe",
        password_hash="",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def build_feed_item(
    *,
    user_id: UUID,
    title: str = "Feed title",
    body: str = "Feed body",
    created_at: datetime | None = None,
) -> FeedItem:
    """Return a hydrated feed item model for service tests."""

    return FeedItem(
        id=uuid4(),
        user_id=user_id,
        title=title,
        body=body,
        created_at=created_at or datetime.now(UTC),
    )


def test_list_user_feed_raises_not_found_when_user_missing() -> None:
    """Service should raise a domain error when a user does not exist."""

    repository = Mock(spec=FeedRepository)
    user_repository = Mock(spec=UserRepository)
    user_repository.get_by_id.return_value = None
    service = FeedService(repository=repository, user_repository=user_repository)
    session = Mock()

    with pytest.raises(UserNotFoundError, match="User not found"):
        service.list_user_feed(session, uuid4(), page=1, limit=20)


def test_list_user_feed_applies_pagination_and_serializes_results() -> None:
    """Service should calculate offsets and serialize feed items."""

    repository = Mock(spec=FeedRepository)
    user = build_user()
    repository.list_feed_items.return_value = [
        build_feed_item(user_id=user.id, title="Newest"),
        build_feed_item(user_id=user.id, title="Older"),
    ]
    repository.count_feed_items.return_value = 7
    user_repository = Mock(spec=UserRepository)
    user_repository.get_by_id.return_value = user
    service = FeedService(repository=repository, user_repository=user_repository)
    session = Mock()

    response = service.list_user_feed(session, user.id, page=2, limit=3)

    repository.list_feed_items.assert_called_once_with(
        session,
        user_id=user.id,
        offset=3,
        limit=3,
    )
    repository.count_feed_items.assert_called_once_with(session, user_id=user.id)
    assert response.page == 2
    assert response.limit == 3
    assert response.total == 7
    assert [item.title for item in response.items] == ["Newest", "Older"]
