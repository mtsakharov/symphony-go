"""create tweet requests table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260603_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the tweet_requests table."""

    op.create_table(
        "tweet_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brief", sa.String(length=2_000), nullable=True),
        sa.Column("target_audience", sa.String(length=255), nullable=True),
        sa.Column("objective", sa.String(length=255), nullable=True),
        sa.Column("tone", sa.String(length=100), nullable=True),
        sa.Column("call_to_action", sa.String(length=255), nullable=True),
        sa.Column("reviewer_notes", sa.String(length=2_000), nullable=True),
        sa.Column("approved_by_compliance", sa.Boolean(), nullable=True),
        sa.Column("approved_by_reviewer", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=64), server_default="draft", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop the tweet_requests table."""

    op.drop_table("tweet_requests")
