"""Integration tests for feed and post endpoints."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from app.posts.models import Post, PostType, VideoProcessingStatus


def seed_post(
    db_session_factory: sessionmaker[Session],
    *,
    post_type: PostType = PostType.VIDEO,
    body: str = "A post body",
    video_status: VideoProcessingStatus | None = VideoProcessingStatus.PROCESSING,
    video_playback_reference: str | None = None,
    video_failure_reason: str | None = None,
    video_poster_url: str | None = "https://cdn.example.com/poster.jpg",
    video_poster_width: int | None = 1280,
    video_poster_height: int | None = 720,
    video_thumbnail_url: str | None = "https://cdn.example.com/thumb.jpg",
    video_thumbnail_width: int | None = 320,
    video_thumbnail_height: int | None = 180,
) -> UUID:
    """Insert a post fixture directly into the test database."""

    with db_session_factory() as session:
        post = Post(
            post_type=post_type,
            body=body,
            video_caption="Caption text",
            video_duration_seconds=42,
            video_status=video_status,
            video_playback_reference=video_playback_reference,
            video_failure_reason=video_failure_reason,
            video_poster_url=video_poster_url,
            video_poster_width=video_poster_width,
            video_poster_height=video_poster_height,
            video_thumbnail_url=video_thumbnail_url,
            video_thumbnail_width=video_thumbnail_width,
            video_thumbnail_height=video_thumbnail_height,
        )
        session.add(post)
        session.commit()
        return post.id


def get_feed_item(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the first feed item from a feed response."""

    items = cast(Sequence[dict[str, Any]], payload["items"])
    assert len(items) == 1
    return items[0]


def assert_video_media(
    payload: dict[str, Any],
    *,
    expected_status: str,
    expected_playable: bool,
    expected_playback_reference: str | None,
    expected_failure_reason: str | None,
    expect_thumbnail: bool,
) -> None:
    """Assert the shared video media response shape."""

    assert payload["post_type"] == "video"
    assert payload["video_media"] == {
        "status": expected_status,
        "is_playable": expected_playable,
        "caption": "Caption text",
        "duration_seconds": 42,
        "poster": {
            "url": "https://cdn.example.com/poster.jpg",
            "width": 1280,
            "height": 720,
        },
        "thumbnail": (
            {
                "url": "https://cdn.example.com/thumb.jpg",
                "width": 320,
                "height": 180,
            }
            if expect_thumbnail
            else None
        ),
        "playback_reference": expected_playback_reference,
        "failure_reason": expected_failure_reason,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("video_status", "video_playback_reference", "video_failure_reason", "expected_playable"),
    [
        (VideoProcessingStatus.PROCESSING, None, None, False),
        (VideoProcessingStatus.READY, "playback://video-123", None, True),
        (VideoProcessingStatus.FAILED, "playback://should-not-leak", "transcode_failed", False),
    ],
)
async def test_feed_and_detail_return_expected_video_states(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
    video_status: VideoProcessingStatus,
    video_playback_reference: str | None,
    video_failure_reason: str | None,
    expected_playable: bool,
) -> None:
    """Feed and detail endpoints should share the same state mapping contract."""

    post_id = seed_post(
        db_session_factory,
        video_status=video_status,
        video_playback_reference=video_playback_reference,
        video_failure_reason=video_failure_reason,
    )

    feed_response = await client.get("/api/v1/feed")
    detail_response = await client.get(f"/api/v1/posts/{post_id}")

    assert feed_response.status_code == 200
    assert detail_response.status_code == 200
    assert feed_response.json()["total"] == 1

    assert_video_media(
        get_feed_item(cast(dict[str, Any], feed_response.json())),
        expected_status=video_status.value,
        expected_playable=expected_playable,
        expected_playback_reference=(
            video_playback_reference if video_status is VideoProcessingStatus.READY else None
        ),
        expected_failure_reason=(
            video_failure_reason if video_status is VideoProcessingStatus.FAILED else None
        ),
        expect_thumbnail=True,
    )
    assert_video_media(
        cast(dict[str, Any], detail_response.json()),
        expected_status=video_status.value,
        expected_playable=expected_playable,
        expected_playback_reference=(
            video_playback_reference if video_status is VideoProcessingStatus.READY else None
        ),
        expected_failure_reason=(
            video_failure_reason if video_status is VideoProcessingStatus.FAILED else None
        ),
        expect_thumbnail=True,
    )


@pytest.mark.asyncio
async def test_feed_and_detail_return_null_thumbnail_when_metadata_is_incomplete(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Incomplete thumbnail metadata should serialize as null."""

    post_id = seed_post(
        db_session_factory,
        video_status=VideoProcessingStatus.READY,
        video_playback_reference="playback://video-123",
        video_thumbnail_height=None,
    )

    feed_response = await client.get("/api/v1/feed")
    detail_response = await client.get(f"/api/v1/posts/{post_id}")

    assert feed_response.status_code == 200
    assert detail_response.status_code == 200

    assert_video_media(
        get_feed_item(cast(dict[str, Any], feed_response.json())),
        expected_status="ready",
        expected_playable=True,
        expected_playback_reference="playback://video-123",
        expected_failure_reason=None,
        expect_thumbnail=False,
    )
    assert_video_media(
        cast(dict[str, Any], detail_response.json()),
        expected_status="ready",
        expected_playable=True,
        expected_playback_reference="playback://video-123",
        expected_failure_reason=None,
        expect_thumbnail=False,
    )


@pytest.mark.asyncio
async def test_get_post_returns_not_found_for_missing_post(client: AsyncClient) -> None:
    """Fetching a missing post should return 404."""

    response = await client.get(f"/api/v1/posts/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Post not found"}


@pytest.mark.asyncio
async def test_openapi_includes_feed_and_post_video_schema(client: AsyncClient) -> None:
    """OpenAPI should expose the new routes and video payload schema."""

    response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    payload = cast(dict[str, Any], response.json())
    assert "/api/v1/feed" in payload["paths"]
    assert "/api/v1/posts/{post_id}" in payload["paths"]
    assert "VideoMediaResponse" in payload["components"]["schemas"]
    post_schema = payload["components"]["schemas"]["PostResponse"]
    assert "video_media" in post_schema["properties"]
