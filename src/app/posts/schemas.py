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

    title: TitleField = Field(description="Human-readable post title.")
    body: BodyField = Field(description="Primary post body content.")
    status: PostStatus = Field(
        default=PostStatus.DRAFT,
        description="Publication state for the post. Defaults to `draft`.",
    )
    author_id: UUID = Field(description="Existing user id that owns the post.")


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

    title: OptionalTitleField = Field(default=None, description="Updated post title.")
    body: OptionalBodyField = Field(default=None, description="Updated post body.")
    status: PostStatus | None = Field(
        default=None,
        description="Updated publication state for the post.",
    )
    author_id: UUID | None = Field(
        default=None,
        description="Updated author id. Must reference an existing user.",
    )


class PostResponse(BaseModel):
    """Serialized post returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "de305d54-75b4-431b-adb2-eb6b9e546014",
                "title": "Introducing Posts API v1",
                "body": "This release adds CRUD operations for posts.",
                "status": "published",
                "author_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
                "published_at": "2026-05-28T12:00:00Z",
                "created_at": "2026-05-28T11:45:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            }
        },
    )

    id: UUID = Field(description="Unique identifier for the post.")
    title: str = Field(description="Human-readable post title.")
    body: str = Field(description="Primary post body content.")
    status: PostStatus = Field(description="Publication state for the post.")
    author_id: UUID = Field(description="User id that owns the post.")
    published_at: datetime | None = Field(
        description="Timestamp when the post entered the `published` state.",
    )
    created_at: datetime = Field(description="Timestamp when the post was created.")
    updated_at: datetime = Field(description="Timestamp when the post was last updated.")


class PostListResponse(BaseModel):
    """Paginated posts list response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "de305d54-75b4-431b-adb2-eb6b9e546014",
                        "title": "Introducing Posts API v1",
                        "body": "This release adds CRUD operations for posts.",
                        "status": "published",
                        "author_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
                        "published_at": "2026-05-28T12:00:00Z",
                        "created_at": "2026-05-28T11:45:00Z",
                        "updated_at": "2026-05-28T12:00:00Z",
                    }
                ],
                "page": 1,
                "limit": 20,
                "total": 57,
            }
        }
    )

    items: list[PostResponse] = Field(
        description="Posts returned for the requested page after filters and sorting are applied.",
    )
    page: int = Field(ge=1, description="1-based page number echoed in the response.")
    limit: int = Field(ge=1, description="Page size echoed in the response.")
    total: int = Field(
        ge=0,
        description="Total number of posts that match the filters before pagination.",
    )


class DeletePostResponse(BaseModel):
    """Delete post response payload."""

    message: str


class ErrorResponse(BaseModel):
    """Simple structured error response."""

    detail: str
