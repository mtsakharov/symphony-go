"""Repository layer for video assets."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.assets.models import VideoAsset


class VideoAssetRepository:
    """Persist and query video assets."""

    def get_by_id(self, session: Session, asset_id: UUID) -> VideoAsset | None:
        """Return a video asset by id if present."""

        return session.get(VideoAsset, asset_id)

    def create(self, session: Session, *, asset: VideoAsset) -> VideoAsset:
        """Persist a new video asset."""

        session.add(asset)
        session.flush()
        return asset
