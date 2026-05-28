"""Repository layer for posts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.posts.models import Post, PostStatus
from app.users.models import User


class PostRepository:
    """Persist and query posts."""

    def get_by_id(self, session: Session, post_id: UUID) -> Post | None:
        """Return a post by id if present."""

        return session.get(Post, post_id)

    def author_exists(self, session: Session, author_id: UUID) -> bool:
        """Return whether a referenced author exists."""

        return session.get(User, author_id) is not None

    def list_posts(
        self,
        session: Session,
        *,
        offset: int,
        limit: int,
        status: PostStatus | None,
        author_id: UUID | None,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> list[Post]:
        """Return a filtered page of posts."""

        statement = (
            self._build_filtered_statement(
                status=status,
                author_id=author_id,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(statement).scalars().all())

    def count_posts(
        self,
        session: Session,
        *,
        status: PostStatus | None,
        author_id: UUID | None,
        search: str | None,
    ) -> int:
        """Return the total number of posts matching the filters."""

        statement = self._build_filtered_statement(
            status=status,
            author_id=author_id,
            search=search,
            sort_by="created_at",
            sort_order="desc",
        )
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        return int(session.execute(count_statement).scalar_one())

    def create(self, session: Session, *, post: Post) -> Post:
        """Persist a new post."""

        session.add(post)
        session.flush()
        return post

    def delete(self, session: Session, *, post: Post) -> None:
        """Delete an existing post."""

        session.delete(post)
        session.flush()

    def _build_filtered_statement(
        self,
        *,
        status: PostStatus | None,
        author_id: UUID | None,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> Select[tuple[Post]]:
        """Build a filtered posts query with sorting applied."""

        statement = select(Post)

        if status is not None:
            statement = statement.where(Post.status == status)

        if author_id is not None:
            statement = statement.where(Post.author_id == author_id)

        if search:
            search_value = f"%{search.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(Post.title).like(search_value),
                    func.lower(Post.body).like(search_value),
                )
            )

        sort_column = {
            "created_at": Post.created_at,
            "updated_at": Post.updated_at,
            "published_at": Post.published_at,
            "title": Post.title,
        }[sort_by]
        order_expression = sort_column.asc() if sort_order == "asc" else sort_column.desc()
        tie_breaker = Post.id.asc() if sort_order == "asc" else Post.id.desc()
        return statement.order_by(order_expression, tie_breaker)
