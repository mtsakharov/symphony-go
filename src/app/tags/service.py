"""Service layer for tags."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.tags.exceptions import TagConflictError, TagNotFoundError
from app.tags.models import Tag
from app.tags.repository import TagRepository
from app.tags.schemas import TagCreate, TagListResponse, TagResponse, TagUpdate


class TagService:
    """Business logic for tag CRUD operations."""

    def __init__(self, repository: TagRepository | None = None) -> None:
        self.repository = repository or TagRepository()

    def create_tag(self, session: Session, payload: TagCreate) -> TagResponse:
        """Create a new tag if the name is unique."""

        if self.repository.get_by_name(session, payload.name) is not None:
            raise TagConflictError("Tag with this name already exists")

        tag = Tag(name=payload.name, description=payload.description)
        try:
            self.repository.create(session, tag=tag)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise TagConflictError("Tag with this name already exists") from exc

        session.refresh(tag)
        return TagResponse.model_validate(tag)

    def list_tags(self, session: Session, *, page: int, limit: int) -> TagListResponse:
        """Return a paginated list of tags."""

        offset = (page - 1) * limit
        tags = self.repository.list_tags(session, offset=offset, limit=limit)
        total = self.repository.count_tags(session)
        return TagListResponse(
            items=[TagResponse.model_validate(tag) for tag in tags],
            page=page,
            limit=limit,
            total=total,
        )

    def get_tag(self, session: Session, tag_id: UUID) -> TagResponse:
        """Return a single tag or raise if absent."""

        tag = self.repository.get_by_id(session, tag_id)
        if tag is None:
            raise TagNotFoundError("Tag not found")
        return TagResponse.model_validate(tag)

    def update_tag(self, session: Session, tag_id: UUID, payload: TagUpdate) -> TagResponse:
        """Apply partial updates to a tag."""

        tag = self.repository.get_by_id(session, tag_id)
        if tag is None:
            raise TagNotFoundError("Tag not found")

        if payload.name is not None:
            existing_tag = self.repository.get_by_name(session, payload.name)
            if existing_tag is not None and existing_tag.id != tag.id:
                raise TagConflictError("Tag with this name already exists")
            tag.name = payload.name

        if payload.description is not None:
            tag.description = payload.description

        try:
            session.add(tag)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise TagConflictError("Tag with this name already exists") from exc

        session.refresh(tag)
        return TagResponse.model_validate(tag)

    def delete_tag(self, session: Session, tag_id: UUID) -> None:
        """Delete a tag by id."""

        tag = self.repository.get_by_id(session, tag_id)
        if tag is None:
            raise TagNotFoundError("Tag not found")

        self.repository.delete(session, tag=tag)
        session.commit()
