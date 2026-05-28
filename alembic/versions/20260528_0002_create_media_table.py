"""create media table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260528_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the media table."""

    op.create_table(
        "media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index(op.f("ix_media_content_type"), "media", ["content_type"], unique=False)


def downgrade() -> None:
    """Drop the media table."""

    op.drop_index(op.f("ix_media_content_type"), table_name="media")
    op.drop_table("media")
