"""create devices table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260602_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the devices table."""

    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("secret_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier"),
    )
    op.create_index(op.f("ix_devices_identifier"), "devices", ["identifier"], unique=False)


def downgrade() -> None:
    """Drop the devices table."""

    op.drop_index(op.f("ix_devices_identifier"), table_name="devices")
    op.drop_table("devices")
