"""Repository layer for media."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.media.models import Media


class MediaRepository:
    """Persist and query media metadata."""

    def get_by_id(self, session: Session, media_id: UUID) -> Media | None:
        """Return a media record by id if present."""

        return session.get(Media, media_id)

    def list_media(self, session: Session, *, offset: int, limit: int) -> list[Media]:
        """Return a page of media ordered by creation time."""

        statement = (
            select(Media)
            .order_by(Media.created_at.desc(), Media.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(statement).scalars().all())

    def count_media(self, session: Session) -> int:
        """Return the total number of media records."""

        statement = select(func.count()).select_from(Media)
        return int(session.execute(statement).scalar_one())

    def create(self, session: Session, *, media: Media) -> Media:
        """Persist a new media record."""

        session.add(media)
        session.flush()
        return media

    def delete(self, session: Session, *, media: Media) -> None:
        """Delete an existing media record."""

        session.delete(media)
        session.flush()

