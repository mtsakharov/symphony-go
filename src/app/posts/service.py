"""Service layer for posts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.posts.exceptions import PostNotFoundError
from app.posts.models import Post
from app.posts.repository import PostRepository
from app.posts.schemas import PostCreate, PostListResponse, PostResponse, PostUpdate


class PostService:
    """Business logic for post CRUD operations."""

    def __init__(self, repository: PostRepository | None = None) -> None:
        self.repository = repository or PostRepository()

    def create_post(self, session: Session, payload: PostCreate) -> PostResponse:
        """Create a new post."""

        post = Post(
            title=payload.title,
            content=payload.content,
            is_published=payload.is_published,
        )
        self.repository.create(session, post=post)
        session.commit()
        session.refresh(post)
        return PostResponse.model_validate(post)

    def list_posts(self, session: Session, *, page: int, limit: int) -> PostListResponse:
        """Return a paginated list of posts."""

        offset = (page - 1) * limit
        posts = self.repository.list_posts(session, offset=offset, limit=limit)
        total = self.repository.count_posts(session)
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

        for field_name, value in payload.model_dump(exclude_unset=True).items():
            setattr(post, field_name, value)

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
