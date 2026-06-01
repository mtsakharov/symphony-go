"""create feed items table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260601_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the feed_items table."""

    op.create_table(
        "feed_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feed_items_user_id"), "feed_items", ["user_id"], unique=False)
    op.create_index(
        "ix_feed_items_user_created_at",
        "feed_items",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the feed_items table."""

    op.drop_index("ix_feed_items_user_created_at", table_name="feed_items")
    op.drop_index(op.f("ix_feed_items_user_id"), table_name="feed_items")
    op.drop_table("feed_items")
