"""Posts and media asset database models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utc_now() -> datetime:
    """Return the current UTC datetime."""

    return datetime.now(UTC)


class MediaAssetType(StrEnum):
    """Supported media asset types."""

    IMAGE = "image"
    VIDEO = "video"


class UploadStatus(StrEnum):
    """Upload lifecycle states for media assets."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class PostType(StrEnum):
    """Supported post types."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"


class MediaState(StrEnum):
    """Client-visible media state for a post."""

    READY = "ready"


class MediaAsset(Base):
    """Database model for uploaded media assets."""

    __tablename__ = "media_assets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    media_type: Mapped[MediaAssetType] = mapped_column(
        Enum(MediaAssetType, name="media_asset_type"),
    )
    upload_status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, name="upload_status"),
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

    post_assets: Mapped[list[PostAsset]] = relationship(back_populates="asset")


class Post(Base):
    """Database model for created posts."""

    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    post_type: Mapped[PostType] = mapped_column(
        Enum(PostType, name="post_type"),
    )
    caption: Mapped[str] = mapped_column(String(2200), default="", server_default="")
    media_state: Mapped[MediaState] = mapped_column(
        Enum(MediaState, name="media_state"),
        default=MediaState.READY,
        server_default=MediaState.READY.value,
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

    post_assets: Mapped[list[PostAsset]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostAsset.position",
    )


class PostAsset(Base):
    """Association table between posts and media assets."""

    __tablename__ = "post_assets"
    __table_args__ = (
        UniqueConstraint("post_id", "position", name="uq_post_assets_post_position"),
    )

    post_id: Mapped[UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, default=0)

    post: Mapped[Post] = relationship(back_populates="post_assets")
    asset: Mapped[MediaAsset] = relationship(back_populates="post_assets")
