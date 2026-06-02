"""Repository layer for posts and post index records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.posts.models import Post, PostIndexRecord


class PostRepository:
    """Persist and query posts."""

    def get_by_id(self, session: Session, post_id: UUID) -> Post | None:
        """Return a post by id if present."""

        return session.get(Post, post_id)

    def create(self, session: Session, *, post: Post) -> Post:
        """Persist a new post."""

        session.add(post)
        session.flush()
        return post

    def delete(self, session: Session, *, post: Post) -> None:
        """Delete an existing post."""

        session.delete(post)
        session.flush()


class PostIndexRecordRepository:
    """Persist and query post index records."""

    def get_by_post_and_user(
        self,
        session: Session,
        *,
        post_id: UUID,
        user_id: UUID,
    ) -> PostIndexRecord | None:
        """Return a single index record for the given post and user."""

        statement = select(PostIndexRecord).where(
            PostIndexRecord.post_id == post_id,
            PostIndexRecord.user_id == user_id,
        )
        return session.execute(statement).scalar_one_or_none()

    def list_by_post(self, session: Session, *, post_id: UUID) -> list[PostIndexRecord]:
        """Return all index records for the given post."""

        statement = select(PostIndexRecord).where(PostIndexRecord.post_id == post_id)
        return list(session.execute(statement).scalars().all())

    def save(self, session: Session, *, record: PostIndexRecord) -> PostIndexRecord:
        """Persist an index record."""

        session.add(record)
        session.flush()
        return record
