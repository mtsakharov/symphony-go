"""Schemas for grounded answer requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class AnswerRequest(BaseModel):
    """Request payload for generating an answer."""

    user_id: str = Field(min_length=1, max_length=255)
    question: str = Field(min_length=1, max_length=4_000)


class Citation(BaseModel):
    """Citation metadata for a supporting post."""

    post_id: str
    excerpt: str
    permalink: HttpUrl | None = None
    score: float | None = None


class AnswerResponse(BaseModel):
    """Grounded answer result."""

    answer: str
    is_fallback: bool
    citations: list[Citation]
