"""Posts database models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

VIDEO_MEDIA_TYPE = "video"
VIDEO_PROCESSING_STATUSES = ("uploading", "processing", "ready", "failed")


def utc_now() -> datetime:
    """Return the current UTC datetime."""

    return datetime.now(UTC)


class Post(Base):
    """Database model for application posts."""

    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint(
            "media_type IS NULL OR media_type = 'video'",
            name="ck_posts_media_type_video_only",
        ),
        CheckConstraint(
            "processing_status IS NULL OR processing_status IN "
            "('uploading', 'processing', 'ready', 'failed')",
            name="ck_posts_processing_status_valid",
        ),
        CheckConstraint(
            "media_type IS NULL OR processing_status IS NOT NULL",
            name="ck_posts_video_requires_processing_status",
        ),
        CheckConstraint(
            "media_type IS NULL OR upload_ref IS NOT NULL OR asset_ref IS NOT NULL",
            name="ck_posts_video_requires_source_reference",
        ),
        CheckConstraint(
            "media_type IS NOT NULL OR ("
            "upload_ref IS NULL AND asset_ref IS NULL AND processing_status IS NULL AND "
            "playback_ref IS NULL AND poster_ref IS NULL AND duration_ms IS NULL AND "
            "failure_reason IS NULL"
            ")",
            name="ck_posts_video_metadata_requires_media_type",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_posts_duration_ms_non_negative",
        ),
        CheckConstraint(
            "(processing_status = 'failed' AND failure_reason IS NOT NULL) OR "
            "(processing_status IS NULL OR processing_status != 'failed')",
            name="ck_posts_failed_requires_failure_reason",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    body: Mapped[str] = mapped_column(Text, default="", server_default="")
    media_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    upload_ref: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    asset_ref: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    processing_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    playback_ref: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    poster_ref: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
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

    @property
    def video_asset(self) -> dict[str, str | int | None] | None:
        """Return the optional serialized video asset payload."""

        if self.media_type is None:
            return None

        return {
            "media_type": self.media_type,
            "upload_ref": self.upload_ref,
            "asset_ref": self.asset_ref,
            "processing_status": self.processing_status,
            "playback_ref": self.playback_ref,
            "poster_ref": self.poster_ref,
            "duration_ms": self.duration_ms,
            "failure_reason": self.failure_reason,
        }
