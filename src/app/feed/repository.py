"""Repository layer for feed items."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.feed.models import FeedItem


class FeedRepository:
    """Persist and query feed items."""

    def list_feed_items(
        self,
        session: Session,
        *,
        user_id: UUID,
        offset: int,
        limit: int,
    ) -> list[FeedItem]:
        """Return a page of feed items for a user."""

        statement = (
            select(FeedItem)
            .where(FeedItem.user_id == user_id)
            .order_by(FeedItem.created_at.desc(), FeedItem.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(statement).scalars().all())

    def count_feed_items(self, session: Session, *, user_id: UUID) -> int:
        """Return the total number of feed items for a user."""

        statement = select(func.count()).select_from(FeedItem).where(FeedItem.user_id == user_id)
        return int(session.execute(statement).scalar_one())
