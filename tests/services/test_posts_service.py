"""Unit tests for the posts service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.posts.exceptions import PostNotFoundError
from app.posts.models import Post
from app.posts.repository import PostRepository
from app.posts.schemas import PostCreate, PostUpdate
from app.posts.service import PostService


def build_post(*, title: str = "First post", content: str = "Hello world") -> Post:
    """Return a hydrated post model for service tests."""

    now = datetime.now(UTC)
    return Post(
        id=uuid4(),
        title=title,
        content=content,
        is_published=False,
        created_at=now,
        updated_at=now,
    )


def test_create_post_persists_post() -> None:
    """Service should create a post and commit the transaction."""

    repository = Mock(spec=PostRepository)
    service = PostService(repository=repository)
    session = Mock()
    persisted_post = build_post()

    def persist_post(*args: object, **kwargs: object) -> Post:
        post = kwargs["post"]
        assert isinstance(post, Post)
        post.id = persisted_post.id
        post.created_at = persisted_post.created_at
        post.updated_at = persisted_post.updated_at
        return post

    repository.create.side_effect = persist_post

    service.create_post(
        session,
        PostCreate(title="First post", content="Hello world", is_published=True),
    )

    repository.create.assert_called_once()
    session.commit.assert_called_once()
    session.refresh.assert_called_once()


def test_get_post_raises_not_found_when_missing() -> None:
    """Service should raise a domain error when a post does not exist."""

    repository = Mock(spec=PostRepository)
    repository.get_by_id.return_value = None
    service = PostService(repository=repository)
    session = Mock()

    with pytest.raises(PostNotFoundError, match="Post not found"):
        service.get_post(session, uuid4())


def test_update_post_updates_existing_post() -> None:
    """Service should apply partial updates to the loaded post."""

    repository = Mock(spec=PostRepository)
    post = build_post()
    repository.get_by_id.return_value = post
    service = PostService(repository=repository)
    session = Mock()

    response = service.update_post(
        session,
        post.id,
        PostUpdate(title="Updated post", is_published=True),
    )

    assert response.title == "Updated post"
    assert response.content == "Hello world"
    assert response.is_published is True
    session.commit.assert_called_once()


def test_delete_post_raises_not_found_when_missing() -> None:
    """Service should raise a domain error when deleting a missing post."""

    repository = Mock(spec=PostRepository)
    repository.get_by_id.return_value = None
    service = PostService(repository=repository)
    session = Mock()

    with pytest.raises(PostNotFoundError, match="Post not found"):
        service.delete_post(session, uuid4())
