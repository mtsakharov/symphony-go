"""Integration tests for chat endpoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient

from app.chat.exceptions import ChatUpstreamError, SessionAccessError
from app.chat.schemas import ChatQuestionResponse, ChatResponseStatus


class StubChatService:
    """Test double for the chat service."""

    def __init__(
        self,
        *,
        response: ChatQuestionResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def answer_question(
        self,
        *,
        user_id: str,
        question: str,
        session_id: str | None,
    ) -> ChatQuestionResponse:
        """Record the call and return the configured response."""

        self.calls.append(
            {
                "user_id": user_id,
                "question": question,
                "session_id": session_id,
            }
        )
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


@pytest.mark.asyncio
async def test_answer_question_returns_normalized_payload(
    client: AsyncClient,
    override_chat_dependencies: Callable[[Any, str], None],
) -> None:
    """Authenticated callers should receive answer text, citations, and status."""

    service = StubChatService(
        response=ChatQuestionResponse(
            answer_text="The release post confirms the rollout.",
            citations=[
                {
                    "post_id": "post-42",
                    "title": "Release notes",
                    "url": "https://example.com/posts/42",
                    "snippet": "Rollout begins today.",
                    "source": "posts",
                }
            ],
            status=ChatResponseStatus.ANSWERED,
        )
    )
    override_chat_dependencies(service, "user-123")

    response = await client.post(
        "/api/v1/chat/qa",
        json={"question": "What changed?", "session_id": "thread-1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer_text": "The release post confirms the rollout.",
        "citations": [
            {
                "post_id": "post-42",
                "title": "Release notes",
                "url": "https://example.com/posts/42",
                "snippet": "Rollout begins today.",
                "source": "posts",
            }
        ],
        "status": "answered",
    }
    assert service.calls == [
        {
            "user_id": "user-123",
            "question": "What changed?",
            "session_id": "thread-1",
        }
    ]


@pytest.mark.asyncio
async def test_answer_question_rejects_unauthenticated_requests(client: AsyncClient) -> None:
    """Missing credentials should return a stable 401 response."""

    response = await client.post("/api/v1/chat/qa", json={"question": "What changed?"})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "detail": {
            "code": "unauthorized",
            "message": "Authentication required",
        }
    }


@pytest.mark.asyncio
async def test_answer_question_returns_insufficient_evidence_status(
    client: AsyncClient,
    override_chat_dependencies: Callable[[Any, str], None],
) -> None:
    """Insufficient evidence should be explicit in the API response."""

    service = StubChatService(
        response=ChatQuestionResponse(
            answer_text=None,
            citations=[],
            status=ChatResponseStatus.INSUFFICIENT_EVIDENCE,
        )
    )
    override_chat_dependencies(service, "user-123")

    response = await client.post("/api/v1/chat/qa", json={"question": "What changed?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer_text": None,
        "citations": [],
        "status": "insufficient_evidence",
    }


@pytest.mark.asyncio
async def test_answer_question_returns_empty_state_status(
    client: AsyncClient,
    override_chat_dependencies: Callable[[Any, str], None],
) -> None:
    """No available post context should map to the empty-state status."""

    service = StubChatService(
        response=ChatQuestionResponse(
            answer_text=None,
            citations=[],
            status=ChatResponseStatus.EMPTY_STATE,
        )
    )
    override_chat_dependencies(service, "user-123")

    response = await client.post("/api/v1/chat/qa", json={"question": "What changed?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer_text": None,
        "citations": [],
        "status": "empty_state",
    }


@pytest.mark.asyncio
async def test_answer_question_maps_upstream_failures_to_stable_api_errors(
    client: AsyncClient,
    override_chat_dependencies: Callable[[Any, str], None],
) -> None:
    """Upstream model or retrieval failures should not leak provider details."""

    service = StubChatService(error=ChatUpstreamError("provider timeout"))
    override_chat_dependencies(service, "user-123")

    response = await client.post("/api/v1/chat/qa", json={"question": "What changed?"})

    assert response.status_code == 502
    assert response.json() == {
        "detail": {
            "code": "chat_upstream_failure",
            "message": "Chat answer service is unavailable.",
        }
    }


@pytest.mark.asyncio
async def test_answer_question_rejects_cross_user_session_access(
    client: AsyncClient,
    override_chat_dependencies: Callable[[Any, str], None],
) -> None:
    """Authenticated callers must not access a different user's session."""

    service = StubChatService(
        error=SessionAccessError("Session does not belong to the authenticated user")
    )
    override_chat_dependencies(service, "user-123")

    response = await client.post(
        "/api/v1/chat/qa",
        json={"question": "What changed?", "session_id": "other-user:thread-1"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": {
            "code": "chat_session_forbidden",
            "message": "Session does not belong to the authenticated user",
        }
    }
