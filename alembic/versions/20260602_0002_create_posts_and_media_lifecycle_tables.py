"""create posts and media lifecycle tables"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260602_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


media_asset_type = sa.Enum("video", name="media_asset_type", native_enum=False)
media_asset_role = sa.Enum("source", "derived", name="media_asset_role", native_enum=False)
media_lifecycle_state = sa.Enum(
    "pending_upload",
    "completed_upload",
    "attached",
    "pending_delete",
    "deleted",
    name="media_lifecycle_state",
    native_enum=False,
)
post_type = sa.Enum("video", name="post_type", native_enum=False)


def upgrade() -> None:
    """Create posts and unified media lifecycle tables."""

    bind = op.get_bind()
    media_asset_type.create(bind, checkfirst=True)
    media_asset_role.create(bind, checkfirst=True)
    media_lifecycle_state.create(bind, checkfirst=True)
    post_type.create(bind, checkfirst=True)

    op.create_table(
        "posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_type", post_type, nullable=False),
        sa.Column("caption", sa.String(length=2200), server_default="", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("media_type", media_asset_type, nullable=False),
        sa.Column("asset_role", media_asset_role, nullable=False),
        sa.Column("lifecycle_state", media_lifecycle_state, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("codec", sa.String(length=100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("post_id", sa.Uuid(), nullable=True),
        sa.Column("source_media_id", sa.Uuid(), nullable=True),
        sa.Column("cleanup_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_media_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index("ix_media_assets_post_id", "media_assets", ["post_id"])
    op.create_index("ix_media_assets_source_media_id", "media_assets", ["source_media_id"])
    op.create_index("ix_media_assets_storage_path", "media_assets", ["storage_path"])


def downgrade() -> None:
    """Drop posts and unified media lifecycle tables."""

    bind = op.get_bind()

    op.drop_index("ix_media_assets_storage_path", table_name="media_assets")
    op.drop_index("ix_media_assets_source_media_id", table_name="media_assets")
    op.drop_index("ix_media_assets_post_id", table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_table("posts")

    post_type.drop(bind, checkfirst=True)
    media_lifecycle_state.drop(bind, checkfirst=True)
    media_asset_role.drop(bind, checkfirst=True)
    media_asset_type.drop(bind, checkfirst=True)
