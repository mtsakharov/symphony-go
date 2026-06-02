"""External chat request and response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request payload for a grounded chat turn."""

    user_id: UUID
    session_id: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)


class PostEvidence(BaseModel):
    """Serialized evidence returned with a grounded answer."""

    post_id: str
    content: str


class ChatResponse(BaseModel):
    """Response payload for a grounded chat turn."""

    session_id: str
    answer: str
    evidence: list[PostEvidence]
    history_turns_used: int = Field(ge=0)
