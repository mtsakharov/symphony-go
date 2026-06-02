"""Pydantic schemas for chat endpoints."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

QuestionField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
]
SessionIdField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class ChatResponseStatus(StrEnum):
    """Stable status values for the chat answer contract."""

    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    EMPTY_STATE = "empty_state"


class ChatQuestionRequest(BaseModel):
    """Payload for asking a post-grounded question."""

    question: QuestionField
    session_id: SessionIdField | None = None


class ChatCitation(BaseModel):
    """Normalized citation metadata for an answered post."""

    post_id: str
    title: str | None = None
    url: str | None = None
    snippet: str | None = None
    source: str | None = None


class ChatQuestionResponse(BaseModel):
    """Normalized API response for post-grounded answers."""

    answer_text: str | None = None
    citations: list[ChatCitation] = Field(default_factory=list)
    status: ChatResponseStatus


class ErrorDetail(BaseModel):
    """Stable machine-readable API error payload."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Error response wrapper used by the chat endpoint."""

    detail: ErrorDetail
