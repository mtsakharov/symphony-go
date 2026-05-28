"""create posts table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260528_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the posts table."""

    op.create_table(
        "posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "published", name="post_status", native_enum=False),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_posts_author_id"), "posts", ["author_id"], unique=False)
    op.create_index(op.f("ix_posts_title"), "posts", ["title"], unique=False)


def downgrade() -> None:
    """Drop the posts table."""

    op.drop_index(op.f("ix_posts_title"), table_name="posts")
    op.drop_index(op.f("ix_posts_author_id"), table_name="posts")
    op.drop_table("posts")
    sa.Enum("draft", "published", name="post_status", native_enum=False).drop(
        op.get_bind(),
        checkfirst=True,
    )
