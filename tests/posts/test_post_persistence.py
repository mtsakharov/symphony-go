"""Persistence tests for posts and video asset metadata."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.posts.models import Post
from app.posts.schemas import PostResponse, VideoProcessingStatus


def test_post_without_video_metadata_round_trips(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Posts without video metadata should continue to load without a video asset."""

    with db_session_factory() as session:
        post = Post(body="text-only post")
        session.add(post)
        session.commit()
        post_id = post.id

    with db_session_factory() as session:
        loaded = session.get(Post, post_id)

    assert loaded is not None
    assert loaded.media_type is None
    assert PostResponse.model_validate(loaded).video_asset is None


@pytest.mark.parametrize(
    ("status", "builder"),
    [
        (
            VideoProcessingStatus.PROCESSING,
            lambda: {
                "upload_ref": "upload-123",
                "poster_ref": "poster-processing.jpg",
            },
        ),
        (
            VideoProcessingStatus.READY,
            lambda: {
                "asset_ref": "asset-456",
                "playback_ref": "https://cdn.example.com/video.m3u8",
                "poster_ref": "https://cdn.example.com/poster.jpg",
                "duration_ms": 12_345,
            },
        ),
        (
            VideoProcessingStatus.FAILED,
            lambda: {
                "upload_ref": "upload-789",
                "failure_reason": "transcode_failed",
            },
        ),
    ],
)
def test_video_asset_states_persist_and_serialize(
    db_session_factory: sessionmaker[Session],
    status: VideoProcessingStatus,
    builder: Callable[[], dict[str, str | int]],
) -> None:
    """Video asset metadata should survive a save/load round trip."""

    payload = builder()

    with db_session_factory() as session:
        post = Post(
            body="video post",
            media_type="video",
            processing_status=status.value,
            upload_ref=payload.get("upload_ref"),
            asset_ref=payload.get("asset_ref"),
            playback_ref=payload.get("playback_ref"),
            poster_ref=payload.get("poster_ref"),
            duration_ms=payload.get("duration_ms"),
            failure_reason=payload.get("failure_reason"),
        )
        session.add(post)
        session.commit()
        post_id = post.id

    with db_session_factory() as session:
        loaded = session.get(Post, post_id)

    assert loaded is not None
    assert loaded.media_type == "video"
    assert loaded.processing_status == status.value

    response = PostResponse.model_validate(loaded)

    assert response.video_asset is not None
    assert response.video_asset.media_type == "video"
    assert response.video_asset.processing_status == status
    assert response.video_asset.upload_ref == payload.get("upload_ref")
    assert response.video_asset.asset_ref == payload.get("asset_ref")
    assert response.video_asset.playback_ref == payload.get("playback_ref")
    assert response.video_asset.poster_ref == payload.get("poster_ref")
    assert response.video_asset.duration_ms == payload.get("duration_ms")
    assert response.video_asset.failure_reason == payload.get("failure_reason")
