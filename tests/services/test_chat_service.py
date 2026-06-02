"""Unit tests for the chat service."""

from __future__ import annotations

from typing import Any, cast

import pytest

from app.chat.client import PostsChatClient
from app.chat.exceptions import ChatUpstreamError
from app.chat.schemas import ChatState, PostsChatRequest
from app.chat.service import ChatService


class StubPostsChatClient:
    """Test double for the upstream posts chat client."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    async def ask_posts_question(
        self,
        *,
        question: str,
        session_id: str | None,
        forwarded_headers: dict[str, str],
    ) -> dict[str, Any]:
        """Record the request and return the configured payload."""

        self.calls.append(
            {
                "question": question,
                "session_id": session_id,
                "forwarded_headers": forwarded_headers,
            }
        )
        return self.payload


@pytest.mark.asyncio
async def test_ask_about_posts_normalizes_grounded_answer() -> None:
    """Grounded responses should preserve answer text, citations, and session ids."""

    client = StubPostsChatClient(
        {
            "answer": "You mostly write about release notes and migration work.",
            "session_id": "session-2",
            "citations": [
                {
                    "title": "Release notes recap",
                    "url": "https://example.com/posts/1",
                    "excerpt": "I wrapped up the migration checklist.",
                    "post_id": "1",
                }
            ],
        }
    )
    service = ChatService(client=cast(PostsChatClient, client))

    response = await service.ask_about_posts(
        PostsChatRequest(question="What do I write about?", session_id="session-1"),
        forwarded_headers={"authorization": "Bearer user-token"},
    )

    assert response.state is ChatState.ANSWERED
    assert response.answer == "You mostly write about release notes and migration work."
    assert response.session_id == "session-2"
    assert response.citations[0].title == "Release notes recap"
    assert client.calls == [
        {
            "question": "What do I write about?",
            "session_id": "session-1",
            "forwarded_headers": {"authorization": "Bearer user-token"},
        }
    ]


@pytest.mark.asyncio
async def test_ask_about_posts_maps_no_posts_state() -> None:
    """Empty-corpus responses should normalize to the no-posts UI state."""

    client = StubPostsChatClient(
        {
            "state": "no_posts",
            "answer": "You do not have any posts yet, so there is nothing to cite.",
            "session_id": "session-3",
        }
    )
    service = ChatService(client=cast(PostsChatClient, client))

    response = await service.ask_about_posts(
        PostsChatRequest(question="What have I posted?"),
        forwarded_headers={},
    )

    assert response.state is ChatState.NO_POSTS
    assert response.answer == "You do not have any posts yet, so there is nothing to cite."
    assert response.citations == []


@pytest.mark.asyncio
async def test_ask_about_posts_maps_insufficient_evidence_from_fallback_text() -> None:
    """Insufficient-evidence copy should stay distinct from no-posts state."""

    client = StubPostsChatClient(
        {
            "answer": "There is not enough information from your posts to answer that yet.",
            "session_id": "session-4",
        }
    )
    service = ChatService(client=cast(PostsChatClient, client))

    response = await service.ask_about_posts(
        PostsChatRequest(question="Which city did I move to?"),
        forwarded_headers={},
    )

    assert response.state is ChatState.INSUFFICIENT_EVIDENCE
    assert response.answer == "There is not enough information from your posts to answer that yet."


@pytest.mark.asyncio
async def test_ask_about_posts_rejects_answer_without_citation() -> None:
    """Answered responses without visible citations should fail fast."""

    client = StubPostsChatClient(
        {
            "state": "answered",
            "answer": "You post about migrations.",
            "session_id": "session-5",
        }
    )
    service = ChatService(client=cast(PostsChatClient, client))

    with pytest.raises(
        ChatUpstreamError,
        match="Answered responses must include at least one citation",
    ):
        await service.ask_about_posts(
            PostsChatRequest(question="What do I post about?"),
            forwarded_headers={},
        )
