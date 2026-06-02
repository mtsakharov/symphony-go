"""Repository helpers for post persistence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.posts.models import Post


class PostRepository:
    """Persistence access for posts."""

    def create(self, session: Session, *, post: Post) -> None:
        """Persist a new post."""

        session.add(post)

    def get_by_id(
        self,
        session: Session,
        post_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Post | None:
        """Return a post with its assets loaded."""

        statement = select(Post).options(selectinload(Post.assets)).where(Post.id == post_id)
        if not include_deleted:
            statement = statement.where(Post.deleted_at.is_(None))
        return session.execute(statement).scalar_one_or_none()

    def list_visible(self, session: Session) -> list[Post]:
        """Return visible posts."""

        statement = (
            select(Post)
            .options(selectinload(Post.assets))
            .where(Post.deleted_at.is_(None))
            .order_by(Post.created_at.desc())
        )
        return list(session.execute(statement).scalars())

