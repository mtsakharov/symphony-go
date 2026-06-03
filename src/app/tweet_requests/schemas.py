"""Pydantic schemas for tweet request endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.tweet_requests.models import TweetRequestStatus


class TweetRequestWriteBase(BaseModel):
    """Shared write payload fields for tweet requests."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    brief: str | None = Field(default=None, max_length=2_000)
    target_audience: str | None = Field(default=None, max_length=255)
    objective: str | None = Field(default=None, max_length=255)
    tone: str | None = Field(default=None, max_length=100)
    call_to_action: str | None = Field(default=None, max_length=255)
    reviewer_notes: str | None = Field(default=None, max_length=2_000)
    approved_by_compliance: bool | None = None
    approved_by_reviewer: bool | None = None

    @model_validator(mode="after")
    def normalize_blank_strings(self) -> Self:
        """Convert blank strings to null so readiness checks stay deterministic."""

        for field_name in (
            "brief",
            "target_audience",
            "objective",
            "tone",
            "call_to_action",
            "reviewer_notes",
        ):
            value = getattr(self, field_name)
            if value == "":
                setattr(self, field_name, None)
        return self


class TweetRequestCreate(TweetRequestWriteBase):
    """Payload for creating a tweet request draft."""


class TweetRequestUpdate(TweetRequestWriteBase):
    """Payload for incrementally updating a tweet request draft."""


class MissingReadinessField(BaseModel):
    """Structured description of a missing readiness field."""

    field: str
    message: str


class ReadinessBlocker(BaseModel):
    """Structured description of a non-field readiness blocker."""

    code: str
    message: str


class TweetRequestValidation(BaseModel):
    """Derived validation output returned alongside a tweet request."""

    is_ready: bool
    missing_fields: list[MissingReadinessField]
    blockers: list[ReadinessBlocker]


class TweetRequestStatusEvaluationResponse(BaseModel):
    """Derived status payload returned by the status evaluation endpoint."""

    id: UUID
    status: TweetRequestStatus
    validation: TweetRequestValidation


class TweetRequestResponse(BaseModel):
    """Serialized tweet request returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brief: str | None
    target_audience: str | None
    objective: str | None
    tone: str | None
    call_to_action: str | None
    reviewer_notes: str | None
    approved_by_compliance: bool | None
    approved_by_reviewer: bool | None
    status: TweetRequestStatus
    validation: TweetRequestValidation
    created_at: datetime
    updated_at: datetime
