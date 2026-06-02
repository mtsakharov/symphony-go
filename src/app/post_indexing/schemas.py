"""Shared types for post indexing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


@dataclass(frozen=True, slots=True)
class SourcePost:
    """Normalized post payload consumed by the indexing service."""

    id: UUID
    user_id: UUID
    title: str
    body: str
    visibility: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    is_archived: bool
    is_deleted: bool


@dataclass(frozen=True, slots=True)
class PostChunk:
    """Deterministic text chunk derived from a single post."""

    chunk_id: str
    chunk_index: int
    text: str


@dataclass(frozen=True, slots=True)
class IndexedPostChunk:
    """Persistable payload for one indexed post chunk."""

    user_id: UUID
    post_id: UUID
    chunk_id: str
    chunk_index: int
    content: str
    embedding: list[float]
    visibility: str
    source_created_at: datetime
    source_updated_at: datetime
    source_published_at: datetime | None


class PostIndexingSummary(BaseModel):
    """Summary returned after indexing one user's posts."""

    user_id: UUID
    indexed_posts: int = Field(ge=0)
    skipped_posts: int = Field(ge=0)
    removed_posts: int = Field(ge=0)
    indexed_chunks: int = Field(ge=0)
