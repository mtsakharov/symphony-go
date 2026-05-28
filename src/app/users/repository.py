"""Repository layer for users."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.users.models import User


class UserRepository:
    """Persist and query users."""

    def get_by_id(self, session: Session, user_id: UUID) -> User | None:
        """Return a user by id if present."""

        return session.get(User, user_id)

    def get_by_email(self, session: Session, email: str) -> User | None:
        """Return a user by email if present."""

        statement = select(User).where(User.email == email)
        return session.execute(statement).scalar_one_or_none()

    def list_users(
        self,
        session: Session,
        *,
        offset: int,
        limit: int,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> list[User]:
        """Return a page of users ordered by creation time."""

        statement = (
            self._apply_filters(select(User), search=search, is_active=is_active)
            .order_by(User.created_at.desc(), User.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(statement).scalars().all())

    def count_users(
        self,
        session: Session,
        *,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        """Return the total number of users."""

        statement = self._apply_filters(
            select(func.count()).select_from(User),
            search=search,
            is_active=is_active,
        )
        return int(session.execute(statement).scalar_one())

    def create(self, session: Session, *, user: User) -> User:
        """Persist a new user."""

        session.add(user)
        session.flush()
        return user

    def delete(self, session: Session, *, user: User) -> None:
        """Delete an existing user."""

        session.delete(user)
        session.flush()

    @staticmethod
    def _apply_filters(
        statement: Any,
        *,
        search: str | None,
        is_active: bool | None,
    ) -> Any:
        """Apply optional search and status filters to a users query."""

        if search is not None:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    User.email.ilike(pattern),
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                )
            )

        if is_active is not None:
            statement = statement.where(User.is_active.is_(is_active))

        return statement
