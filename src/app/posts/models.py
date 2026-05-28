"""Posts database models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def utc_now() -> datetime:
    """Return the current UTC datetime."""

    return datetime.now(UTC)


class PostStatus(StrEnum):
    """Supported post publication states."""

    DRAFT = "draft"
    PUBLISHED = "published"


class Post(Base):
    """Database model for content posts."""

    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), index=True)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, name="post_status", native_enum=False),
        default=PostStatus.DRAFT,
        server_default=PostStatus.DRAFT.value,
    )
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
