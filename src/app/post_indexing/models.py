"""Indexed post chunk models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.users.models import utc_now


class PostIndexRecord(Base):
    """Stored search/index record for a single post chunk."""

    __tablename__ = "post_index_records"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "post_id",
            "chunk_id",
            name="uq_post_index_records_user_post_chunk",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    post_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("posts.id", ondelete="CASCADE"),
        index=True,
    )
    chunk_id: Mapped[str] = mapped_column(String(128))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(JSON)
    visibility: Mapped[str] = mapped_column(String(32))
    source_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
    )
