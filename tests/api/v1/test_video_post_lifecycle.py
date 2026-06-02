"""High-confidence integration coverage for the video-post lifecycle."""

from __future__ import annotations

from typing import Any, cast

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from tests.api.v1.test_users import create_user

from app.posts.pipeline import (
    VideoProcessingFailure,
    VideoProcessingPending,
    VideoProcessingResult,
)


class FailingVideoPipeline:
    """Pipeline double that simulates a terminal transcode failure."""

    def transcode(self, asset: object) -> VideoProcessingResult:
        del asset
        raise VideoProcessingFailure("transcode_failed")


class DeferredVideoPipeline:
    """Pipeline double that leaves the asset in processing."""

    def transcode(self, asset: object) -> VideoProcessingResult:
        del asset
        raise VideoProcessingPending()


async def create_video_post(client: AsyncClient, *, user_id: str, caption: str) -> dict[str, Any]:
    """Create a draft video post shell."""

    response = await client.post(
        "/api/v1/posts",
        json={"user_id": user_id, "post_type": "video", "caption": caption},
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


async def create_text_post(client: AsyncClient, *, user_id: str, caption: str) -> dict[str, Any]:
    """Create a ready text post."""

    response = await client.post(
        "/api/v1/posts",
        json={"user_id": user_id, "post_type": "text", "caption": caption},
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


async def initiate_upload(
    client: AsyncClient,
    *,
    post_id: str,
    overrides: dict[str, object] | None = None,
) -> dict[str, Any]:
    """Initiate a single valid upload slot."""

    payload: dict[str, list[dict[str, object]]] = {
        "assets": [
            {
                "filename": "launch.mp4",
                "mime_type": "video/mp4",
                "video_codec": "h264",
                "audio_codec": "aac-lc",
                "file_size_bytes": 5_000_000,
                "duration_seconds": 45,
            }
        ]
    }
    if overrides is not None:
        payload["assets"][0].update(overrides)

    response = await client.post(f"/api/v1/posts/{post_id}/video-uploads", json=payload)
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


async def complete_upload(
    client: AsyncClient,
    *,
    post_id: str,
    upload_id: str,
    source_key: str = "video-post-uploads/demo/launch.mp4",
) -> dict[str, Any]:
    """Finalize an upload and return the accepted processing response."""

    response = await client.post(
        f"/api/v1/posts/{post_id}/video-uploads/{upload_id}/complete",
        json={"source_key": source_key},
    )
    assert response.status_code == 202
    return cast(dict[str, Any], response.json())


@pytest.mark.asyncio
async def test_video_post_happy_path_becomes_playable_in_detail_and_feed(
    client: AsyncClient,
) -> None:
    """Upload, post creation, processing, and playback exposure should all line up."""

    created_user = await create_user(client)
    created_post = await create_video_post(
        client,
        user_id=str(created_user["id"]),
        caption="Launch clip",
    )
    upload = await initiate_upload(client, post_id=str(created_post["id"]))

    processing_response = await complete_upload(
        client,
        post_id=str(created_post["id"]),
        upload_id=str(upload["id"]),
    )
    assert processing_response["status"] == "processing"
    assert processing_response["video_asset"]["status"] == "processing"
    assert processing_response["video_asset"]["is_playable"] is False

    detail_response = await client.get(f"/api/v1/posts/{created_post['id']}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["status"] == "ready"
    assert detail_payload["video_asset"]["status"] == "ready"
    assert detail_payload["video_asset"]["is_playable"] is True
    assert detail_payload["video_asset"]["failure_reason"] is None
    assert detail_payload["video_asset"]["playback_metadata"]["playback_url"].endswith(
        "/master.m3u8"
    )

    feed_response = await client.get(f"/api/v1/users/{created_user['id']}/feed")
    assert feed_response.status_code == 200
    feed_payload = feed_response.json()
    assert feed_payload["total"] == 1
    assert feed_payload["items"][0]["id"] == created_post["id"]
    assert feed_payload["items"][0]["video_asset"]["is_playable"] is True


@pytest.mark.asyncio
async def test_validation_rejection_does_not_create_playable_video_asset(
    client: AsyncClient,
) -> None:
    """Server-side validation failures should leave the draft post non-playable."""

    created_user = await create_user(client)
    created_post = await create_video_post(
        client,
        user_id=str(created_user["id"]),
        caption="Rejected clip",
    )

    response = await client.post(
        f"/api/v1/posts/{created_post['id']}/video-uploads",
        json={
            "assets": [
                {
                    "filename": "rejected.mov",
                    "mime_type": "video/quicktime",
                    "video_codec": "hevc",
                    "audio_codec": "aac-lc",
                    "file_size_bytes": 5_000_000,
                    "duration_seconds": 45,
                }
            ]
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "unsupported_format",
        "message": "Video format is not supported",
    }

    detail_response = await client.get(f"/api/v1/posts/{created_post['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "draft"
    assert detail_response.json()["video_asset"] is None


@pytest.mark.asyncio
async def test_failed_video_asset_never_renders_playable_and_feed_keeps_surrounding_items(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """A degraded video item should not break adjacent healthy feed items."""

    app.state.video_pipeline = FailingVideoPipeline()
    created_user = await create_user(client)
    older_text_post = await create_text_post(
        client,
        user_id=str(created_user["id"]),
        caption="Older text item",
    )
    failed_video_post = await create_video_post(
        client,
        user_id=str(created_user["id"]),
        caption="Broken video",
    )
    newer_text_post = await create_text_post(
        client,
        user_id=str(created_user["id"]),
        caption="Newer text item",
    )
    upload = await initiate_upload(client, post_id=str(failed_video_post["id"]))
    await complete_upload(
        client,
        post_id=str(failed_video_post["id"]),
        upload_id=str(upload["id"]),
        source_key="video-post-uploads/demo/broken.mp4",
    )

    detail_response = await client.get(f"/api/v1/posts/{failed_video_post['id']}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["status"] == "failed"
    assert detail_payload["video_asset"]["status"] == "failed"
    assert detail_payload["video_asset"]["is_playable"] is False
    assert detail_payload["video_asset"]["playback_metadata"] is None
    assert detail_payload["video_asset"]["failure_reason"] == "transcode_failed"

    feed_response = await client.get(
        f"/api/v1/users/{created_user['id']}/feed",
        params={"page": 1, "limit": 10},
    )
    assert feed_response.status_code == 200
    feed_payload = feed_response.json()
    assert feed_payload["total"] == 3
    assert [item["id"] for item in feed_payload["items"]] == [
        newer_text_post["id"],
        failed_video_post["id"],
        older_text_post["id"],
    ]
    failed_item = feed_payload["items"][1]
    assert failed_item["video_asset"]["is_playable"] is False
    assert failed_item["video_asset"]["playback_metadata"] is None
    assert feed_payload["items"][0]["post_type"] == "text"
    assert feed_payload["items"][2]["post_type"] == "text"


@pytest.mark.asyncio
async def test_processing_video_remains_non_playable_while_feed_and_detail_still_render(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """Deferred processing should expose a stable non-playable processing state."""

    app.state.video_pipeline = DeferredVideoPipeline()
    created_user = await create_user(client)
    ready_text_post = await create_text_post(
        client,
        user_id=str(created_user["id"]),
        caption="Ready context",
    )
    created_post = await create_video_post(
        client,
        user_id=str(created_user["id"]),
        caption="Still processing",
    )
    upload = await initiate_upload(client, post_id=str(created_post["id"]))
    await complete_upload(
        client,
        post_id=str(created_post["id"]),
        upload_id=str(upload["id"]),
    )

    detail_response = await client.get(f"/api/v1/posts/{created_post['id']}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["status"] == "processing"
    assert detail_payload["video_asset"]["status"] == "processing"
    assert detail_payload["video_asset"]["is_playable"] is False
    assert detail_payload["video_asset"]["playback_metadata"] is None

    feed_response = await client.get(f"/api/v1/users/{created_user['id']}/feed")
    assert feed_response.status_code == 200
    feed_payload = feed_response.json()
    assert feed_payload["total"] == 2
    assert [item["id"] for item in feed_payload["items"]] == [
        created_post["id"],
        ready_text_post["id"],
    ]
    assert feed_payload["items"][0]["video_asset"]["is_playable"] is False
    assert feed_payload["items"][1]["post_type"] == "text"
