"""Unit tests for the post service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.posts.exceptions import VideoUploadValidationError
from app.posts.models import Post, PostStatus, PostType
from app.posts.repository import PostRepository
from app.posts.schemas import PostCreate, VideoUploadCreateRequest
from app.posts.service import PostService, VideoAssetProcessor
from app.users.models import User
from app.users.repository import UserRepository


def build_user() -> User:
    """Return a hydrated user for service tests."""

    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        email="user@example.com",
        first_name="John",
        last_name="Doe",
        password_hash="",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def build_post(
    *,
    post_type: PostType = PostType.VIDEO,
    status: PostStatus = PostStatus.DRAFT,
) -> Post:
    """Return a hydrated post model for service tests."""

    now = datetime.now(UTC)
    return Post(
        id=uuid4(),
        user_id=uuid4(),
        post_type=post_type,
        caption="caption",
        status=status,
        created_at=now,
        updated_at=now,
    )


def build_service(
    *,
    repository: PostRepository | None = None,
    user_repository: UserRepository | None = None,
) -> PostService:
    """Return a post service with mocked collaborators."""

    processor = Mock(spec=VideoAssetProcessor)
    return PostService(
        repository=repository,
        user_repository=user_repository,
        processor=processor,
    )


def test_create_text_post_sets_ready_status() -> None:
    """Text posts should be immediately ready."""

    repository = Mock(spec=PostRepository)
    user_repository = Mock(spec=UserRepository)
    user = build_user()
    user_repository.get_by_id.return_value = user
    post = build_post(post_type=PostType.TEXT, status=PostStatus.READY)
    repository.get_post_by_id.return_value = post
    service = build_service(repository=repository, user_repository=user_repository)
    session = Mock()

    response = service.create_post(
        session,
        PostCreate(user_id=user.id, post_type=PostType.TEXT, caption="Hello"),
    )

    assert response.status is PostStatus.READY
    session.commit.assert_called_once()


def test_initiate_video_upload_rejects_unsupported_audio_codec() -> None:
    """Upload initiation should enforce the server-side audio codec limit."""

    repository = Mock(spec=PostRepository)
    repository.get_post_by_id.return_value = build_post()
    service = build_service(repository=repository, user_repository=Mock(spec=UserRepository))
    session = Mock()

    with pytest.raises(VideoUploadValidationError, match="Audio format is not supported"):
        service.initiate_video_upload(
            session,
            post_id=repository.get_post_by_id.return_value.id,
            payload=VideoUploadCreateRequest(
                assets=[
                    {
                        "filename": "clip.mp4",
                        "mime_type": "video/mp4",
                        "video_codec": "h264",
                        "audio_codec": "opus",
                        "file_size_bytes": 5_000_000,
                        "duration_seconds": 45,
                    }
                ]
            ),
        )
