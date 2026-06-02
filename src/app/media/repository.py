"""Repository helpers for media lifecycle persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.media.models import MediaAsset, MediaLifecycleState


class MediaRepository:
    """Persistence access for media lifecycle entities."""

    def create(self, session: Session, *, asset: MediaAsset) -> None:
        """Persist a new media asset."""

        session.add(asset)

    def get_by_id(self, session: Session, asset_id: UUID) -> MediaAsset | None:
        """Return a media asset by id."""

        return session.get(MediaAsset, asset_id)

    def get_by_id_with_relations(self, session: Session, asset_id: UUID) -> MediaAsset | None:
        """Return a media asset with its source and derived relations loaded."""

        statement = (
            select(MediaAsset)
            .options(
                selectinload(MediaAsset.source_media),
                selectinload(MediaAsset.derived_assets),
            )
            .where(MediaAsset.id == asset_id)
        )
        return session.execute(statement).scalar_one_or_none()

    def list_by_ids(self, session: Session, asset_ids: Sequence[UUID]) -> list[MediaAsset]:
        """Return assets matching the provided ids."""

        if not asset_ids:
            return []
        statement = select(MediaAsset).where(MediaAsset.id.in_(asset_ids))
        return list(session.execute(statement).scalars())

    def list_by_post_id(self, session: Session, post_id: UUID) -> list[MediaAsset]:
        """Return media assets associated with a post."""

        statement = (
            select(MediaAsset)
            .where(MediaAsset.post_id == post_id)
            .order_by(MediaAsset.asset_role, MediaAsset.created_at)
        )
        return list(session.execute(statement).scalars())

    def list_due_for_cleanup(
        self,
        session: Session,
        *,
        now: datetime,
        limit: int,
    ) -> list[MediaAsset]:
        """Return assets that are due for cleanup."""

        due_states = (
            MediaLifecycleState.PENDING_UPLOAD,
            MediaLifecycleState.PENDING_DELETE,
        )
        statement: Select[tuple[MediaAsset]] = (
            select(MediaAsset)
            .where(
                MediaAsset.lifecycle_state.in_(due_states),
                MediaAsset.cleanup_after.is_not(None),
                MediaAsset.cleanup_after <= now,
            )
            .order_by(MediaAsset.cleanup_after, MediaAsset.created_at)
            .limit(limit)
        )
        return list(session.execute(statement).scalars())

