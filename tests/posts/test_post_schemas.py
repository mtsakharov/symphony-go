"""Schema serialization tests for posts and video assets."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.posts.models import Post
from app.posts.schemas import PostResponse, VideoAsset, VideoProcessingStatus


def test_post_response_serializes_without_video_asset() -> None:
    """Posts without video metadata should serialize with a null video asset."""

    now = datetime.now(UTC)
    post = Post(
        id=uuid4(),
        body="plain text",
        created_at=now,
        updated_at=now,
    )

    response = PostResponse.model_validate(post)

    assert response.body == "plain text"
    assert response.video_asset is None


@pytest.mark.parametrize("status", list(VideoProcessingStatus))
def test_post_response_serializes_video_asset(status: VideoProcessingStatus) -> None:
    """Posts with video metadata should serialize each supported state."""

    now = datetime.now(UTC)
    post = Post(
        id=uuid4(),
        body="video post",
        media_type="video",
        upload_ref="upload-123",
        processing_status=status.value,
        playback_ref="https://cdn.example.com/video.m3u8"
        if status == VideoProcessingStatus.READY
        else None,
        poster_ref="https://cdn.example.com/poster.jpg",
        duration_ms=98_765 if status == VideoProcessingStatus.READY else None,
        failure_reason="transcode_failed" if status == VideoProcessingStatus.FAILED else None,
        created_at=now,
        updated_at=now,
    )

    response = PostResponse.model_validate(post)

    assert response.video_asset is not None
    assert response.video_asset.media_type == "video"
    assert response.video_asset.processing_status == status


def test_video_asset_rejects_non_video_media_type() -> None:
    """The schema should reject non-video media types for this iteration."""

    with pytest.raises(ValidationError):
        VideoAsset(
            media_type="image",
            upload_ref="upload-123",
            processing_status=VideoProcessingStatus.PROCESSING,
        )
