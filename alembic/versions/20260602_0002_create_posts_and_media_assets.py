"""create posts and media assets tables"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260602_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


media_asset_type = sa.Enum("image", "video", name="media_asset_type")
upload_status = sa.Enum("pending", "completed", "failed", name="upload_status")
post_type = sa.Enum("text", "image", "video", name="post_type")
media_state = sa.Enum("ready", name="media_state")


def upgrade() -> None:
    """Create the posts, media assets, and post assets tables."""

    bind = op.get_bind()
    media_asset_type.create(bind, checkfirst=True)
    upload_status.create(bind, checkfirst=True)
    post_type.create(bind, checkfirst=True)
    media_state.create(bind, checkfirst=True)

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("media_type", media_asset_type, nullable=False),
        sa.Column("upload_status", upload_status, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_type", post_type, nullable=False),
        sa.Column("caption", sa.String(length=2200), server_default="", nullable=False),
        sa.Column("media_state", media_state, server_default="ready", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "post_assets",
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["media_assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id", "asset_id"),
        sa.UniqueConstraint("post_id", "position", name="uq_post_assets_post_position"),
    )


def downgrade() -> None:
    """Drop the posts, media assets, and post assets tables."""

    bind = op.get_bind()

    op.drop_table("post_assets")
    op.drop_table("posts")
    op.drop_table("media_assets")

    media_state.drop(bind, checkfirst=True)
    post_type.drop(bind, checkfirst=True)
    upload_status.drop(bind, checkfirst=True)
    media_asset_type.drop(bind, checkfirst=True)
