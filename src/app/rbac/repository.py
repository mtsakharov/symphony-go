"""Repository layer for RBAC."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.rbac.models import Permission, Role, RolePermission, UserRole
from app.users.models import User


class RbacRepository:
    """Persist and query RBAC resources."""

    def count_users(self, session: Session) -> int:
        """Return the total number of users."""

        statement = select(func.count()).select_from(User)
        return int(session.execute(statement).scalar_one())

    def get_user_by_id(self, session: Session, user_id: UUID) -> User | None:
        """Return a user by id if present."""

        return session.get(User, user_id)

    def list_permissions(self, session: Session) -> list[Permission]:
        """Return all permissions ordered by code."""

        statement = select(Permission).order_by(Permission.code.asc())
        return list(session.execute(statement).scalars().all())

    def get_permission_by_id(self, session: Session, permission_id: UUID) -> Permission | None:
        """Return a permission by id if present."""

        return session.get(Permission, permission_id)

    def get_permission_by_code(self, session: Session, code: str) -> Permission | None:
        """Return a permission by code if present."""

        statement = select(Permission).where(Permission.code == code)
        return session.execute(statement).scalar_one_or_none()

    def create_permission(self, session: Session, *, permission: Permission) -> Permission:
        """Persist a new permission."""

        session.add(permission)
        session.flush()
        return permission

    def list_roles(self, session: Session) -> list[Role]:
        """Return all roles ordered by name."""

        statement = (
            select(Role)
            .options(selectinload(Role.permissions))
            .execution_options(populate_existing=True)
            .order_by(Role.name.asc(), Role.id.asc())
        )
        return list(session.execute(statement).scalars().all())

    def get_role_by_id(self, session: Session, role_id: UUID) -> Role | None:
        """Return a role by id if present."""

        statement = (
            select(Role)
            .options(selectinload(Role.permissions))
            .execution_options(populate_existing=True)
            .where(Role.id == role_id)
        )
        return session.execute(statement).scalar_one_or_none()

    def get_role_by_name(self, session: Session, name: str) -> Role | None:
        """Return a role by name if present."""

        statement = (
            select(Role)
            .options(selectinload(Role.permissions))
            .execution_options(populate_existing=True)
            .where(Role.name == name)
        )
        return session.execute(statement).scalar_one_or_none()

    def create_role(self, session: Session, *, role: Role) -> Role:
        """Persist a new role."""

        session.add(role)
        session.flush()
        return role

    def delete_role(self, session: Session, *, role: Role) -> None:
        """Delete a role and its assignments."""

        session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        session.execute(delete(UserRole).where(UserRole.role_id == role.id))
        session.delete(role)
        session.flush()

    def get_role_permission(
        self, session: Session, *, role_id: UUID, permission_id: UUID
    ) -> RolePermission | None:
        """Return an existing role-permission assignment if present."""

        statement = select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
        return session.execute(statement).scalar_one_or_none()

    def create_role_permission(
        self, session: Session, *, role_permission: RolePermission
    ) -> RolePermission:
        """Persist a role-permission assignment."""

        session.add(role_permission)
        session.flush()
        return role_permission

    def delete_role_permission(self, session: Session, *, role_permission: RolePermission) -> None:
        """Delete a role-permission assignment."""

        session.delete(role_permission)
        session.flush()

    def list_user_roles(self, session: Session, *, user_id: UUID) -> list[Role]:
        """Return all roles assigned to a user."""

        statement = (
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .options(selectinload(Role.permissions))
            .execution_options(populate_existing=True)
            .where(UserRole.user_id == user_id)
            .order_by(Role.name.asc(), Role.id.asc())
        )
        return list(session.execute(statement).scalars().all())

    def get_user_role(self, session: Session, *, user_id: UUID, role_id: UUID) -> UserRole | None:
        """Return an existing user-role assignment if present."""

        statement = select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        return session.execute(statement).scalar_one_or_none()

    def create_user_role(self, session: Session, *, user_role: UserRole) -> UserRole:
        """Persist a user-role assignment."""

        session.add(user_role)
        session.flush()
        return user_role

    def delete_user_role(self, session: Session, *, user_role: UserRole) -> None:
        """Delete a user-role assignment."""

        session.delete(user_role)
        session.flush()

    def get_effective_permission_codes(self, session: Session, *, user_id: UUID) -> set[str]:
        """Return the distinct permission codes granted to a user."""

        statement = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
        )
        return set(session.execute(statement).scalars().all())
