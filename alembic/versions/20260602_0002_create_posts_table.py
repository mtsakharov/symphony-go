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
        sa.Column("body", sa.Text(), server_default="", nullable=False),
        sa.Column("media_type", sa.String(length=32), nullable=True),
        sa.Column("upload_ref", sa.String(length=2048), nullable=True),
        sa.Column("asset_ref", sa.String(length=2048), nullable=True),
        sa.Column("processing_status", sa.String(length=32), nullable=True),
        sa.Column("playback_ref", sa.String(length=2048), nullable=True),
        sa.Column("poster_ref", sa.String(length=2048), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "media_type IS NULL OR media_type = 'video'",
            name="ck_posts_media_type_video_only",
        ),
        sa.CheckConstraint(
            "processing_status IS NULL OR processing_status IN "
            "('uploading', 'processing', 'ready', 'failed')",
            name="ck_posts_processing_status_valid",
        ),
        sa.CheckConstraint(
            "media_type IS NULL OR processing_status IS NOT NULL",
            name="ck_posts_video_requires_processing_status",
        ),
        sa.CheckConstraint(
            "media_type IS NULL OR upload_ref IS NOT NULL OR asset_ref IS NOT NULL",
            name="ck_posts_video_requires_source_reference",
        ),
        sa.CheckConstraint(
            "media_type IS NOT NULL OR ("
            "upload_ref IS NULL AND asset_ref IS NULL AND processing_status IS NULL AND "
            "playback_ref IS NULL AND poster_ref IS NULL AND duration_ms IS NULL AND "
            "failure_reason IS NULL"
            ")",
            name="ck_posts_video_metadata_requires_media_type",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_posts_duration_ms_non_negative",
        ),
        sa.CheckConstraint(
            "(processing_status = 'failed' AND failure_reason IS NOT NULL) OR "
            "(processing_status IS NULL OR processing_status != 'failed')",
            name="ck_posts_failed_requires_failure_reason",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop the posts table."""

    op.drop_table("posts")
