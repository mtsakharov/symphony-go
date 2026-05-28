"""Service layer for roles and permissions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access.exceptions import (
    PermissionConflictError,
    PermissionNotFoundError,
    RoleConflictError,
    RoleNotFoundError,
)
from app.access.models import Permission, Role
from app.access.repository import PermissionRepository, RoleRepository
from app.access.schemas import (
    PermissionCreate,
    PermissionListResponse,
    PermissionResponse,
    PermissionUpdate,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleSummaryResponse,
    RoleUpdate,
)


def serialize_permission(permission: Permission) -> PermissionResponse:
    """Return an API response model for a permission."""

    return PermissionResponse.model_validate(permission)


def serialize_role_summary(role: Role) -> RoleSummaryResponse:
    """Return a summary response model for a role."""

    return RoleSummaryResponse.model_validate(role)


def serialize_role(role: Role) -> RoleResponse:
    """Return an API response model for a role."""

    permissions = sorted(
        role.permissions,
        key=lambda permission: (permission.name, str(permission.id)),
    )
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=[serialize_permission(permission) for permission in permissions],
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


class PermissionService:
    """Business logic for permission CRUD operations."""

    def __init__(self, repository: PermissionRepository | None = None) -> None:
        self.repository = repository or PermissionRepository()

    def create_permission(self, session: Session, payload: PermissionCreate) -> PermissionResponse:
        """Create a new permission if the name is unique."""

        if self.repository.get_by_name(session, payload.name) is not None:
            raise PermissionConflictError("Permission with this name already exists")

        permission = Permission(name=payload.name, description=payload.description)

        try:
            self.repository.create(session, permission=permission)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise PermissionConflictError("Permission with this name already exists") from exc

        session.refresh(permission)
        return serialize_permission(permission)

    def list_permissions(
        self,
        session: Session,
        *,
        page: int,
        limit: int,
    ) -> PermissionListResponse:
        """Return a paginated list of permissions."""

        offset = (page - 1) * limit
        permissions = self.repository.list_permissions(session, offset=offset, limit=limit)
        total = self.repository.count_permissions(session)
        return PermissionListResponse(
            items=[serialize_permission(permission) for permission in permissions],
            page=page,
            limit=limit,
            total=total,
        )

    def get_permission(self, session: Session, permission_id: UUID) -> PermissionResponse:
        """Return a single permission or raise if absent."""

        permission = self.repository.get_by_id(session, permission_id)
        if permission is None:
            raise PermissionNotFoundError("Permission not found")
        return serialize_permission(permission)

    def update_permission(
        self,
        session: Session,
        permission_id: UUID,
        payload: PermissionUpdate,
    ) -> PermissionResponse:
        """Apply partial updates to a permission."""

        permission = self.repository.get_by_id(session, permission_id)
        if permission is None:
            raise PermissionNotFoundError("Permission not found")

        if payload.name is not None:
            existing_permission = self.repository.get_by_name(session, payload.name)
            if existing_permission is not None and existing_permission.id != permission.id:
                raise PermissionConflictError("Permission with this name already exists")
            permission.name = payload.name

        if "description" in payload.model_fields_set:
            permission.description = payload.description

        try:
            session.add(permission)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise PermissionConflictError("Permission with this name already exists") from exc

        session.refresh(permission)
        return serialize_permission(permission)

    def delete_permission(self, session: Session, permission_id: UUID) -> None:
        """Delete a permission by id."""

        permission = self.repository.get_by_id(session, permission_id)
        if permission is None:
            raise PermissionNotFoundError("Permission not found")

        permission.roles.clear()
        self.repository.delete(session, permission=permission)
        session.commit()


class RoleService:
    """Business logic for role CRUD operations."""

    def __init__(
        self,
        repository: RoleRepository | None = None,
        permission_repository: PermissionRepository | None = None,
    ) -> None:
        self.repository = repository or RoleRepository()
        self.permission_repository = permission_repository or PermissionRepository()

    def create_role(self, session: Session, payload: RoleCreate) -> RoleResponse:
        """Create a new role if the name is unique."""

        if self.repository.get_by_name(session, payload.name) is not None:
            raise RoleConflictError("Role with this name already exists")

        permissions = self._get_permissions_or_raise(session, payload.permission_ids)
        role = Role(name=payload.name, description=payload.description, permissions=permissions)

        try:
            self.repository.create(session, role=role)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise RoleConflictError("Role with this name already exists") from exc

        session.refresh(role)
        return serialize_role(role)

    def list_roles(self, session: Session, *, page: int, limit: int) -> RoleListResponse:
        """Return a paginated list of roles."""

        offset = (page - 1) * limit
        roles = self.repository.list_roles(session, offset=offset, limit=limit)
        total = self.repository.count_roles(session)
        return RoleListResponse(
            items=[serialize_role(role) for role in roles],
            page=page,
            limit=limit,
            total=total,
        )

    def get_role(self, session: Session, role_id: UUID) -> RoleResponse:
        """Return a single role or raise if absent."""

        role = self.repository.get_by_id(session, role_id)
        if role is None:
            raise RoleNotFoundError("Role not found")
        return serialize_role(role)

    def update_role(self, session: Session, role_id: UUID, payload: RoleUpdate) -> RoleResponse:
        """Apply partial updates to a role."""

        role = self.repository.get_by_id(session, role_id)
        if role is None:
            raise RoleNotFoundError("Role not found")

        if payload.name is not None:
            existing_role = self.repository.get_by_name(session, payload.name)
            if existing_role is not None and existing_role.id != role.id:
                raise RoleConflictError("Role with this name already exists")
            role.name = payload.name

        if "description" in payload.model_fields_set:
            role.description = payload.description

        if payload.permission_ids is not None:
            role.permissions = self._get_permissions_or_raise(session, payload.permission_ids)

        try:
            session.add(role)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise RoleConflictError("Role with this name already exists") from exc

        session.refresh(role)
        return serialize_role(role)

    def delete_role(self, session: Session, role_id: UUID) -> None:
        """Delete a role by id."""

        role = self.repository.get_by_id(session, role_id)
        if role is None:
            raise RoleNotFoundError("Role not found")

        role.permissions.clear()
        role.users.clear()
        self.repository.delete(session, role=role)
        session.commit()

    def _get_permissions_or_raise(
        self,
        session: Session,
        permission_ids: list[UUID],
    ) -> list[Permission]:
        """Resolve permission ids or raise if any are missing."""

        permissions = self.permission_repository.list_by_ids(session, permission_ids)
        missing_ids = [
            str(permission_id)
            for permission_id in permission_ids
            if all(permission.id != permission_id for permission in permissions)
        ]
        if missing_ids:
            missing_ids.sort()
            raise PermissionNotFoundError(
                f"Permissions not found: {', '.join(missing_ids)}"
            )
        return permissions
