"""Repository layer for users."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.rbac.models import UserRole
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

    def list_users(self, session: Session, *, offset: int, limit: int) -> list[User]:
        """Return a page of users ordered by creation time."""

        statement = (
            select(User)
            .order_by(User.created_at.desc(), User.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(statement).scalars().all())

    def count_users(self, session: Session) -> int:
        """Return the total number of users."""

        statement = select(func.count()).select_from(User)
        return int(session.execute(statement).scalar_one())

    def create(self, session: Session, *, user: User) -> User:
        """Persist a new user."""

        session.add(user)
        session.flush()
        return user

    def delete(self, session: Session, *, user: User) -> None:
        """Delete an existing user."""

        session.execute(delete(UserRole).where(UserRole.user_id == user.id))
        session.delete(user)
        session.flush()
