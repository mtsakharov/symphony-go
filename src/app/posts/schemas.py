"""Pydantic schemas for post endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.posts.models import PostVisibility

PostBody = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
OptionalPostBody = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=5000),
    ]
    | None
)


class PostCreate(BaseModel):
    """Payload for creating a post."""

    author_id: UUID
    body: PostBody
    visibility: PostVisibility = PostVisibility.PUBLIC


class PostUpdate(BaseModel):
    """Payload for updating a post."""

    body: OptionalPostBody = None
    visibility: PostVisibility | None = None


class PostResponse(BaseModel):
    """Serialized post returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    author_id: UUID
    body: str
    visibility: PostVisibility
    version: int
    created_at: datetime
    updated_at: datetime


class DeletePostResponse(BaseModel):
    """Delete post response payload."""

    message: str


class PostIndexRecordResponse(BaseModel):
    """Serialized index state for post integration tests and debugging."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    user_id: UUID
    source_version: int
    indexed_body: str
    content_hash: str
    visibility: PostVisibility | None
    is_active: bool
    invalidated_at: datetime | None
    invalidation_reason: str | None
    last_operation: str
    last_synced_at: datetime


class PostWithIndexResponse(PostResponse):
    """Serialized post including current index state."""

    index_record: PostIndexRecordResponse | None = Field(default=None)
