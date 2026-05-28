"""Service layer for posts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.posts.exceptions import PostAuthorNotFoundError, PostNotFoundError
from app.posts.models import Post, PostStatus, utc_now
from app.posts.repository import PostRepository
from app.posts.schemas import (
    PostCreate,
    PostListResponse,
    PostResponse,
    PostSortField,
    PostUpdate,
    SortOrder,
)


class PostService:
    """Business logic for post CRUD operations."""

    def __init__(self, repository: PostRepository | None = None) -> None:
        self.repository = repository or PostRepository()

    def create_post(self, session: Session, payload: PostCreate) -> PostResponse:
        """Create a new post after validating the author."""

        self._ensure_author_exists(session, payload.author_id)

        post = Post(
            title=payload.title,
            body=payload.body,
            status=payload.status,
            author_id=payload.author_id,
        )
        self._apply_status(post, payload.status)

        self.repository.create(session, post=post)
        session.commit()
        session.refresh(post)
        return PostResponse.model_validate(post)

    def list_posts(
        self,
        session: Session,
        *,
        page: int,
        limit: int,
        status: PostStatus | None,
        author_id: UUID | None,
        search: str | None,
        sort_by: PostSortField,
        sort_order: SortOrder,
    ) -> PostListResponse:
        """Return a filtered paginated list of posts."""

        normalized_search = search.strip() if search else None
        offset = (page - 1) * limit
        posts = self.repository.list_posts(
            session,
            offset=offset,
            limit=limit,
            status=status,
            author_id=author_id,
            search=normalized_search or None,
            sort_by=sort_by.value,
            sort_order=sort_order.value,
        )
        total = self.repository.count_posts(
            session,
            status=status,
            author_id=author_id,
            search=normalized_search or None,
        )
        return PostListResponse(
            items=[PostResponse.model_validate(post) for post in posts],
            page=page,
            limit=limit,
            total=total,
        )

    def get_post(self, session: Session, post_id: UUID) -> PostResponse:
        """Return a single post or raise if absent."""

        post = self.repository.get_by_id(session, post_id)
        if post is None:
            raise PostNotFoundError("Post not found")
        return PostResponse.model_validate(post)

    def update_post(self, session: Session, post_id: UUID, payload: PostUpdate) -> PostResponse:
        """Apply partial updates to a post."""

        post = self.repository.get_by_id(session, post_id)
        if post is None:
            raise PostNotFoundError("Post not found")

        update_data = payload.model_dump(exclude_unset=True)
        author_id = update_data.pop("author_id", None)
        status = update_data.pop("status", None)

        if author_id is not None:
            self._ensure_author_exists(session, author_id)
            post.author_id = author_id

        for field_name, value in update_data.items():
            setattr(post, field_name, value)

        if status is not None:
            self._apply_status(post, status)

        session.add(post)
        session.commit()
        session.refresh(post)
        return PostResponse.model_validate(post)

    def delete_post(self, session: Session, post_id: UUID) -> None:
        """Delete a post by id."""

        post = self.repository.get_by_id(session, post_id)
        if post is None:
            raise PostNotFoundError("Post not found")

        self.repository.delete(session, post=post)
        session.commit()

    def _ensure_author_exists(self, session: Session, author_id: UUID) -> None:
        """Raise when a referenced author does not exist."""

        if not self.repository.author_exists(session, author_id):
            raise PostAuthorNotFoundError("Author not found")

    def _apply_status(self, post: Post, status: PostStatus) -> None:
        """Normalize publication timestamps based on post status."""

        post.status = status
        if status == PostStatus.PUBLISHED:
            if post.published_at is None:
                post.published_at = utc_now()
            return
        post.published_at = None
