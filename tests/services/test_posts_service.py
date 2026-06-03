"""Unit tests for the posts service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.posts.exceptions import PostAuthorNotFoundError, PostNotFoundError
from app.posts.models import Post, PostStatus
from app.posts.repository import PostRepository
from app.posts.schemas import PostCreate, PostSortField, PostUpdate, SortOrder
from app.posts.service import PostService


def build_post(
    *,
    status: PostStatus = PostStatus.DRAFT,
    published_at: datetime | None = None,
) -> Post:
    """Return a hydrated post model for service tests."""

    now = datetime.now(UTC)
    return Post(
        id=uuid4(),
        title="Hello world",
        body="Post body",
        status=status,
        author_id=uuid4(),
        published_at=published_at,
        created_at=now,
        updated_at=now,
    )


def test_create_post_raises_when_author_is_missing() -> None:
    """Service should reject creation when the author does not exist."""

    repository = Mock(spec=PostRepository)
    repository.author_exists.return_value = False
    service = PostService(repository=repository)
    session = Mock()

    with pytest.raises(PostAuthorNotFoundError, match="Author not found"):
        service.create_post(
            session,
            PostCreate(
                title="Hello world",
                body="Post body",
                author_id=uuid4(),
            ),
        )


def test_get_post_raises_not_found_when_missing() -> None:
    """Service should raise a domain error when a post does not exist."""

    repository = Mock(spec=PostRepository)
    repository.get_by_id.return_value = None
    service = PostService(repository=repository)
    session = Mock()

    with pytest.raises(PostNotFoundError, match="Post not found"):
        service.get_post(session, uuid4())


def test_update_post_sets_published_at_when_publishing() -> None:
    """Service should timestamp a post when it becomes published."""

    repository = Mock(spec=PostRepository)
    post = build_post()
    repository.get_by_id.return_value = post
    repository.author_exists.return_value = True
    service = PostService(repository=repository)
    session = Mock()

    response = service.update_post(
        session,
        post.id,
        PostUpdate(status=PostStatus.PUBLISHED, title="Published"),
    )

    assert response.status == PostStatus.PUBLISHED
    assert response.title == "Published"
    assert response.published_at is not None
    session.commit.assert_called_once()


def test_update_post_clears_published_at_when_moving_back_to_draft() -> None:
    """Service should clear publication timestamp when draft is restored."""

    repository = Mock(spec=PostRepository)
    post = build_post(status=PostStatus.PUBLISHED, published_at=datetime.now(UTC))
    repository.get_by_id.return_value = post
    repository.author_exists.return_value = True
    service = PostService(repository=repository)
    session = Mock()

    response = service.update_post(
        session,
        post.id,
        PostUpdate(status=PostStatus.DRAFT),
    )

    assert response.status == PostStatus.DRAFT
    assert response.published_at is None


def test_list_posts_normalizes_search_and_preserves_pagination_metadata() -> None:
    """Service should normalize list query inputs before calling the repository."""

    repository = Mock(spec=PostRepository)
    repository.list_posts.return_value = [build_post()]
    repository.count_posts.return_value = 7
    service = PostService(repository=repository)
    session = Mock()
    author_id = uuid4()

    response = service.list_posts(
        session,
        page=3,
        limit=2,
        status=PostStatus.PUBLISHED,
        author_id=author_id,
        search="  launch  ",
        sort_by=PostSortField.TITLE,
        sort_order=SortOrder.ASC,
    )

    repository.list_posts.assert_called_once_with(
        session,
        offset=4,
        limit=2,
        status=PostStatus.PUBLISHED,
        author_id=author_id,
        search="launch",
        sort_by="title",
        sort_order="asc",
    )
    repository.count_posts.assert_called_once_with(
        session,
        status=PostStatus.PUBLISHED,
        author_id=author_id,
        search="launch",
    )
    assert response.page == 3
    assert response.limit == 2
    assert response.total == 7
