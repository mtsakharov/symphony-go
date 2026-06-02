"""Integration tests for video upload endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


def build_request_payload(**asset_overrides: object) -> dict[str, list[dict[str, object]]]:
    """Return a valid upload initiation request body."""

    asset = {
        "filename": "clip.mp4",
        "mime_type": "video/mp4",
        "codec": "h264",
        "file_size_bytes": 5_000_000,
        "duration_seconds": 45,
    }
    asset.update(asset_overrides)
    return {"assets": [asset]}


@pytest.mark.asyncio
async def test_initiate_video_upload_returns_pending_upload(client: AsyncClient) -> None:
    """A valid upload request should reserve a pending upload slot."""

    response = await client.post("/api/v1/video-uploads", json=build_request_payload())

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending_upload"
    assert payload["upload_path"].startswith("video-uploads/")
    assert payload["upload_path"].endswith("/clip.mp4")
    assert payload["cleanup_after"] is not None


@pytest.mark.asyncio
async def test_complete_video_upload_returns_completed_status(client: AsyncClient) -> None:
    """Completing a reserved upload should make it attachable to a post."""

    create_response = await client.post("/api/v1/video-uploads", json=build_request_payload())
    upload_id = create_response.json()["id"]

    complete_response = await client.post(f"/api/v1/video-uploads/{upload_id}/complete")

    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed_upload"
    assert complete_response.json()["cleanup_after"] is None


@pytest.mark.asyncio
async def test_initiate_video_upload_rejects_multiple_assets(client: AsyncClient) -> None:
    """The upload flow should only accept exactly one video asset."""

    payload = build_request_payload()
    first_asset = payload["assets"][0]
    payload["assets"] = [first_asset, first_asset]

    response = await client.post("/api/v1/video-uploads", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "invalid_asset_count",
        "message": "Exactly one video asset is required",
    }
