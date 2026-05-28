"""Unit tests for role and permission services."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.access.exceptions import PermissionNotFoundError
from app.access.models import Permission, Role
from app.access.repository import PermissionRepository, RoleRepository
from app.access.schemas import RoleCreate, RoleUpdate
from app.access.service import RoleService


def build_permission(*, name: str = "users.read") -> Permission:
    """Return a hydrated permission model for service tests."""

    now = datetime.now(UTC)
    return Permission(
        id=uuid4(),
        name=name,
        description="Read users",
        created_at=now,
        updated_at=now,
    )


def build_role(*, name: str = "admin") -> Role:
    """Return a hydrated role model for service tests."""

    now = datetime.now(UTC)
    return Role(
        id=uuid4(),
        name=name,
        description="Administrators",
        permissions=[],
        created_at=now,
        updated_at=now,
    )


def test_create_role_raises_not_found_when_permission_missing() -> None:
    """Role creation should fail when a referenced permission does not exist."""

    repository = Mock(spec=RoleRepository)
    repository.get_by_name.return_value = None
    permission_repository = Mock(spec=PermissionRepository)
    permission_repository.list_by_ids.return_value = []
    service = RoleService(repository=repository, permission_repository=permission_repository)
    session = Mock()
    missing_id = uuid4()

    with pytest.raises(PermissionNotFoundError, match=str(missing_id)):
        service.create_role(
            session,
            RoleCreate(
                name="admin",
                description="Administrators",
                permission_ids=[missing_id],
            ),
        )


def test_update_role_replaces_permissions() -> None:
    """Role updates should replace the assigned permissions."""

    repository = Mock(spec=RoleRepository)
    role = build_role()
    repository.get_by_id.return_value = role
    repository.get_by_name.return_value = None
    permission = build_permission(name="users.write")
    permission_repository = Mock(spec=PermissionRepository)
    permission_repository.list_by_ids.return_value = [permission]
    service = RoleService(repository=repository, permission_repository=permission_repository)
    session = Mock()

    response = service.update_role(
        session,
        role.id,
        RoleUpdate(
            description="Administrators",
            permission_ids=[permission.id],
        ),
    )

    assert [item.name for item in response.permissions] == ["users.write"]
    session.commit.assert_called_once()
