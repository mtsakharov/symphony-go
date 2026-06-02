"""Integration tests for the posts chat API."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.v1.endpoints.chat import get_chat_service
from app.chat.schemas import ChatState, Citation, PostsChatRequest, PostsChatResponse
from app.chat.service import ChatService


class StubChatService:
    """Test double for the posts chat service dependency."""

    def __init__(self, responses: list[PostsChatResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def ask_about_posts(
        self,
        payload: PostsChatRequest,
        *,
        forwarded_headers: dict[str, str],
    ) -> PostsChatResponse:
        """Return the next configured response and record the request."""

        self.calls.append(
            {
                "payload": payload,
                "forwarded_headers": forwarded_headers,
            }
        )
        return self.responses.pop(0)


def override_chat_service(
    app: FastAPI,
    stub_service: StubChatService,
) -> None:
    """Install a dependency override for the chat service."""

    app.dependency_overrides[get_chat_service] = lambda: cast(ChatService, stub_service)


@pytest.fixture(autouse=True)
def clear_chat_service_override(app: FastAPI) -> Iterator[None]:
    """Remove the chat service override after each test."""

    yield
    app.dependency_overrides.pop(get_chat_service, None)


@pytest.mark.asyncio
async def test_ask_posts_question_returns_grounded_answer_with_citations(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """Supported answers should include answer text, state, session id, and citations."""

    stub_service = StubChatService(
        [
            PostsChatResponse(
                answer="You write about release work.",
                state=ChatState.ANSWERED,
                session_id="session-10",
                citations=[
                    Citation(
                        title="Release recap",
                        url="https://example.com/posts/release",
                        excerpt="We shipped the migration.",
                    )
                ],
            )
        ]
    )
    override_chat_service(app, stub_service)

    response = await client.post(
        "/api/v1/chat/posts",
        headers={"authorization": "Bearer member-token", "cookie": "session=abc"},
        json={"question": "What do I write about?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "You write about release work.",
        "state": "answered",
        "session_id": "session-10",
        "citations": [
            {
                "title": "Release recap",
                "url": "https://example.com/posts/release",
                "excerpt": "We shipped the migration.",
                "post_id": None,
            }
        ],
    }
    assert stub_service.calls[0]["payload"].question == "What do I write about?"
    assert stub_service.calls[0]["forwarded_headers"] == {
        "authorization": "Bearer member-token",
        "cookie": "session=abc",
    }


@pytest.mark.asyncio
async def test_ask_posts_question_returns_no_posts_state(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """No-posts responses should remain distinct in the client contract."""

    stub_service = StubChatService(
        [
            PostsChatResponse(
                answer="You do not have any posts yet, so there is nothing to cite.",
                state=ChatState.NO_POSTS,
                session_id="session-11",
            )
        ]
    )
    override_chat_service(app, stub_service)

    response = await client.post(
        "/api/v1/chat/posts",
        json={"question": "What have I posted recently?"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "no_posts"


@pytest.mark.asyncio
async def test_ask_posts_question_returns_insufficient_evidence_state(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """Insufficient-evidence responses should remain distinct in the client contract."""

    stub_service = StubChatService(
        [
            PostsChatResponse(
                answer="There is not enough information from your posts to answer that yet.",
                state=ChatState.INSUFFICIENT_EVIDENCE,
                session_id="session-12",
            )
        ]
    )
    override_chat_service(app, stub_service)

    response = await client.post(
        "/api/v1/chat/posts",
        json={"question": "Which city did I move to?"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "insufficient_evidence"


@pytest.mark.asyncio
async def test_ask_posts_question_forwards_session_id_on_follow_up(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """Follow-up turns should forward the current session id and return the latest one."""

    stub_service = StubChatService(
        [
            PostsChatResponse(
                answer="Your latest posts focus on migrations.",
                state=ChatState.ANSWERED,
                session_id="session-22",
                citations=[
                    Citation(title="Migration diary")
                ],
            )
        ]
    )
    override_chat_service(app, stub_service)

    response = await client.post(
        "/api/v1/chat/posts",
        json={
            "question": "And what about my last post?",
            "session_id": "session-21",
        },
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == "session-22"
    assert stub_service.calls[0]["payload"].session_id == "session-21"
