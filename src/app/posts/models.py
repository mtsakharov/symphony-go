"""Database models for posts, upload intents, and processed video assets."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.users.models import utc_now

if TYPE_CHECKING:
    from app.users.models import User


class PostType(StrEnum):
    """Supported post types."""

    TEXT = "text"
    VIDEO = "video"


class PostStatus(StrEnum):
    """Client-visible post lifecycle states."""

    DRAFT = "draft"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class VideoUploadStatus(StrEnum):
    """Upload-intent lifecycle states."""

    PENDING_UPLOAD = "pending_upload"
    COMPLETED = "completed"


class VideoAssetStatus(StrEnum):
    """Processed asset lifecycle states."""

    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Post(Base):
    """Database model for published and draft posts."""

    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    post_type: Mapped[PostType] = mapped_column(Enum(PostType, name="post_type"))
    caption: Mapped[str] = mapped_column(String(2200), default="", server_default="")
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, name="post_status"),
        default=PostStatus.DRAFT,
        server_default=PostStatus.DRAFT.value,
    )
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

    user: Mapped[User] = relationship(back_populates="posts")
    video_uploads: Mapped[list[VideoUpload]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="VideoUpload.created_at.desc()",
    )
    video_asset: Mapped[VideoAsset | None] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        uselist=False,
    )


class VideoUpload(Base):
    """Reserved upload slot for a single video asset."""

    __tablename__ = "video_uploads"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("posts.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    video_codec: Mapped[str] = mapped_column(String(100))
    audio_codec: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column()
    duration_seconds: Mapped[float] = mapped_column(Float)
    status: Mapped[VideoUploadStatus] = mapped_column(
        Enum(VideoUploadStatus, name="video_upload_status"),
        default=VideoUploadStatus.PENDING_UPLOAD,
        server_default=VideoUploadStatus.PENDING_UPLOAD.value,
    )
    upload_path: Mapped[str] = mapped_column(String(512), unique=True)
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

    post: Mapped[Post] = relationship(back_populates="video_uploads")
    video_asset: Mapped[VideoAsset | None] = relationship(back_populates="upload", uselist=False)


class VideoAsset(Base):
    """Processed video asset state attached to a post."""

    __tablename__ = "video_assets"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("posts.id", ondelete="CASCADE"),
        unique=True,
    )
    upload_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("video_uploads.id", ondelete="CASCADE"),
        unique=True,
    )
    source_key: Mapped[str] = mapped_column(String(512), unique=True)
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[VideoAssetStatus] = mapped_column(
        Enum(VideoAssetStatus, name="video_asset_status"),
        default=VideoAssetStatus.PROCESSING,
        server_default=VideoAssetStatus.PROCESSING.value,
    )
    is_playable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=func.false(),
    )
    playback_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    poster_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    thumbnail_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
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

    post: Mapped[Post] = relationship(back_populates="video_asset")
    upload: Mapped[VideoUpload] = relationship(back_populates="video_asset")
