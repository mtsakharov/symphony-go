"""Repository layer for posts and media assets."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.posts.models import MediaAsset, Post, PostAsset


class PostRepository:
    """Persist and query posts and media assets."""

    def get_assets_by_ids(self, session: Session, asset_ids: Sequence[UUID]) -> list[MediaAsset]:
        """Return all media assets that match the requested ids."""

        statement = select(MediaAsset).where(MediaAsset.id.in_(asset_ids))
        return list(session.execute(statement).scalars().all())

    def create_post(self, session: Session, *, post: Post, assets: Sequence[MediaAsset]) -> Post:
        """Persist a post and its asset associations."""

        session.add(post)
        session.flush()

        for position, asset in enumerate(assets):
            session.add(PostAsset(post=post, asset=asset, position=position))

        session.flush()
        return post

    def get_post_by_id(self, session: Session, post_id: UUID) -> Post | None:
        """Return a post with all linked assets."""

        statement = (
            select(Post)
            .options(selectinload(Post.post_assets).selectinload(PostAsset.asset))
            .where(Post.id == post_id)
        )
        return session.execute(statement).scalar_one_or_none()

