"""Integration tests for video asset endpoints."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.assets.models import VideoAsset
from app.assets.pipeline import VideoProcessingFailure, VideoProcessingResult


class FailingVideoPipeline:
    """Pipeline double that simulates a transcode failure."""

    def transcode(self, asset: VideoAsset) -> VideoProcessingResult:
        raise VideoProcessingFailure("transcode_failed")


@pytest.mark.asyncio
async def test_create_video_asset_persists_ready_state(
    client: AsyncClient,
) -> None:
    """Posting upload-complete should eventually persist a ready asset."""

    create_response = await client.post(
        "/api/v1/video-assets/upload-complete",
        json={
            "source_key": "uploads/videos/demo.mp4",
            "file_name": "demo.mp4",
            "mime_type": "video/mp4",
        },
    )

    assert create_response.status_code == 202
    created_asset = create_response.json()
    assert created_asset["status"] == "processing"
    assert created_asset["is_playable"] is False

    get_response = await client.get(f"/api/v1/video-assets/{created_asset['id']}")

    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["status"] == "ready"
    assert payload["is_playable"] is True
    assert payload["failure_reason"] is None
    assert payload["playback_metadata"] == {
        "playback_url": "uploads/videos/demo/master.m3u8",
        "content_type": "application/x-mpegURL",
        "duration_seconds": 0.0,
        "width": 1920,
        "height": 1080,
    }
    assert payload["poster_metadata"] == {
        "url": "uploads/videos/demo/poster.jpg",
        "content_type": "image/jpeg",
        "width": 1920,
        "height": 1080,
    }
    assert payload["thumbnail_metadata"] == {
        "url": "uploads/videos/demo/thumbnail.jpg",
        "content_type": "image/jpeg",
        "width": 480,
        "height": 270,
    }


@pytest.mark.asyncio
async def test_create_video_asset_persists_failed_state(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """A pipeline failure should persist a non-playable failed asset."""

    app.state.video_pipeline = FailingVideoPipeline()

    create_response = await client.post(
        "/api/v1/video-assets/upload-complete",
        json={
            "source_key": "uploads/videos/broken.mp4",
            "file_name": "broken.mp4",
            "mime_type": "video/mp4",
        },
    )

    assert create_response.status_code == 202
    created_asset = create_response.json()

    get_response = await client.get(f"/api/v1/video-assets/{created_asset['id']}")

    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["status"] == "failed"
    assert payload["is_playable"] is False
    assert payload["failure_reason"] == "transcode_failed"
    assert payload["playback_metadata"] is None
    assert payload["poster_metadata"] is None
    assert payload["thumbnail_metadata"] is None


@pytest.mark.asyncio
async def test_get_video_asset_returns_not_found(client: AsyncClient) -> None:
    """Fetching a missing asset should return 404."""

    response = await client.get(f"/api/v1/video-assets/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Video asset not found"}
