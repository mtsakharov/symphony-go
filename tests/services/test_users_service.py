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


def test_create_user_normalizes_email_before_lookup_and_persistence() -> None:
    """Service should canonicalize emails before checking uniqueness and saving."""

    repository = Mock(spec=UserRepository)
    repository.get_by_email.return_value = None
    service = UserService(repository=repository)
    session = Mock()

    def refresh_user(user: User) -> None:
        hydrated_user = build_user(email=user.email)
        user.id = hydrated_user.id
        user.is_active = hydrated_user.is_active
        user.created_at = hydrated_user.created_at
        user.updated_at = hydrated_user.updated_at

    session.refresh.side_effect = refresh_user

    response = service.create_user(
        session,
        UserCreate(email="User.Name@Example.COM", first_name="John", last_name="Doe"),
    )

    repository.get_by_email.assert_called_once_with(session, "user.name@example.com")
    created_user = repository.create.call_args.kwargs["user"]
    assert created_user.email == "user.name@example.com"
    assert response.email == "user.name@example.com"


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


def test_update_user_normalizes_email_before_uniqueness_check() -> None:
    """Service should normalize updated email addresses before validation."""

    repository = Mock(spec=UserRepository)
    user = build_user()
    repository.get_by_id.return_value = user
    repository.get_by_email.return_value = None
    service = UserService(repository=repository)
    session = Mock()

    response = service.update_user(
        session,
        user.id,
        UserUpdate(email="Jane.Doe@Example.COM"),
    )

    repository.get_by_email.assert_called_once_with(session, "jane.doe@example.com")
    assert user.email == "jane.doe@example.com"
    assert response.email == "jane.doe@example.com"
