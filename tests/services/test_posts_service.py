"""Unit tests for the posts service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.posts.exceptions import PostNotFoundError
from app.posts.models import Post, PostType, VideoProcessingStatus
from app.posts.service import PostService


def build_post(
    *,
    post_type: PostType = PostType.VIDEO,
    video_status: VideoProcessingStatus | None = VideoProcessingStatus.PROCESSING,
    video_playback_reference: str | None = None,
    video_failure_reason: str | None = None,
    video_thumbnail_url: str | None = "https://cdn.example.com/thumb.jpg",
    video_thumbnail_width: int | None = 320,
    video_thumbnail_height: int | None = 180,
) -> Post:
    """Return a hydrated post model for service tests."""

    now = datetime.now(UTC)
    return Post(
        id=uuid4(),
        post_type=post_type,
        body="hello world",
        video_caption="Caption text",
        video_duration_seconds=42,
        video_status=video_status,
        video_playback_reference=video_playback_reference,
        video_failure_reason=video_failure_reason,
        video_poster_url="https://cdn.example.com/poster.jpg",
        video_poster_width=1280,
        video_poster_height=720,
        video_thumbnail_url=video_thumbnail_url,
        video_thumbnail_width=video_thumbnail_width,
        video_thumbnail_height=video_thumbnail_height,
        created_at=now,
        updated_at=now,
    )


def test_serialize_post_returns_ready_video_media() -> None:
    """Ready videos should expose playable metadata."""

    service = PostService()

    response = service.serialize_post(
        build_post(
            video_status=VideoProcessingStatus.READY,
            video_playback_reference="playback://video-123",
        )
    )

    assert response.video_media is not None
    assert response.video_media.status is VideoProcessingStatus.READY
    assert response.video_media.is_playable is True
    assert response.video_media.playback_reference == "playback://video-123"
    assert response.video_media.failure_reason is None
    assert response.video_media.thumbnail is not None


def test_serialize_post_returns_non_playable_processing_payload() -> None:
    """Processing videos should never expose playback fields."""

    service = PostService()

    response = service.serialize_post(build_post(video_status=VideoProcessingStatus.PROCESSING))

    assert response.video_media is not None
    assert response.video_media.status is VideoProcessingStatus.PROCESSING
    assert response.video_media.is_playable is False
    assert response.video_media.playback_reference is None
    assert response.video_media.failure_reason is None


def test_serialize_post_returns_failed_payload_with_reason() -> None:
    """Failed videos should carry failure context without playback."""

    service = PostService()

    response = service.serialize_post(
        build_post(
            video_status=VideoProcessingStatus.FAILED,
            video_failure_reason="transcode_failed",
            video_playback_reference="playback://should-not-leak",
        )
    )

    assert response.video_media is not None
    assert response.video_media.status is VideoProcessingStatus.FAILED
    assert response.video_media.is_playable is False
    assert response.video_media.playback_reference is None
    assert response.video_media.failure_reason == "transcode_failed"


def test_serialize_post_returns_null_thumbnail_when_metadata_is_incomplete() -> None:
    """Incomplete derived asset metadata should collapse to null."""

    service = PostService()

    response = service.serialize_post(
        build_post(
            video_status=VideoProcessingStatus.READY,
            video_playback_reference="playback://video-123",
            video_thumbnail_height=None,
        )
    )

    assert response.video_media is not None
    assert response.video_media.thumbnail is None
    assert response.video_media.poster is not None


def test_get_post_raises_not_found_when_missing() -> None:
    """Missing posts should raise a domain error."""

    repository = Mock()
    repository.get_by_id.return_value = None
    service = PostService(repository=repository)

    with pytest.raises(PostNotFoundError, match="Post not found"):
        service.get_post(session=Mock(), post_id=uuid4())
