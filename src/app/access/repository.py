"""Repository layer for roles and permissions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.access.models import Permission, Role


class PermissionRepository:
    """Persist and query permissions."""

    def get_by_id(self, session: Session, permission_id: UUID) -> Permission | None:
        """Return a permission by id if present."""

        statement = select(Permission).where(Permission.id == permission_id)
        return session.execute(statement).scalar_one_or_none()

    def get_by_name(self, session: Session, name: str) -> Permission | None:
        """Return a permission by name if present."""

        statement = select(Permission).where(Permission.name == name)
        return session.execute(statement).scalar_one_or_none()

    def list_permissions(self, session: Session, *, offset: int, limit: int) -> list[Permission]:
        """Return a page of permissions ordered by creation time."""

        statement = (
            select(Permission)
            .order_by(Permission.created_at.desc(), Permission.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(statement).scalars().all())

    def count_permissions(self, session: Session) -> int:
        """Return the total number of permissions."""

        statement = select(func.count()).select_from(Permission)
        return int(session.execute(statement).scalar_one())

    def list_by_ids(self, session: Session, permission_ids: list[UUID]) -> list[Permission]:
        """Return permissions matching the provided ids."""

        if not permission_ids:
            return []

        statement = select(Permission).where(Permission.id.in_(permission_ids))
        permissions = list(session.execute(statement).scalars().all())
        permissions_by_id = {permission.id: permission for permission in permissions}
        return [
            permissions_by_id[permission_id]
            for permission_id in permission_ids
            if permission_id in permissions_by_id
        ]

    def create(self, session: Session, *, permission: Permission) -> Permission:
        """Persist a new permission."""

        session.add(permission)
        session.flush()
        return permission

    def delete(self, session: Session, *, permission: Permission) -> None:
        """Delete an existing permission."""

        session.delete(permission)
        session.flush()


class RoleRepository:
    """Persist and query roles."""

    def get_by_id(self, session: Session, role_id: UUID) -> Role | None:
        """Return a role by id if present."""

        statement = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        return session.execute(statement).scalar_one_or_none()

    def get_by_name(self, session: Session, name: str) -> Role | None:
        """Return a role by name if present."""

        statement = select(Role).where(Role.name == name)
        return session.execute(statement).scalar_one_or_none()

    def list_roles(self, session: Session, *, offset: int, limit: int) -> list[Role]:
        """Return a page of roles ordered by creation time."""

        statement = (
            select(Role)
            .options(selectinload(Role.permissions))
            .order_by(Role.created_at.desc(), Role.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(statement).scalars().all())

    def count_roles(self, session: Session) -> int:
        """Return the total number of roles."""

        statement = select(func.count()).select_from(Role)
        return int(session.execute(statement).scalar_one())

    def list_by_ids(self, session: Session, role_ids: list[UUID]) -> list[Role]:
        """Return roles matching the provided ids."""

        if not role_ids:
            return []

        statement = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id.in_(role_ids))
        )
        roles = list(session.execute(statement).scalars().all())
        roles_by_id = {role.id: role for role in roles}
        return [roles_by_id[role_id] for role_id in role_ids if role_id in roles_by_id]

    def create(self, session: Session, *, role: Role) -> Role:
        """Persist a new role."""

        session.add(role)
        session.flush()
        return role

    def delete(self, session: Session, *, role: Role) -> None:
        """Delete an existing role."""

        session.delete(role)
        session.flush()
