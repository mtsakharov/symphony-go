"""Unit tests for post lifecycle behavior."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.media.models import MediaAsset, MediaLifecycleState
from app.media.schemas import VideoUploadCreateRequest
from app.media.service import MediaService
from app.posts.models import Post
from app.posts.schemas import PostCreate
from app.posts.service import PostService


def build_settings(**overrides: object) -> Settings:
    """Return deterministic settings for post lifecycle tests."""

    defaults: dict[str, object] = {
        "database_url": "sqlite:///unused.db",
        "media_abandoned_upload_timeout_seconds": 600,
        "media_delete_retention_seconds": 0,
    }
    defaults.update(overrides)
    return Settings(**cast(dict[str, Any], defaults))


def build_upload_request() -> VideoUploadCreateRequest:
    """Return a valid upload initiation request body."""

    return VideoUploadCreateRequest(
        assets=[
            {
                "filename": "clip.mp4",
                "mime_type": "video/mp4",
                "codec": "h264",
                "file_size_bytes": 5_000_000,
                "duration_seconds": 45,
            }
        ]
    )


def test_create_post_attaches_completed_upload_and_clears_timeout(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Creating a video post should atomically attach the completed upload."""

    media_service = MediaService(settings=build_settings())
    post_service = PostService(settings=build_settings())

    with db_session_factory() as session:
        upload = media_service.initiate_video_upload(session, build_upload_request())
        media_service.complete_video_upload(session, upload.id)

        response = post_service.create_post(
            session,
            PostCreate(post_type="video", caption="Launch clip", asset_ids=[upload.id]),
        )
        asset = session.get(MediaAsset, upload.id)

        assert asset is not None
        assert asset.post_id == response.id
        assert asset.lifecycle_state is MediaLifecycleState.ATTACHED
        assert asset.cleanup_after is None


def test_delete_post_marks_source_and_derived_assets_for_cleanup_idempotently(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Deleting a post should mark all owned assets for cleanup and repeat safely."""

    settings = build_settings(media_delete_retention_seconds=30)
    media_service = MediaService(settings=settings)
    post_service = PostService(settings=settings)

    with db_session_factory() as session:
        upload = media_service.initiate_video_upload(session, build_upload_request())
        media_service.complete_video_upload(session, upload.id)
        created_post = post_service.create_post(
            session,
            PostCreate(post_type="video", caption="Launch clip", asset_ids=[upload.id]),
        )
        derived_asset = media_service.create_derived_asset(
            session,
            post_id=created_post.id,
            source_asset_id=upload.id,
            filename="master.m3u8",
            mime_type="application/x-mpegURL",
            storage_path="video-public/master.m3u8",
        )

        post_service.delete_post(session, created_post.id)
        post_service.delete_post(session, created_post.id)

        source_asset = session.get(MediaAsset, upload.id)
        persisted_derived_asset = session.get(MediaAsset, derived_asset.id)
        post = session.get(Post, created_post.id)

        assert post is not None
        assert post.deleted_at is not None
        assert source_asset is not None
        assert source_asset.lifecycle_state is MediaLifecycleState.PENDING_DELETE
        assert source_asset.cleanup_after is not None
        assert persisted_derived_asset is not None
        assert persisted_derived_asset.lifecycle_state is MediaLifecycleState.PENDING_DELETE
        assert persisted_derived_asset.cleanup_after is not None
        assert persisted_derived_asset.cleanup_after.replace(tzinfo=None) == (
            source_asset.cleanup_after.replace(tzinfo=None)
        )
