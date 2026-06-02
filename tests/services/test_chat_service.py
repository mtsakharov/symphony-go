"""Unit tests for the chat service."""

from __future__ import annotations

from typing import Any

import pytest

from app.chat.exceptions import MalformedUpstreamResponseError, SessionAccessError
from app.chat.schemas import ChatResponseStatus
from app.chat.service import ChatService


class FakeLangGraphClient:
    """Configurable fake LangGraph client for service tests."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    async def answer_question(
        self,
        *,
        user_id: str,
        question: str,
        session_id: str | None,
    ) -> dict[str, Any]:
        """Record the call and return a canned payload."""

        self.calls.append(
            {
                "user_id": user_id,
                "question": question,
                "session_id": session_id,
            }
        )
        return self.payload


@pytest.mark.asyncio
async def test_answer_question_normalizes_answer_and_citations() -> None:
    """The service should normalize citations and scope session ids by user."""

    client = FakeLangGraphClient(
        {
            "answer": "The launch post confirms a staggered rollout.",
            "sources": [
                {
                    "id": "post-42",
                    "title": "Launch post",
                    "url": "https://example.com/posts/42",
                    "snippet": "Rolling out over the next 24 hours.",
                    "internal_score": 0.99,
                }
            ],
            "provider": "langgraph",
        }
    )
    service = ChatService(client)

    response = await service.answer_question(
        user_id="user-123",
        question="What changed?",
        session_id="thread-1",
    )

    assert client.calls == [
        {
            "user_id": "user-123",
            "question": "What changed?",
            "session_id": "user-123:thread-1",
        }
    ]
    assert response.answer_text == "The launch post confirms a staggered rollout."
    assert response.status is ChatResponseStatus.ANSWERED
    assert response.model_dump() == {
        "answer_text": "The launch post confirms a staggered rollout.",
        "citations": [
            {
                "post_id": "post-42",
                "title": "Launch post",
                "url": "https://example.com/posts/42",
                "snippet": "Rolling out over the next 24 hours.",
                "source": None,
            }
        ],
        "status": "answered",
    }


@pytest.mark.asyncio
async def test_answer_question_maps_insufficient_evidence() -> None:
    """Fallback-style upstream results should map to insufficient evidence."""

    client = FakeLangGraphClient(
        {
            "status": "no_answer",
            "fallback": True,
            "citations": [{"post_id": "post-42", "title": "Launch post"}],
        }
    )
    service = ChatService(client)

    response = await service.answer_question(
        user_id="user-123",
        question="What changed?",
        session_id=None,
    )

    assert response.answer_text is None
    assert response.status is ChatResponseStatus.INSUFFICIENT_EVIDENCE
    assert response.citations[0].post_id == "post-42"


@pytest.mark.asyncio
async def test_answer_question_maps_empty_state() -> None:
    """Missing context should map to the explicit empty-state status."""

    client = FakeLangGraphClient(
        {
            "empty_state": True,
            "posts": [],
        }
    )
    service = ChatService(client)

    response = await service.answer_question(
        user_id="user-123",
        question="What changed?",
        session_id=None,
    )

    assert response.answer_text is None
    assert response.citations == []
    assert response.status is ChatResponseStatus.EMPTY_STATE


@pytest.mark.asyncio
async def test_answer_question_rejects_cross_user_session_ids() -> None:
    """Namespaced session ids from another user should be rejected."""

    client = FakeLangGraphClient({"answer": "irrelevant"})
    service = ChatService(client)

    with pytest.raises(SessionAccessError, match="does not belong"):
        await service.answer_question(
            user_id="user-123",
            question="What changed?",
            session_id="user-999:thread-1",
        )


@pytest.mark.asyncio
async def test_answer_question_rejects_answered_payload_without_answer_text() -> None:
    """Malformed answered payloads should raise a stable domain exception."""

    client = FakeLangGraphClient(
        {
            "status": "answered",
            "citations": [{"post_id": "post-42", "title": "Launch post"}],
        }
    )
    service = ChatService(client)

    with pytest.raises(MalformedUpstreamResponseError, match="must include answer text"):
        await service.answer_question(
            user_id="user-123",
            question="What changed?",
            session_id=None,
        )
