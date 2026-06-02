"""Media lifecycle database models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BIGINT, JSON, DateTime, Enum, Float, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.posts.models import Post


def utc_now() -> datetime:
    """Return the current UTC datetime."""

    return datetime.now(UTC)


class MediaAssetType(StrEnum):
    """Supported media asset types."""

    VIDEO = "video"


class MediaAssetRole(StrEnum):
    """Relationship between an asset and the post lifecycle."""

    SOURCE = "source"
    DERIVED = "derived"


class MediaLifecycleState(StrEnum):
    """Lifecycle states for uploaded and derived assets."""

    PENDING_UPLOAD = "pending_upload"
    COMPLETED_UPLOAD = "completed_upload"
    ATTACHED = "attached"
    PENDING_DELETE = "pending_delete"
    DELETED = "deleted"


class MediaAsset(Base):
    """Database model for uploaded and derived media assets."""

    __tablename__ = "media_assets"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    media_type: Mapped[MediaAssetType] = mapped_column(
        Enum(MediaAssetType, name="media_asset_type", native_enum=False),
    )
    asset_role: Mapped[MediaAssetRole] = mapped_column(
        Enum(MediaAssetRole, name="media_asset_role", native_enum=False),
    )
    lifecycle_state: Mapped[MediaLifecycleState] = mapped_column(
        Enum(MediaLifecycleState, name="media_lifecycle_state", native_enum=False),
    )
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(255))
    codec: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    storage_path: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    details: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    post_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_media_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cleanup_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    post: Mapped[Post | None] = relationship(back_populates="assets")
    source_media: Mapped[MediaAsset | None] = relationship(
        remote_side="MediaAsset.id",
        back_populates="derived_assets",
    )
    derived_assets: Mapped[list[MediaAsset]] = relationship(back_populates="source_media")
