"""create video uploads table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260602_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the video_uploads table."""

    op.create_table(
        "video_uploads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("codec", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending_upload", nullable=False),
        sa.Column("upload_path", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("upload_path"),
    )
    op.create_index(op.f("ix_video_uploads_mime_type"), "video_uploads", ["mime_type"])


def downgrade() -> None:
    """Drop the video_uploads table."""

    op.drop_index(op.f("ix_video_uploads_mime_type"), table_name="video_uploads")
    op.drop_table("video_uploads")
