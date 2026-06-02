"""Repository layer for posts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.posts.models import Post


class PostRepository:
    """Persist and query posts."""

    def get_by_id(self, session: Session, post_id: UUID) -> Post | None:
        """Return a post by id if present."""

        return session.get(Post, post_id)

    def list_feed(self, session: Session, *, offset: int, limit: int) -> list[Post]:
        """Return a page of posts ordered by creation time."""

        statement = (
            select(Post)
            .order_by(Post.created_at.desc(), Post.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(statement).scalars().all())

    def count_posts(self, session: Session) -> int:
        """Return the total number of posts."""

        statement = select(func.count()).select_from(Post)
        return int(session.execute(statement).scalar_one())
