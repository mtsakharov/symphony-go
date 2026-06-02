"""Integration tests for chat endpoints."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.v1.endpoints.chat import get_chat_responder, get_post_retriever
from app.chat.models import RetrievedPost
from app.chat.service import ChatPrompt


class RecordingRetriever:
    """Test retriever that records every query."""

    def __init__(self, responses: dict[str, list[RetrievedPost]]) -> None:
        self.responses = responses
        self.calls: list[tuple[UUID, str]] = []

    def retrieve_posts(self, *, user_id: UUID, query: str) -> Sequence[RetrievedPost]:
        """Return configured evidence for the query."""

        self.calls.append((user_id, query))
        return self.responses.get(query, [])


class RecordingResponder:
    """Test responder that records prompts."""

    def __init__(self) -> None:
        self.prompts: list[ChatPrompt] = []

    def generate_reply(self, prompt: ChatPrompt) -> str:
        """Return a deterministic answer for assertions."""

        self.prompts.append(prompt)
        return f"answer:{prompt.question}"


@pytest.fixture
def chat_overrides(app: FastAPI) -> tuple[RecordingRetriever, RecordingResponder]:
    """Install deterministic chat collaborators for API tests."""

    retriever = RecordingRetriever(
        {
            "First message": [RetrievedPost(post_id="post-1", content="first evidence")],
            "Follow up": [RetrievedPost(post_id="post-2", content="follow-up evidence")],
            "New session": [RetrievedPost(post_id="post-3", content="new session evidence")],
        }
    )
    responder = RecordingResponder()
    app.dependency_overrides[get_post_retriever] = lambda: retriever
    app.dependency_overrides[get_chat_responder] = lambda: responder
    return retriever, responder


@pytest.mark.asyncio
async def test_chat_follow_up_reuses_context_and_retrieves_again(
    client: AsyncClient,
    chat_overrides: tuple[RecordingRetriever, RecordingResponder],
) -> None:
    """Two requests with the same session id should reuse bounded context."""

    user_id = str(uuid4())
    retriever, responder = chat_overrides

    first_response = await client.post(
        "/api/v1/chat/respond",
        json={"user_id": user_id, "session_id": "session-a", "message": "First message"},
    )
    second_response = await client.post(
        "/api/v1/chat/respond",
        json={"user_id": user_id, "session_id": "session-a", "message": "Follow up"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["history_turns_used"] == 1
    assert second_response.json()["evidence"] == [
        {"post_id": "post-2", "content": "follow-up evidence"}
    ]
    assert retriever.calls == [(UUID(user_id), "First message"), (UUID(user_id), "Follow up")]
    assert responder.prompts[1].prior_turns[0].user_message == "First message"


@pytest.mark.asyncio
async def test_chat_new_session_is_isolated(
    client: AsyncClient,
    chat_overrides: tuple[RecordingRetriever, RecordingResponder],
) -> None:
    """Switching session ids should not leak prior context."""

    user_id = str(uuid4())
    _, responder = chat_overrides

    first_response = await client.post(
        "/api/v1/chat/respond",
        json={"user_id": user_id, "session_id": "session-a", "message": "First message"},
    )
    second_response = await client.post(
        "/api/v1/chat/respond",
        json={"user_id": user_id, "session_id": "session-b", "message": "New session"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["history_turns_used"] == 0
    assert responder.prompts[1].prior_turns == []
