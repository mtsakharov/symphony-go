"""Service layer for users."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access.exceptions import RoleNotFoundError
from app.access.models import Permission, Role
from app.access.repository import RoleRepository
from app.access.service import serialize_permission, serialize_role_summary
from app.users.exceptions import UserEmailConflictError, UserNotFoundError
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate, UserListResponse, UserResponse, UserUpdate


def serialize_user(user: User) -> UserResponse:
    """Return an API response model for a user."""

    roles = sorted(user.roles, key=lambda role: (role.name, str(role.id)))
    permissions_by_id: dict[UUID, Permission] = {}
    for role in roles:
        for permission in role.permissions:
            permissions_by_id[permission.id] = permission

    permissions = sorted(
        permissions_by_id.values(),
        key=lambda permission: (permission.name, str(permission.id)),
    )
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        roles=[serialize_role_summary(role) for role in roles],
        permissions=[serialize_permission(permission) for permission in permissions],
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


class UserService:
    """Business logic for user CRUD operations."""

    def __init__(
        self,
        repository: UserRepository | None = None,
        role_repository: RoleRepository | None = None,
    ) -> None:
        self.repository = repository or UserRepository()
        self.role_repository = role_repository or RoleRepository()

    def create_user(self, session: Session, payload: UserCreate) -> UserResponse:
        """Create a new user if the email is unique."""

        email = str(payload.email)
        if self.repository.get_by_email(session, email) is not None:
            raise UserEmailConflictError("User with this email already exists")

        user = User(
            email=email,
            first_name=payload.first_name,
            last_name=payload.last_name,
            roles=self._get_roles_or_raise(session, payload.role_ids),
        )

        try:
            self.repository.create(session, user=user)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise UserEmailConflictError("User with this email already exists") from exc

        session.refresh(user)
        return serialize_user(user)

    def list_users(self, session: Session, *, page: int, limit: int) -> UserListResponse:
        """Return a paginated list of users."""

        offset = (page - 1) * limit
        users = self.repository.list_users(session, offset=offset, limit=limit)
        total = self.repository.count_users(session)
        return UserListResponse(
            items=[serialize_user(user) for user in users],
            page=page,
            limit=limit,
            total=total,
        )

    def get_user(self, session: Session, user_id: UUID) -> UserResponse:
        """Return a single user or raise if absent."""

        user = self.repository.get_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError("User not found")
        return serialize_user(user)

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
            if field_name == "role_ids":
                continue
            setattr(user, field_name, value)

        if payload.role_ids is not None:
            user.roles = self._get_roles_or_raise(session, payload.role_ids)

        try:
            session.add(user)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise UserEmailConflictError("User with this email already exists") from exc

        session.refresh(user)
        return serialize_user(user)

    def delete_user(self, session: Session, user_id: UUID) -> None:
        """Delete a user by id."""

        user = self.repository.get_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError("User not found")

        self.repository.delete(session, user=user)
        session.commit()

    def _get_roles_or_raise(self, session: Session, role_ids: list[UUID]) -> list[Role]:
        """Resolve role ids or raise if any are missing."""

        roles = self.role_repository.list_by_ids(session, role_ids)
        missing_ids = [
            str(role_id)
            for role_id in role_ids
            if all(role.id != role_id for role in roles)
        ]
        if missing_ids:
            missing_ids.sort()
            raise RoleNotFoundError(f"Roles not found: {', '.join(missing_ids)}")
        return roles
