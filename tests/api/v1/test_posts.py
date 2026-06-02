"""Integration tests for post and cleanup endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.media.models import MediaAsset, MediaLifecycleState
from app.media.service import MediaCleanupService, MediaService
from app.media.storage import LocalMediaStorage


def build_request_payload() -> dict[str, list[dict[str, object]]]:
    """Return a valid upload initiation request body."""

    return {
        "assets": [
            {
                "filename": "clip.mp4",
                "mime_type": "video/mp4",
                "codec": "h264",
                "file_size_bytes": 5_000_000,
                "duration_seconds": 45,
            }
        ]
    }


def build_settings(tmp_path: Path) -> Settings:
    """Return deterministic settings for integration helpers."""

    return Settings(
        database_url="sqlite:///unused.db",
        media_storage_dir=str(tmp_path),
        media_delete_retention_seconds=0,
        media_cleanup_batch_size=10,
    )


@pytest.mark.asyncio
async def test_pending_uploads_do_not_surface_as_visible_posts(client: AsyncClient) -> None:
    """Reserved uploads should not appear in visible post responses."""

    create_upload = await client.post("/api/v1/video-uploads", json=build_request_payload())
    assert create_upload.status_code == 201

    list_response = await client.get("/api/v1/posts")

    assert list_response.status_code == 200
    assert list_response.json() == []


@pytest.mark.asyncio
async def test_delete_video_post_marks_assets_and_cleanup_removes_files(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    """Deleting a post should hide it and allow cleanup to tombstone source and derived assets."""

    upload_response = await client.post("/api/v1/video-uploads", json=build_request_payload())
    upload_id = cast(str, upload_response.json()["id"])
    await client.post(f"/api/v1/video-uploads/{upload_id}/complete")
    create_post_response = await client.post(
        "/api/v1/posts",
        json={"post_type": "video", "caption": "Launch clip", "asset_ids": [upload_id]},
    )
    post_id = cast(str, create_post_response.json()["id"])

    media_service = MediaService(settings=build_settings(tmp_path))
    storage = LocalMediaStorage(storage_dir=tmp_path)
    cleanup_service = MediaCleanupService(storage=storage, settings=build_settings(tmp_path))

    with db_session_factory() as session:
        source_asset = session.get(MediaAsset, UUID(upload_id))
        assert source_asset is not None
        storage.resolve_path(source_asset.storage_path).parent.mkdir(parents=True, exist_ok=True)
        storage.resolve_path(source_asset.storage_path).write_bytes(b"source")

        derived_asset = media_service.create_derived_asset(
            session,
            post_id=UUID(cast(str, create_post_response.json()["id"])),
            source_asset_id=source_asset.id,
            filename="master.m3u8",
            mime_type="application/x-mpegURL",
            storage_path="video-public/master.m3u8",
        )
        storage.resolve_path(derived_asset.storage_path).parent.mkdir(parents=True, exist_ok=True)
        storage.resolve_path(derived_asset.storage_path).write_bytes(b"derived")

    delete_response = await client.delete(f"/api/v1/posts/{post_id}")
    get_response = await client.get(f"/api/v1/posts/{post_id}")

    assert delete_response.status_code == 200
    assert get_response.status_code == 404

    with db_session_factory() as session:
        summary = cleanup_service.run_once(session)
        refreshed_source = session.get(MediaAsset, UUID(upload_id))
        refreshed_derived = session.get(MediaAsset, derived_asset.id)

        assert summary.processed == 2
        assert refreshed_source is not None
        assert refreshed_source.lifecycle_state is MediaLifecycleState.DELETED
        assert refreshed_derived is not None
        assert refreshed_derived.lifecycle_state is MediaLifecycleState.DELETED
        assert not storage.resolve_path("video-public/master.m3u8").exists()
