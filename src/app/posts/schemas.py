"""Pydantic schemas for post endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

TitleField = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
ContentField = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OptionalTitleField = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    ]
    | None
)
OptionalContentField = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
    ]
    | None
)


class PostCreate(BaseModel):
    """Payload for creating a post."""

    title: TitleField
    content: ContentField
    is_published: bool = False


class PostUpdate(BaseModel):
    """Payload for updating a post."""

    title: OptionalTitleField = None
    content: OptionalContentField = None
    is_published: bool | None = None


class PostResponse(BaseModel):
    """Serialized post returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    is_published: bool
    created_at: datetime
    updated_at: datetime


class PostListResponse(BaseModel):
    """Paginated posts list response."""

    items: list[PostResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)


class DeletePostResponse(BaseModel):
    """Delete post response payload."""

    message: str
