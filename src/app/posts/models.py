"""Posts database models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text, Uuid, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def utc_now() -> datetime:
    """Return the current UTC datetime."""

    return datetime.now(UTC)


class PostType(StrEnum):
    """Supported post types."""

    TEXT = "text"
    VIDEO = "video"


class VideoProcessingStatus(StrEnum):
    """Supported video processing states."""

    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Post(Base):
    """Database model for feed posts."""

    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_type: Mapped[PostType] = mapped_column(
        SqlEnum(
            PostType,
            native_enum=False,
            length=32,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=PostType.TEXT,
        server_default=PostType.TEXT.value,
    )
    body: Mapped[str] = mapped_column(Text, default="", server_default="")
    video_caption: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_status: Mapped[VideoProcessingStatus | None] = mapped_column(
        SqlEnum(
            VideoProcessingStatus,
            native_enum=False,
            length=32,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=True,
    )
    video_playback_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    video_poster_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_poster_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_poster_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_thumbnail_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_thumbnail_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
