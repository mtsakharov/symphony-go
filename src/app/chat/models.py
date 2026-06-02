"""Internal chat domain models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """A completed user and assistant exchange."""

    user_message: str
    assistant_message: str


@dataclass(frozen=True, slots=True)
class RetrievedPost:
    """A retrieved post snippet used as evidence for a chat turn."""

    post_id: str
    content: str
