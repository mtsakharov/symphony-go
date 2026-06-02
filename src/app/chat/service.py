"""Chat service orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.chat.models import ConversationTurn, RetrievedPost
from app.chat.schemas import ChatRequest, ChatResponse, PostEvidence
from app.chat.session_store import InMemorySessionContextStore


@dataclass(frozen=True, slots=True)
class ChatPrompt:
    """Prompt payload passed to the chat responder."""

    user_id: UUID
    session_id: str
    question: str
    prior_turns: list[ConversationTurn]
    retrieved_posts: list[RetrievedPost]


class PostRetriever(Protocol):
    """Retrieve current post evidence for a user and query."""

    def retrieve_posts(self, *, user_id: UUID, query: str) -> Sequence[RetrievedPost]:
        """Return fresh post evidence for the current turn."""


class ChatResponder(Protocol):
    """Generate an answer from the assembled prompt."""

    def generate_reply(self, prompt: ChatPrompt) -> str:
        """Return the assistant reply for the given prompt."""


class NullPostRetriever:
    """Fallback retriever used when no real index integration is configured."""

    def retrieve_posts(self, *, user_id: UUID, query: str) -> Sequence[RetrievedPost]:
        """Return no evidence while preserving the retrieval contract."""

        return []


class GroundedTemplateResponder:
    """Deterministic fallback responder for local development and tests."""

    def generate_reply(self, prompt: ChatPrompt) -> str:
        """Generate a grounded reply from retrieved evidence and recent context."""

        if prompt.retrieved_posts:
            evidence_preview = " ".join(post.content for post in prompt.retrieved_posts[:2])
            return (
                f"Grounded answer for '{prompt.question}' using current post evidence: "
                f"{evidence_preview}"
            )

        if prompt.prior_turns:
            return (
                f"No fresh post evidence matched '{prompt.question}'. "
                f"Retained {len(prompt.prior_turns)} recent turn(s) of context."
            )

        return f"No fresh post evidence matched '{prompt.question}'."


class ChatService:
    """Coordinate retrieval, prompt construction, and session retention."""

    def __init__(
        self,
        *,
        retriever: PostRetriever,
        responder: ChatResponder,
        session_store: InMemorySessionContextStore,
    ) -> None:
        self._retriever = retriever
        self._responder = responder
        self._session_store = session_store

    def answer(self, payload: ChatRequest) -> ChatResponse:
        """Answer a chat turn using fresh retrieval and bounded session context."""

        prior_turns = self._session_store.get_turns(payload.session_id)
        retrieved_posts = list(
            self._retriever.retrieve_posts(user_id=payload.user_id, query=payload.message)
        )
        prompt = ChatPrompt(
            user_id=payload.user_id,
            session_id=payload.session_id,
            question=payload.message,
            prior_turns=prior_turns,
            retrieved_posts=retrieved_posts,
        )
        answer = self._responder.generate_reply(prompt)
        self._session_store.append_turn(
            payload.session_id,
            ConversationTurn(user_message=payload.message, assistant_message=answer),
        )
        return ChatResponse(
            session_id=payload.session_id,
            answer=answer,
            evidence=[
                PostEvidence(post_id=post.post_id, content=post.content) for post in retrieved_posts
            ],
            history_turns_used=len(prior_turns),
        )
