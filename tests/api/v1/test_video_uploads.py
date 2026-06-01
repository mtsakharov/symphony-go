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
    assert payload["asset"]["mime_type"] == "video/mp4"
    assert payload["asset"]["codec"] == "h264"
    assert payload["asset"]["file_size_bytes"] == 5_000_000
    assert payload["asset"]["duration_seconds"] == 45
    assert "id" in payload
    assert "created_at" in payload


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


@pytest.mark.asyncio
async def test_initiate_video_upload_rejects_unsupported_format(client: AsyncClient) -> None:
    """Unsupported MIME types or codecs should return a machine-readable failure."""

    response = await client.post(
        "/api/v1/video-uploads",
        json=build_request_payload(mime_type="video/quicktime", codec="hevc"),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "unsupported_format",
        "message": "Video format is not supported",
    }


@pytest.mark.asyncio
async def test_initiate_video_upload_rejects_oversized_file(client: AsyncClient) -> None:
    """Files above the configured size limit should be rejected."""

    response = await client.post(
        "/api/v1/video-uploads",
        json=build_request_payload(file_size_bytes=100_000_001),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "file_too_large",
        "message": "Video file exceeds the configured size limit",
    }


@pytest.mark.asyncio
async def test_initiate_video_upload_rejects_too_long_duration(client: AsyncClient) -> None:
    """Videos longer than the configured duration limit should be rejected."""

    response = await client.post(
        "/api/v1/video-uploads",
        json=build_request_payload(duration_seconds=181),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "duration_too_long",
        "message": "Video duration exceeds the configured limit",
    }
