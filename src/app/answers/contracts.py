"""Protocols and transport models for the answer flow."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(slots=True, frozen=True)
class ModelMessage:
    """A chat message passed to the model adapter."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(slots=True, frozen=True)
class RetrievedPost:
    """A single retrieved post used as grounding evidence."""

    post_id: str
    text: str
    permalink: str | None = None
    score: float | None = None


class AnswerRetriever(Protocol):
    """User-scoped retrieval boundary for grounded answering."""

    def retrieve(self, *, user_id: str, question: str) -> Sequence[RetrievedPost]:
        """Return posts relevant to the user's question."""


class AnswerChatModel(Protocol):
    """Model boundary for grounded answer generation."""

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        """Generate an answer from the assembled prompt messages."""
