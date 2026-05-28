"""Pydantic schemas for tag endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

TagNameField = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
TagDescriptionField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]


class TagCreate(BaseModel):
    """Payload for creating a tag."""

    name: TagNameField
    description: TagDescriptionField | None = None


class TagUpdate(BaseModel):
    """Payload for updating a tag."""

    name: TagNameField | None = None
    description: TagDescriptionField | None = None


class TagResponse(BaseModel):
    """Serialized tag returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class TagListResponse(BaseModel):
    """Paginated tags list response."""

    items: list[TagResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)


class DeleteTagResponse(BaseModel):
    """Delete tag response payload."""

    message: str
