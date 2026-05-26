"""Service layer for users."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.users.exceptions import UserEmailConflictError, UserNotFoundError
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate, UserListResponse, UserResponse, UserUpdate


class UserService:
    """Business logic for user CRUD operations."""

    def __init__(self, repository: UserRepository | None = None) -> None:
        self.repository = repository or UserRepository()

    def create_user(self, session: Session, payload: UserCreate) -> UserResponse:
        """Create a new user if the email is unique."""

        email = str(payload.email)
        if self.repository.get_by_email(session, email) is not None:
            raise UserEmailConflictError("User with this email already exists")

        user = User(
            email=email,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )

        try:
            self.repository.create(session, user=user)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise UserEmailConflictError("User with this email already exists") from exc

        session.refresh(user)
        return UserResponse.model_validate(user)

    def list_users(self, session: Session, *, page: int, limit: int) -> UserListResponse:
        """Return a paginated list of users."""

        offset = (page - 1) * limit
        users = self.repository.list_users(session, offset=offset, limit=limit)
        total = self.repository.count_users(session)
        return UserListResponse(
            items=[UserResponse.model_validate(user) for user in users],
            page=page,
            limit=limit,
            total=total,
        )

    def get_user(self, session: Session, user_id: UUID) -> UserResponse:
        """Return a single user or raise if absent."""

        user = self.repository.get_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError("User not found")
        return UserResponse.model_validate(user)

    def update_user(self, session: Session, user_id: UUID, payload: UserUpdate) -> UserResponse:
        """Apply partial updates to a user."""

        user = self.repository.get_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError("User not found")

        if payload.email is not None:
            email = str(payload.email)
            existing_user = self.repository.get_by_email(session, email)
            if existing_user is not None and existing_user.id != user.id:
                raise UserEmailConflictError("User with this email already exists")
            user.email = email

        update_data = payload.model_dump(exclude_unset=True, exclude={"email"})
        for field_name, value in update_data.items():
            setattr(user, field_name, value)

        try:
            session.add(user)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise UserEmailConflictError("User with this email already exists") from exc

        session.refresh(user)
        return UserResponse.model_validate(user)

    def delete_user(self, session: Session, user_id: UUID) -> None:
        """Delete a user by id."""

        user = self.repository.get_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError("User not found")

        self.repository.delete(session, user=user)
        session.commit()
