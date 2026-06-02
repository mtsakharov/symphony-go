"""create video post lifecycle tables

Revision ID: 20260602_0002
Revises: 20260526_0001
Create Date: 2026-06-02 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260602_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("post_type", sa.Enum("text", "video", name="post_type"), nullable=False),
        sa.Column("caption", sa.String(length=2200), server_default="", nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "uploading",
                "processing",
                "ready",
                "failed",
                "deleted",
                name="post_status",
            ),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "video_uploads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("video_codec", sa.String(length=100), nullable=False),
        sa.Column("audio_codec", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending_upload", "completed", name="video_upload_status"),
            server_default="pending_upload",
            nullable=False,
        ),
        sa.Column("upload_path", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("upload_path"),
    )
    op.create_table(
        "video_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("upload_id", sa.Uuid(), nullable=False),
        sa.Column("source_key", sa.String(length=512), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.Enum("processing", "ready", "failed", name="video_asset_status"),
            server_default="processing",
            nullable=False,
        ),
        sa.Column("is_playable", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("playback_metadata", sa.JSON(), nullable=True),
        sa.Column("poster_metadata", sa.JSON(), nullable=True),
        sa.Column("thumbnail_metadata", sa.JSON(), nullable=True),
        sa.Column("failure_reason", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["upload_id"], ["video_uploads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id"),
        sa.UniqueConstraint("source_key"),
        sa.UniqueConstraint("upload_id"),
    )


def downgrade() -> None:
    op.drop_table("video_assets")
    op.drop_table("video_uploads")
    op.drop_table("posts")
    sa.Enum(name="video_asset_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="video_upload_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="post_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="post_type").drop(op.get_bind(), checkfirst=True)
