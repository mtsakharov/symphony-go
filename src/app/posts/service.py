"""Service layer for post creation."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.posts.exceptions import (
    DuplicateAssetReferenceError,
    MediaAssetNotFoundError,
    PostValidationError,
)
from app.posts.models import MediaAsset, MediaAssetType, MediaState, Post, PostType, UploadStatus
from app.posts.repository import PostRepository
from app.posts.schemas import MediaAssetResponse, PostCreate, PostResponse


class PostService:
    """Business logic for creating posts."""

    def __init__(self, repository: PostRepository | None = None) -> None:
        self.repository = repository or PostRepository()

    def create_post(self, session: Session, payload: PostCreate) -> PostResponse:
        """Create a post after validating referenced media assets."""

        self._validate_caption(payload)
        self._validate_duplicate_assets(payload.asset_ids)

        assets = self._load_assets(session, payload.asset_ids)
        self._validate_post_assets(payload.post_type, assets)

        post = Post(
            post_type=payload.post_type,
            caption=payload.caption or "",
            media_state=MediaState.READY,
        )

        self.repository.create_post(session, post=post, assets=assets)
        session.commit()

        persisted_post = self.repository.get_post_by_id(session, post.id)
        if persisted_post is None:
            raise PostValidationError("Created post could not be loaded")

        return self._serialize_post(persisted_post)

    def _validate_caption(self, payload: PostCreate) -> None:
        if payload.post_type is PostType.TEXT and not payload.caption:
            raise PostValidationError("Text posts require caption text")

    def _validate_duplicate_assets(self, asset_ids: Sequence[UUID]) -> None:
        if len(asset_ids) != len(set(asset_ids)):
            raise DuplicateAssetReferenceError("Asset references must be unique")

    def _load_assets(self, session: Session, asset_ids: Sequence[UUID]) -> list[MediaAsset]:
        if not asset_ids:
            return []

        assets = self.repository.get_assets_by_ids(session, asset_ids)
        assets_by_id = {asset.id: asset for asset in assets}
        missing_asset_ids = [
            str(asset_id) for asset_id in asset_ids if asset_id not in assets_by_id
        ]
        if missing_asset_ids:
            raise MediaAssetNotFoundError(
                "Referenced media assets were not found: " + ", ".join(missing_asset_ids)
            )

        return [assets_by_id[asset_id] for asset_id in asset_ids]

    def _validate_post_assets(self, post_type: PostType, assets: Sequence[MediaAsset]) -> None:
        if post_type is PostType.TEXT:
            if assets:
                raise PostValidationError("Text posts cannot reference media assets")
            return

        if post_type is PostType.IMAGE:
            if not assets:
                raise PostValidationError("Image posts require at least one image asset")
            self._validate_asset_statuses(assets)
            self._validate_asset_types(assets, expected_type=MediaAssetType.IMAGE)
            return

        if len(assets) != 1:
            raise PostValidationError("Video posts require exactly one video asset")

        self._validate_asset_statuses(assets)
        self._validate_asset_types(assets, expected_type=MediaAssetType.VIDEO)

    def _validate_asset_statuses(self, assets: Sequence[MediaAsset]) -> None:
        for asset in assets:
            if asset.upload_status is UploadStatus.FAILED:
                raise PostValidationError(f"Media asset {asset.id} upload failed")
            if asset.upload_status is not UploadStatus.COMPLETED:
                raise PostValidationError(f"Media asset {asset.id} is not ready")

    def _validate_asset_types(
        self,
        assets: Sequence[MediaAsset],
        *,
        expected_type: MediaAssetType,
    ) -> None:
        invalid_asset_ids = [
            str(asset.id) for asset in assets if asset.media_type is not expected_type
        ]
        if invalid_asset_ids:
            raise PostValidationError(
                f"Referenced assets must be {expected_type.value}: " + ", ".join(invalid_asset_ids)
            )

    def _serialize_post(self, post: Post) -> PostResponse:
        assets = [post_asset.asset for post_asset in post.post_assets]
        return PostResponse(
            id=post.id,
            post_type=post.post_type,
            caption=post.caption,
            media_state=post.media_state,
            assets=[MediaAssetResponse.model_validate(asset) for asset in assets],
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
