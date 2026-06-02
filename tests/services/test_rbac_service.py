"""Service tests for RBAC operations."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.rbac.exceptions import (
    RbacUserNotFoundError,
    RoleNameConflictError,
    UserRoleConflictError,
)
from app.rbac.schemas import RoleCreate
from app.rbac.service import RbacService
from app.users.models import User


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


def test_create_role_raises_conflict_when_name_exists(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Service should raise a domain error for duplicate role names."""

    service = RbacService()

    with db_session_factory() as session:
        created_role = service.create_role(
            session,
            RoleCreate(name="viewer", description="Read-only access"),
        )

        assert created_role.name == "viewer"

        with pytest.raises(RoleNameConflictError, match="Role with this name already exists"):
            service.create_role(
                session,
                RoleCreate(name="viewer", description="Another description"),
            )


def test_assign_and_remove_permission_from_role(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Service should manage role-permission assignments."""

    service = RbacService()

    with db_session_factory() as session:
        created_role = service.create_role(
            session,
            RoleCreate(name="auditor", description="Audit access"),
        )
        permissions = service.list_permissions(session)
        users_read = next(
            permission for permission in permissions.items if permission.code == "users:read"
        )

        updated_role = service.assign_permission_to_role(session, created_role.id, users_read.id)
        assert {permission.code for permission in updated_role.permissions} == {"users:read"}

        updated_role = service.remove_permission_from_role(session, created_role.id, users_read.id)
        assert updated_role.permissions == []


def test_assign_and_remove_role_from_user(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Service should manage user-role assignments."""

    service = RbacService()

    with db_session_factory() as session:
        user = build_user(email="member@example.com")
        session.add(user)
        session.commit()

        role = service.create_role(session, RoleCreate(name="member", description="Member role"))

        assignment = service.assign_role_to_user(session, user.id, role.id)
        assert assignment.user_id == user.id
        assert [assigned_role.name for assigned_role in assignment.items] == ["member"]

        with pytest.raises(UserRoleConflictError, match="Role is already assigned to this user"):
            service.assign_role_to_user(session, user.id, role.id)

        assignment = service.remove_role_from_user(session, user.id, role.id)
        assert assignment.items == []


def test_get_effective_permission_codes_resolves_permissions(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Service should resolve effective permissions through assigned roles."""

    service = RbacService()

    with db_session_factory() as session:
        user = build_user(email="operator@example.com")
        session.add(user)
        session.commit()

        role = service.create_role(
            session, RoleCreate(name="operator", description="Operator role")
        )
        permissions = service.list_permissions(session)
        users_update = next(
            permission for permission in permissions.items if permission.code == "users:update"
        )

        service.assign_permission_to_role(session, role.id, users_update.id)
        service.assign_role_to_user(session, user.id, role.id)

        effective_permissions = service.get_effective_permission_codes(session, user.id)
        assert effective_permissions == {"users:update"}


def test_list_user_roles_raises_not_found_for_missing_user(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Service should raise a domain error when the target user is absent."""

    service = RbacService()

    with db_session_factory() as session, pytest.raises(
        RbacUserNotFoundError, match="User not found"
    ):
        service.list_user_roles(session, uuid4())
