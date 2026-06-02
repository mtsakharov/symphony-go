"""Repository layer for posts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.posts.models import Post


class PostRepository:
    """Load posts for indexing."""

    def list_for_user(self, session: Session, user_id: UUID) -> list[Post]:
        """Return all posts owned by a single user in a deterministic order."""

        statement = (
            select(Post)
            .where(Post.user_id == user_id)
            .order_by(Post.created_at.asc(), Post.id.asc())
        )
        return list(session.execute(statement).scalars().all())
