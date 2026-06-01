"""create video assets table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260602_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the video assets table."""

    op.create_table(
        "video_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_key", sa.String(length=512), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="processing", nullable=False),
        sa.Column("is_playable", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("playback_metadata", sa.JSON(), nullable=True),
        sa.Column("poster_metadata", sa.JSON(), nullable=True),
        sa.Column("thumbnail_metadata", sa.JSON(), nullable=True),
        sa.Column("failure_reason", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    op.create_index(
        op.f("ix_video_assets_source_key"),
        "video_assets",
        ["source_key"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the video assets table."""

    op.drop_index(op.f("ix_video_assets_source_key"), table_name="video_assets")
    op.drop_table("video_assets")
