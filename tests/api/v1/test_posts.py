"""Integration tests for post endpoints."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from app.posts.models import MediaAsset, MediaAssetType, UploadStatus


def create_media_asset(
    db_session_factory: sessionmaker[Session],
    *,
    media_type: MediaAssetType,
    upload_status: UploadStatus,
) -> MediaAsset:
    """Persist and return a media asset for test setup."""

    with db_session_factory() as session:
        asset = MediaAsset(media_type=media_type, upload_status=upload_status)
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return asset


@pytest.mark.asyncio
async def test_create_text_post_returns_created_post(client: AsyncClient) -> None:
    """Creating a text post should succeed without assets."""

    response = await client.post(
        "/api/v1/posts",
        json={"post_type": "text", "caption": "Hello from text"},
    )

    assert response.status_code == 201
    assert response.json()["post_type"] == "text"
    assert response.json()["caption"] == "Hello from text"
    assert response.json()["media_state"] == "ready"
    assert response.json()["assets"] == []


@pytest.mark.asyncio
async def test_create_image_post_returns_created_post(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Creating an image post should keep image-post behavior working."""

    asset = create_media_asset(
        db_session_factory,
        media_type=MediaAssetType.IMAGE,
        upload_status=UploadStatus.COMPLETED,
    )

    response = await client.post(
        "/api/v1/posts",
        json={
            "post_type": "image",
            "caption": "Image caption",
            "asset_ids": [str(asset.id)],
        },
    )

    assert response.status_code == 201
    assert response.json()["post_type"] == "image"
    assert response.json()["assets"] == [
        {
            "id": str(asset.id),
            "media_type": "image",
            "upload_status": "completed",
        }
    ]


@pytest.mark.asyncio
async def test_create_video_post_returns_created_post(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Creating a video post should return immediate client metadata."""

    asset = create_media_asset(
        db_session_factory,
        media_type=MediaAssetType.VIDEO,
        upload_status=UploadStatus.COMPLETED,
    )

    response = await client.post(
        "/api/v1/posts",
        json={
            "post_type": "video",
            "caption": "Launch clip",
            "asset_ids": [str(asset.id)],
        },
    )

    payload = response.json()

    assert response.status_code == 201
    assert payload["post_type"] == "video"
    assert payload["caption"] == "Launch clip"
    assert payload["media_state"] == "ready"
    assert payload["assets"] == [
        {
            "id": str(asset.id),
            "media_type": "video",
            "upload_status": "completed",
        }
    ]
    assert "id" in payload
    assert "created_at" in payload
    assert "updated_at" in payload


@pytest.mark.asyncio
async def test_create_video_post_rejects_duplicate_asset_references(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Creating a video post with duplicate asset ids should fail."""

    asset = create_media_asset(
        db_session_factory,
        media_type=MediaAssetType.VIDEO,
        upload_status=UploadStatus.COMPLETED,
    )

    response = await client.post(
        "/api/v1/posts",
        json={"post_type": "video", "asset_ids": [str(asset.id), str(asset.id)]},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Asset references must be unique"}


@pytest.mark.asyncio
async def test_create_video_post_rejects_multiple_assets(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Creating a video post with more than one asset should fail."""

    first_asset = create_media_asset(
        db_session_factory,
        media_type=MediaAssetType.VIDEO,
        upload_status=UploadStatus.COMPLETED,
    )
    second_asset = create_media_asset(
        db_session_factory,
        media_type=MediaAssetType.VIDEO,
        upload_status=UploadStatus.COMPLETED,
    )

    response = await client.post(
        "/api/v1/posts",
        json={
            "post_type": "video",
            "asset_ids": [str(first_asset.id), str(second_asset.id)],
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Video posts require exactly one video asset"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("upload_status", "expected_detail"),
    [
        (UploadStatus.PENDING, "is not ready"),
        (UploadStatus.FAILED, "upload failed"),
    ],
)
async def test_create_video_post_rejects_non_ready_or_failed_asset(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
    upload_status: UploadStatus,
    expected_detail: str,
) -> None:
    """Creating a video post with an unavailable asset should fail."""

    asset = create_media_asset(
        db_session_factory,
        media_type=MediaAssetType.VIDEO,
        upload_status=upload_status,
    )

    response = await client.post(
        "/api/v1/posts",
        json={"post_type": "video", "asset_ids": [str(asset.id)]},
    )

    assert response.status_code == 400
    assert expected_detail in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_video_post_rejects_missing_asset(client: AsyncClient) -> None:
    """Creating a video post with a missing asset should fail."""

    missing_asset_id = uuid4()

    response = await client.post(
        "/api/v1/posts",
        json={"post_type": "video", "asset_ids": [str(missing_asset_id)]},
    )

    assert response.status_code == 404
    assert str(missing_asset_id) in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_video_post_rejects_invalid_asset_type(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Creating a video post with a non-video asset should fail."""

    asset = create_media_asset(
        db_session_factory,
        media_type=MediaAssetType.IMAGE,
        upload_status=UploadStatus.COMPLETED,
    )

    response = await client.post(
        "/api/v1/posts",
        json={"post_type": "video", "asset_ids": [str(asset.id)]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == f"Referenced assets must be video: {asset.id}"
