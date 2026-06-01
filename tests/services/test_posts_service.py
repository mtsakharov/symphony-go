"""Unit tests for post service behavior."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.posts.exceptions import (
    DuplicateAssetReferenceError,
    MediaAssetNotFoundError,
    PostValidationError,
)
from app.posts.models import (
    MediaAsset,
    MediaAssetType,
    MediaState,
    Post,
    PostAsset,
    PostType,
    UploadStatus,
)
from app.posts.schemas import PostCreate
from app.posts.service import PostService


def build_media_asset(
    session: Session,
    *,
    media_type: MediaAssetType,
    upload_status: UploadStatus,
) -> MediaAsset:
    """Create and persist a media asset for tests."""

    asset = MediaAsset(media_type=media_type, upload_status=upload_status)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def test_create_video_post_persists_post_and_asset_link(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Creating a valid video post should persist the post and relation."""

    service = PostService()

    with db_session_factory() as session:
        asset = build_media_asset(
            session,
            media_type=MediaAssetType.VIDEO,
            upload_status=UploadStatus.COMPLETED,
        )

        response = service.create_post(
            session,
            PostCreate(post_type="video", caption="Launch clip", asset_ids=[asset.id]),
        )

        persisted_post = session.get(Post, response.id)
        persisted_link = session.execute(
            select(PostAsset).where(PostAsset.post_id == response.id)
        ).scalar_one()

        assert persisted_post is not None
        assert persisted_post.post_type is PostType.VIDEO
        assert persisted_post.caption == "Launch clip"
        assert persisted_post.media_state is MediaState.READY
        assert persisted_link.asset_id == asset.id
        assert response.assets[0].id == asset.id


def test_create_video_post_rejects_duplicate_asset_references(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Duplicate asset references should be rejected."""

    service = PostService()

    with db_session_factory() as session:
        asset = build_media_asset(
            session,
            media_type=MediaAssetType.VIDEO,
            upload_status=UploadStatus.COMPLETED,
        )

        with pytest.raises(DuplicateAssetReferenceError, match="Asset references must be unique"):
            service.create_post(
                session,
                PostCreate(post_type="video", asset_ids=[asset.id, asset.id]),
            )


@pytest.mark.parametrize("upload_status", [UploadStatus.PENDING, UploadStatus.FAILED])
def test_create_video_post_rejects_non_ready_asset(
    db_session_factory: sessionmaker[Session],
    upload_status: UploadStatus,
) -> None:
    """Non-ready assets should be rejected for video posts."""

    service = PostService()

    with db_session_factory() as session:
        asset = build_media_asset(
            session,
            media_type=MediaAssetType.VIDEO,
            upload_status=upload_status,
        )

        with pytest.raises(PostValidationError):
            service.create_post(
                session,
                PostCreate(post_type="video", asset_ids=[asset.id]),
            )


def test_create_video_post_rejects_multiple_assets(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Video posts should accept exactly one asset."""

    service = PostService()

    with db_session_factory() as session:
        first_asset = build_media_asset(
            session,
            media_type=MediaAssetType.VIDEO,
            upload_status=UploadStatus.COMPLETED,
        )
        second_asset = build_media_asset(
            session,
            media_type=MediaAssetType.VIDEO,
            upload_status=UploadStatus.COMPLETED,
        )

        with pytest.raises(PostValidationError, match="exactly one video asset"):
            service.create_post(
                session,
                PostCreate(post_type="video", asset_ids=[first_asset.id, second_asset.id]),
            )


def test_create_video_post_rejects_missing_asset(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Missing assets should be rejected."""

    service = PostService()
    missing_asset_id = uuid4()

    with (
        db_session_factory() as session,
        pytest.raises(MediaAssetNotFoundError, match=str(missing_asset_id)),
    ):
        service.create_post(
            session,
            PostCreate(post_type="video", asset_ids=[missing_asset_id]),
        )
