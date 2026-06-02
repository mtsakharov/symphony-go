"""Service layer for posts."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.media.models import MediaAssetRole, MediaAssetType, MediaLifecycleState, utc_now
from app.media.repository import MediaRepository
from app.posts.exceptions import PostNotFoundError, PostValidationError
from app.posts.models import Post, PostType
from app.posts.repository import PostRepository
from app.posts.schemas import PostCreate, PostResponse


class PostService:
    """Business logic for video posts."""

    def __init__(
        self,
        repository: PostRepository | None = None,
        media_repository: MediaRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository or PostRepository()
        self.media_repository = media_repository or MediaRepository()
        self.settings = settings or get_settings()

    def create_post(self, session: Session, payload: PostCreate) -> PostResponse:
        """Create a post from a completed upload."""

        if payload.post_type is not PostType.VIDEO:
            raise PostValidationError("Only video posts are supported")

        if len(set(payload.asset_ids)) != len(payload.asset_ids):
            raise PostValidationError("Asset references must be unique")

        source_assets = self.media_repository.list_by_ids(session, payload.asset_ids)
        if len(source_assets) != 1:
            raise PostValidationError("Video posts require exactly one completed upload")

        source_asset = source_assets[0]
        if source_asset.media_type is not MediaAssetType.VIDEO:
            raise PostValidationError("Referenced assets must be video uploads")
        if source_asset.asset_role is not MediaAssetRole.SOURCE:
            raise PostValidationError("Video posts must be created from source uploads")
        if source_asset.lifecycle_state is not MediaLifecycleState.COMPLETED_UPLOAD:
            raise PostValidationError(f"Media asset {source_asset.id} is not ready")
        if source_asset.post_id is not None:
            raise PostValidationError("Video upload is already attached to a post")

        post = Post(post_type=PostType.VIDEO, caption=payload.caption)
        self.repository.create(session, post=post)
        session.flush()

        source_asset.post_id = post.id
        source_asset.lifecycle_state = MediaLifecycleState.ATTACHED
        source_asset.cleanup_after = None
        session.add(source_asset)
        session.commit()

        persisted_post = self.repository.get_by_id(session, post.id)
        if persisted_post is None:
            raise PostValidationError("Created post could not be loaded")
        return self._serialize_post(persisted_post)

    def get_post(self, session: Session, post_id: UUID) -> PostResponse:
        """Return a visible post by id."""

        post = self.repository.get_by_id(session, post_id)
        if post is None:
            raise PostNotFoundError("Post not found")
        return self._serialize_post(post)

    def list_posts(self, session: Session) -> list[PostResponse]:
        """Return visible posts only."""

        return [self._serialize_post(post) for post in self.repository.list_visible(session)]

    def delete_post(self, session: Session, post_id: UUID) -> None:
        """Soft-delete a post and mark owned assets for cleanup."""

        post = self.repository.get_by_id(session, post_id, include_deleted=True)
        if post is None:
            return

        now = utc_now()
        if post.deleted_at is None:
            post.deleted_at = now
            session.add(post)

        retention = timedelta(seconds=self.settings.media_delete_retention_seconds)
        for asset in self.media_repository.list_by_post_id(session, post_id):
            if asset.lifecycle_state in {
                MediaLifecycleState.PENDING_DELETE,
                MediaLifecycleState.DELETED,
            }:
                continue

            asset.lifecycle_state = MediaLifecycleState.PENDING_DELETE
            asset.cleanup_after = now + retention
            session.add(asset)

        session.commit()

    def _serialize_post(self, post: Post) -> PostResponse:
        active_assets = [
            asset
            for asset in post.assets
            if asset.lifecycle_state is MediaLifecycleState.ATTACHED
        ]
        return PostResponse(
            id=post.id,
            post_type=post.post_type,
            caption=post.caption,
            assets=active_assets,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )

