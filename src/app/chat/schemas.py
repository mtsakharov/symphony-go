"""Schemas for the posts chat integration."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

QuestionField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1_000),
]
SessionIdField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class ChatState(StrEnum):
    """Normalized UI states returned by the posts chat endpoint."""

    ANSWERED = "answered"
    NO_POSTS = "no_posts"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class PostsChatRequest(BaseModel):
    """Question payload submitted by the client."""

    question: QuestionField
    session_id: SessionIdField | None = None


class Citation(BaseModel):
    """Visible citation metadata rendered beneath an answer."""

    title: QuestionField
    url: str | None = None
    excerpt: str | None = Field(default=None, max_length=500)
    post_id: str | None = None


class PostsChatResponse(BaseModel):
    """Normalized response returned to the thin chat UI."""

    answer: str = Field(min_length=1)
    state: ChatState
    session_id: str | None = None
    citations: list[Citation] = Field(default_factory=list)
