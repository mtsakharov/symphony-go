"""Unit tests for the users service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.users.exceptions import UserEmailConflictError, UserNotFoundError
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate, UserUpdate
from app.users.service import UserService


def build_user(*, email: str = "user@example.com") -> User:
    """Return a hydrated user model for service tests."""

    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        email=email,
        first_name="John",
        last_name="Doe",
        password_hash="",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_create_user_raises_conflict_when_email_exists() -> None:
    """Service should raise a domain error for duplicate emails."""

    repository = Mock(spec=UserRepository)
    repository.get_by_email.return_value = build_user()
    service = UserService(repository=repository)
    session = Mock()

    with pytest.raises(UserEmailConflictError, match="User with this email already exists"):
        service.create_user(
            session,
            UserCreate(email="user@example.com", first_name="John", last_name="Doe"),
        )


def test_get_user_raises_not_found_when_missing() -> None:
    """Service should raise a domain error when a user does not exist."""

    repository = Mock(spec=UserRepository)
    repository.get_by_id.return_value = None
    service = UserService(repository=repository)
    session = Mock()

    with pytest.raises(UserNotFoundError, match="User not found"):
        service.get_user(session, uuid4())


def test_update_user_updates_existing_user() -> None:
    """Service should apply partial updates to the loaded user."""

    repository = Mock(spec=UserRepository)
    user = build_user()
    repository.get_by_id.return_value = user
    repository.get_by_email.return_value = None
    service = UserService(repository=repository)
    session = Mock()

    response = service.update_user(
        session,
        user.id,
        UserUpdate(first_name="Jane", last_name="Smith", is_active=False),
    )

    assert response.first_name == "Jane"
    assert response.last_name == "Smith"
    assert response.is_active is False
    session.commit.assert_called_once()


def test_list_users_uses_page_and_limit_to_build_paginated_response() -> None:
    """Service should translate page inputs into repository pagination calls."""

    repository = Mock(spec=UserRepository)
    repository.list_users.return_value = [
        build_user(email="third@example.com"),
        build_user(email="second@example.com"),
    ]
    repository.count_users.return_value = 5
    service = UserService(repository=repository)
    session = Mock()

    response = service.list_users(session, page=3, limit=2)

    repository.list_users.assert_called_once_with(session, offset=4, limit=2)
    repository.count_users.assert_called_once_with(session)
    assert response.page == 3
    assert response.limit == 2
    assert response.total == 5
    assert [item.email for item in response.items] == ["third@example.com", "second@example.com"]


def test_list_users_returns_empty_items_for_empty_page() -> None:
    """Service should preserve pagination metadata for an empty page result."""

    repository = Mock(spec=UserRepository)
    repository.list_users.return_value = []
    repository.count_users.return_value = 5
    service = UserService(repository=repository)
    session = Mock()

    response = service.list_users(session, page=4, limit=2)

    repository.list_users.assert_called_once_with(session, offset=6, limit=2)
    repository.count_users.assert_called_once_with(session)
    assert response.page == 4
    assert response.limit == 2
    assert response.total == 5
    assert response.items == []
