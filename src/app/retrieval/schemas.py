"""Typed retrieval request and response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

QueryText = StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000)


class RetrievalQuery(BaseModel):
    """Request payload for a retrieval query."""

    query: str = Field(..., min_length=1, max_length=2_000)
    top_k: int | None = Field(default=None, ge=1)
    token_budget: int | None = Field(default=None, ge=1)


class SearchHit(BaseModel):
    """Candidate returned by the search backend."""

    post_id: UUID
    owner_user_id: UUID
    score: float
    search_rank: int = Field(ge=1)
    snippet: str
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)


class EvidenceRecord(BaseModel):
    """Evidence passed to the answer layer."""

    post_id: UUID
    owner_user_id: UUID
    score: float
    rank: int = Field(ge=1)
    search_rank: int = Field(ge=1)
    snippet: str
    token_count: int = Field(ge=1)
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)


class RetrievalResult(BaseModel):
    """Final retrieval output with support metadata."""

    user_id: UUID
    query: str
    requested_top_k: int = Field(ge=1)
    applied_top_k: int = Field(ge=1)
    token_budget: int = Field(ge=1)
    tokens_used: int = Field(ge=0)
    search_candidate_count: int = Field(ge=0)
    eligible_candidate_count: int = Field(ge=0)
    dropped_ineligible_count: int = Field(ge=0)
    truncated: bool
    has_sufficient_evidence: bool
    insufficient_reason: str | None = None
    evidence: list[EvidenceRecord]
