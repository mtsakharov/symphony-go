"""Pydantic schemas for post endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.posts.models import PostStatus

TitleField = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
BodyField = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OptionalTitleField = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    ]
    | None
)
OptionalBodyField = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None


class PostSortField(StrEnum):
    """Supported list sorting fields."""

    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    PUBLISHED_AT = "published_at"
    TITLE = "title"


class SortOrder(StrEnum):
    """Supported sorting directions."""

    ASC = "asc"
    DESC = "desc"


class PostCreate(BaseModel):
    """Payload for creating a post."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "title": "Introducing Posts API v1",
                "body": "This release adds CRUD operations for posts.",
                "status": "draft",
                "author_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
            }
        },
    )

    title: TitleField
    body: BodyField
    status: PostStatus = Field(default=PostStatus.DRAFT)
    author_id: UUID


class PostUpdate(BaseModel):
    """Payload for partially updating a post."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "title": "Introducing Posts API v1",
                "status": "published",
            }
        },
    )

    title: OptionalTitleField = None
    body: OptionalBodyField = None
    status: PostStatus | None = None
    author_id: UUID | None = None


class PostResponse(BaseModel):
    """Serialized post returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    body: str
    status: PostStatus
    author_id: UUID
    published_at: datetime | None
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


class ErrorResponse(BaseModel):
    """Simple structured error response."""

    detail: str
