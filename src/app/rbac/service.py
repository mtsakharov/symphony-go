"""Service layer for RBAC."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.rbac.exceptions import (
    PermissionNotFoundError,
    RbacUserNotFoundError,
    RoleNameConflictError,
    RoleNotFoundError,
    RolePermissionConflictError,
    RolePermissionNotFoundAssignmentError,
    UserRoleConflictError,
    UserRoleNotFoundAssignmentError,
)
from app.rbac.models import Permission, Role, RolePermission, UserRole
from app.rbac.repository import RbacRepository
from app.rbac.schemas import (
    PermissionListResponse,
    PermissionResponse,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
    UserRoleListResponse,
)

DEFAULT_ADMIN_ROLE_NAME = "admin"
DEFAULT_ADMIN_ROLE_DESCRIPTION = "Full access to user and RBAC management."
DEFAULT_PERMISSIONS: dict[str, str] = {
    "users:create": "Create application users.",
    "users:read": "Read application users.",
    "users:update": "Update application users.",
    "users:delete": "Delete application users.",
    "rbac:read": "Read RBAC configuration.",
    "rbac:write": "Manage RBAC configuration.",
}


class RbacService:
    """Business logic for RBAC operations."""

    def __init__(self, repository: RbacRepository | None = None) -> None:
        self.repository = repository or RbacRepository()

    def ensure_seed_data(self, session: Session) -> None:
        """Ensure the default permissions and admin role exist."""

        changed = False
        permissions: dict[str, Permission] = {}

        for code, description in DEFAULT_PERMISSIONS.items():
            permission = self.repository.get_permission_by_code(session, code)
            if permission is None:
                permission = Permission(code=code, description=description)
                self.repository.create_permission(session, permission=permission)
                changed = True
            permissions[code] = permission

        admin_role = self.repository.get_role_by_name(session, DEFAULT_ADMIN_ROLE_NAME)
        if admin_role is None:
            admin_role = Role(
                name=DEFAULT_ADMIN_ROLE_NAME,
                description=DEFAULT_ADMIN_ROLE_DESCRIPTION,
            )
            self.repository.create_role(session, role=admin_role)
            changed = True

        existing_permission_ids = {permission.id for permission in admin_role.permissions}
        for permission in permissions.values():
            if permission.id not in existing_permission_ids:
                self.repository.create_role_permission(
                    session,
                    role_permission=RolePermission(
                        role_id=admin_role.id,
                        permission_id=permission.id,
                    ),
                )
                changed = True

        if changed:
            session.commit()

    def list_permissions(self, session: Session) -> PermissionListResponse:
        """Return all available permissions."""

        self.ensure_seed_data(session)
        permissions = self.repository.list_permissions(session)
        return PermissionListResponse(
            items=[PermissionResponse.model_validate(permission) for permission in permissions]
        )

    def list_roles(self, session: Session) -> RoleListResponse:
        """Return all defined roles."""

        self.ensure_seed_data(session)
        roles = self.repository.list_roles(session)
        return RoleListResponse(items=[RoleResponse.model_validate(role) for role in roles])

    def get_role(self, session: Session, role_id: UUID) -> RoleResponse:
        """Return a single role by id."""

        self.ensure_seed_data(session)
        role = self.repository.get_role_by_id(session, role_id)
        if role is None:
            raise RoleNotFoundError("Role not found")
        return RoleResponse.model_validate(role)

    def create_role(self, session: Session, payload: RoleCreate) -> RoleResponse:
        """Create a new role if the name is unique."""

        self.ensure_seed_data(session)
        if self.repository.get_role_by_name(session, payload.name) is not None:
            raise RoleNameConflictError("Role with this name already exists")

        role = Role(name=payload.name, description=payload.description)
        try:
            self.repository.create_role(session, role=role)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise RoleNameConflictError("Role with this name already exists") from exc

        created_role = self.repository.get_role_by_id(session, role.id)
        assert created_role is not None
        return RoleResponse.model_validate(created_role)

    def update_role(self, session: Session, role_id: UUID, payload: RoleUpdate) -> RoleResponse:
        """Apply partial updates to a role."""

        self.ensure_seed_data(session)
        role = self.repository.get_role_by_id(session, role_id)
        if role is None:
            raise RoleNotFoundError("Role not found")

        if payload.name is not None and payload.name != role.name:
            existing_role = self.repository.get_role_by_name(session, payload.name)
            if existing_role is not None and existing_role.id != role.id:
                raise RoleNameConflictError("Role with this name already exists")
            role.name = payload.name

        update_data = payload.model_dump(exclude_unset=True, exclude={"name"})
        for field_name, value in update_data.items():
            setattr(role, field_name, value)

        try:
            session.add(role)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise RoleNameConflictError("Role with this name already exists") from exc

        updated_role = self.repository.get_role_by_id(session, role.id)
        assert updated_role is not None
        return RoleResponse.model_validate(updated_role)

    def delete_role(self, session: Session, role_id: UUID) -> None:
        """Delete a role."""

        self.ensure_seed_data(session)
        role = self.repository.get_role_by_id(session, role_id)
        if role is None:
            raise RoleNotFoundError("Role not found")

        self.repository.delete_role(session, role=role)
        session.commit()

    def assign_permission_to_role(
        self, session: Session, role_id: UUID, permission_id: UUID
    ) -> RoleResponse:
        """Assign a permission to a role."""

        self.ensure_seed_data(session)
        role = self.repository.get_role_by_id(session, role_id)
        if role is None:
            raise RoleNotFoundError("Role not found")

        permission = self.repository.get_permission_by_id(session, permission_id)
        if permission is None:
            raise PermissionNotFoundError("Permission not found")

        if (
            self.repository.get_role_permission(
                session, role_id=role_id, permission_id=permission_id
            )
            is not None
        ):
            raise RolePermissionConflictError("Permission is already assigned to this role")

        self.repository.create_role_permission(
            session,
            role_permission=RolePermission(role_id=role_id, permission_id=permission_id),
        )
        session.commit()
        return self.get_role(session, role_id)

    def remove_permission_from_role(
        self, session: Session, role_id: UUID, permission_id: UUID
    ) -> RoleResponse:
        """Remove a permission from a role."""

        self.ensure_seed_data(session)
        role = self.repository.get_role_by_id(session, role_id)
        if role is None:
            raise RoleNotFoundError("Role not found")

        assignment = self.repository.get_role_permission(
            session, role_id=role_id, permission_id=permission_id
        )
        if assignment is None:
            raise RolePermissionNotFoundAssignmentError("Role permission assignment not found")

        self.repository.delete_role_permission(session, role_permission=assignment)
        session.commit()
        return self.get_role(session, role_id)

    def list_user_roles(self, session: Session, user_id: UUID) -> UserRoleListResponse:
        """Return all roles assigned to a user."""

        self.ensure_seed_data(session)
        if self.repository.get_user_by_id(session, user_id) is None:
            raise RbacUserNotFoundError("User not found")

        roles = self.repository.list_user_roles(session, user_id=user_id)
        return UserRoleListResponse(
            user_id=user_id,
            items=[RoleResponse.model_validate(role) for role in roles],
        )

    def assign_role_to_user(
        self, session: Session, user_id: UUID, role_id: UUID
    ) -> UserRoleListResponse:
        """Assign a role to a user."""

        self.ensure_seed_data(session)
        if self.repository.get_user_by_id(session, user_id) is None:
            raise RbacUserNotFoundError("User not found")

        role = self.repository.get_role_by_id(session, role_id)
        if role is None:
            raise RoleNotFoundError("Role not found")

        if self.repository.get_user_role(session, user_id=user_id, role_id=role_id) is not None:
            raise UserRoleConflictError("Role is already assigned to this user")

        self.repository.create_user_role(
            session,
            user_role=UserRole(user_id=user_id, role_id=role_id),
        )
        session.commit()
        return self.list_user_roles(session, user_id)

    def remove_role_from_user(
        self, session: Session, user_id: UUID, role_id: UUID
    ) -> UserRoleListResponse:
        """Remove a role from a user."""

        self.ensure_seed_data(session)
        if self.repository.get_user_by_id(session, user_id) is None:
            raise RbacUserNotFoundError("User not found")

        if self.repository.get_role_by_id(session, role_id) is None:
            raise RoleNotFoundError("Role not found")

        assignment = self.repository.get_user_role(session, user_id=user_id, role_id=role_id)
        if assignment is None:
            raise UserRoleNotFoundAssignmentError("User role assignment not found")

        self.repository.delete_user_role(session, user_role=assignment)
        session.commit()
        return self.list_user_roles(session, user_id)

    def get_effective_permission_codes(self, session: Session, user_id: UUID) -> set[str]:
        """Return the effective permissions granted to a user."""

        self.ensure_seed_data(session)
        if self.repository.get_user_by_id(session, user_id) is None:
            raise RbacUserNotFoundError("User not found")

        return self.repository.get_effective_permission_codes(session, user_id=user_id)

    def assign_admin_role(self, session: Session, user_id: UUID) -> None:
        """Assign the default admin role to a user without committing."""

        self.ensure_seed_data(session)
        if self.repository.get_user_by_id(session, user_id) is None:
            raise RbacUserNotFoundError("User not found")

        admin_role = self.repository.get_role_by_name(session, DEFAULT_ADMIN_ROLE_NAME)
        if admin_role is None:
            raise RoleNotFoundError("Role not found")

        if self.repository.get_user_role(session, user_id=user_id, role_id=admin_role.id) is None:
            self.repository.create_user_role(
                session,
                user_role=UserRole(user_id=user_id, role_id=admin_role.id),
            )
