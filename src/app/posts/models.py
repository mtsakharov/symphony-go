"""Post database models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.media.models import utc_now

if TYPE_CHECKING:
    from app.media.models import MediaAsset


class PostType(StrEnum):
    """Supported post types."""

    VIDEO = "video"


class Post(Base):
    """Database model for created posts."""

    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_type: Mapped[PostType] = mapped_column(
        Enum(PostType, name="post_type", native_enum=False),
    )
    caption: Mapped[str] = mapped_column(String(2200), default="", server_default="")
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

    assets: Mapped[list[MediaAsset]] = relationship(back_populates="post")
