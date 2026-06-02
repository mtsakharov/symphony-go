"""create posts table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260602_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the posts table."""

    op.create_table(
        "posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "post_type",
            sa.Enum("text", "video", name="posttype", native_enum=False, length=32),
            server_default="text",
            nullable=False,
        ),
        sa.Column("body", sa.Text(), server_default="", nullable=False),
        sa.Column("video_caption", sa.String(length=500), nullable=True),
        sa.Column("video_duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "video_status",
            sa.Enum(
                "processing",
                "ready",
                "failed",
                name="videoprocessingstatus",
                native_enum=False,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("video_playback_reference", sa.String(length=512), nullable=True),
        sa.Column("video_failure_reason", sa.String(length=255), nullable=True),
        sa.Column("video_poster_url", sa.String(length=512), nullable=True),
        sa.Column("video_poster_width", sa.Integer(), nullable=True),
        sa.Column("video_poster_height", sa.Integer(), nullable=True),
        sa.Column("video_thumbnail_url", sa.String(length=512), nullable=True),
        sa.Column("video_thumbnail_width", sa.Integer(), nullable=True),
        sa.Column("video_thumbnail_height", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_posts_created_at"), "posts", ["created_at"], unique=False)


def downgrade() -> None:
    """Drop the posts table."""

    op.drop_index(op.f("ix_posts_created_at"), table_name="posts")
    op.drop_table("posts")
