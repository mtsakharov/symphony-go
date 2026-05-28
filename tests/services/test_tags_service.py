"""Unit tests for the tags service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.tags.exceptions import TagConflictError, TagNotFoundError
from app.tags.models import Tag
from app.tags.repository import TagRepository
from app.tags.schemas import TagCreate, TagUpdate
from app.tags.service import TagService


def build_tag(*, name: str = "backend") -> Tag:
    """Return a hydrated tag model for service tests."""

    now = datetime.now(UTC)
    return Tag(
        id=uuid4(),
        name=name,
        description="Backend-facing resources",
        created_at=now,
        updated_at=now,
    )


def test_create_tag_raises_conflict_when_name_exists() -> None:
    """Service should raise a domain error for duplicate names."""

    repository = Mock(spec=TagRepository)
    repository.get_by_name.return_value = build_tag()
    service = TagService(repository=repository)
    session = Mock()

    with pytest.raises(TagConflictError, match="Tag with this name already exists"):
        service.create_tag(
            session,
            TagCreate(name="backend", description="Backend-facing resources"),
        )


def test_get_tag_raises_not_found_when_missing() -> None:
    """Service should raise a domain error when a tag does not exist."""

    repository = Mock(spec=TagRepository)
    repository.get_by_id.return_value = None
    service = TagService(repository=repository)
    session = Mock()

    with pytest.raises(TagNotFoundError, match="Tag not found"):
        service.get_tag(session, uuid4())


def test_update_tag_updates_existing_tag() -> None:
    """Service should apply partial updates to the loaded tag."""

    repository = Mock(spec=TagRepository)
    tag = build_tag()
    repository.get_by_id.return_value = tag
    repository.get_by_name.return_value = None
    service = TagService(repository=repository)
    session = Mock()

    response = service.update_tag(
        session,
        tag.id,
        TagUpdate(name="api", description="API-facing resources"),
    )

    assert response.name == "api"
    assert response.description == "API-facing resources"
    session.commit.assert_called_once()
