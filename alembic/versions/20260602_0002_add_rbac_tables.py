"""add rbac tables"""

from __future__ import annotations

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "20260602_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create RBAC tables and seed the default admin role."""

    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_permissions_code"), "permissions", ["code"], unique=False)

    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )
    op.create_index(
        op.f("ix_role_permissions_permission_id"), "role_permissions", ["permission_id"]
    )
    op.create_index(op.f("ix_role_permissions_role_id"), "role_permissions", ["role_id"])

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )
    op.create_index(op.f("ix_user_roles_role_id"), "user_roles", ["role_id"])
    op.create_index(op.f("ix_user_roles_user_id"), "user_roles", ["user_id"])

    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )

    admin_role_id = uuid4()
    seeded_permissions = [
        {"id": uuid4(), "code": "users:create", "description": "Create application users."},
        {"id": uuid4(), "code": "users:read", "description": "Read application users."},
        {"id": uuid4(), "code": "users:update", "description": "Update application users."},
        {"id": uuid4(), "code": "users:delete", "description": "Delete application users."},
        {"id": uuid4(), "code": "rbac:read", "description": "Read RBAC configuration."},
        {"id": uuid4(), "code": "rbac:write", "description": "Manage RBAC configuration."},
    ]

    op.bulk_insert(permissions_table, seeded_permissions)
    op.bulk_insert(
        roles_table,
        [
            {
                "id": admin_role_id,
                "name": "admin",
                "description": "Full access to user and RBAC management.",
            }
        ],
    )
    op.bulk_insert(
        role_permissions_table,
        [
            {
                "id": uuid4(),
                "role_id": admin_role_id,
                "permission_id": permission["id"],
            }
            for permission in seeded_permissions
        ],
    )


def downgrade() -> None:
    """Drop RBAC tables."""

    op.drop_index(op.f("ix_user_roles_user_id"), table_name="user_roles")
    op.drop_index(op.f("ix_user_roles_role_id"), table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_index(op.f("ix_role_permissions_role_id"), table_name="role_permissions")
    op.drop_index(op.f("ix_role_permissions_permission_id"), table_name="role_permissions")
    op.drop_table("role_permissions")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_table("roles")
    op.drop_index(op.f("ix_permissions_code"), table_name="permissions")
    op.drop_table("permissions")
