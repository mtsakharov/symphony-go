"""Database models for persisted tweet request drafts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.tweet_requests.schemas import TweetRequestStatus


def utc_now() -> datetime:
    """Return the current UTC datetime."""

    return datetime.now(UTC)


class TweetRequestDraft(Base):
    """Database model for draft tweet briefs."""

    __tablename__ = "tweet_requests"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    brief: Mapped[str | None] = mapped_column(String(2_000), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    objective: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    call_to_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(String(2_000), nullable=True)
    approved_by_compliance: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    approved_by_reviewer: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    status: Mapped[str] = mapped_column(
        String(64),
        default=TweetRequestStatus.DRAFT.value,
        server_default=TweetRequestStatus.DRAFT.value,
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
