"""Repository layer for tags."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.tags.models import Tag


class TagRepository:
    """Persist and query tags."""

    def get_by_id(self, session: Session, tag_id: UUID) -> Tag | None:
        """Return a tag by id if present."""

        return session.get(Tag, tag_id)

    def get_by_name(self, session: Session, name: str) -> Tag | None:
        """Return a tag by name if present."""

        statement = select(Tag).where(Tag.name == name)
        return session.execute(statement).scalar_one_or_none()

    def list_tags(self, session: Session, *, offset: int, limit: int) -> list[Tag]:
        """Return a page of tags ordered by creation time."""

        statement = select(Tag).order_by(Tag.created_at.desc(), Tag.id.desc()).offset(offset).limit(
            limit
        )
        return list(session.execute(statement).scalars().all())

    def count_tags(self, session: Session) -> int:
        """Return the total number of tags."""

        statement = select(func.count()).select_from(Tag)
        return int(session.execute(statement).scalar_one())

    def create(self, session: Session, *, tag: Tag) -> Tag:
        """Persist a new tag."""

        session.add(tag)
        session.flush()
        return tag

    def delete(self, session: Session, *, tag: Tag) -> None:
        """Delete an existing tag."""

        session.delete(tag)
        session.flush()
