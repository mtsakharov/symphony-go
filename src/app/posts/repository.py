"""Repository layer for canonical post reads."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.posts.models import Post


class PostRepository:
    """Persist and query posts."""

    def create(self, session: Session, *, post: Post) -> Post:
        """Persist a new post."""

        session.add(post)
        session.flush()
        return post

    def list_by_ids_for_user(
        self,
        session: Session,
        *,
        post_ids: Sequence[UUID],
        user_id: UUID,
    ) -> list[Post]:
        """Return posts matching the requested ids for a single user."""

        if not post_ids:
            return []

        statement = select(Post).where(Post.user_id == user_id, Post.id.in_(post_ids))
        return list(session.execute(statement).scalars().all())
