"""Integration tests for grounded answer endpoints."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI
from httpx import AsyncClient

from app.answers.contracts import ModelMessage, RetrievedPost
from app.answers.flow import AnswerFlowSettings
from app.answers.service import AnswerService
from app.api.v1.endpoints.answers import (
    get_answer_model,
    get_answer_retriever,
    get_answer_service,
)


class FakeRetriever:
    """Return fixed retrieved posts for answer tests."""

    def __init__(self, posts: list[RetrievedPost]) -> None:
        self.posts = posts

    def retrieve(self, *, user_id: str, question: str) -> list[RetrievedPost]:
        return self.posts


class FakeAnswerModel:
    """Return a fixed answer for endpoint tests."""

    def __init__(self, answer: str) -> None:
        self.answer = answer

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        return self.answer


async def test_answer_question_returns_grounded_answer_with_citations(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """Supported evidence should return an answer and citations."""

    app.dependency_overrides[get_answer_service] = lambda: AnswerService(
        flow_settings=AnswerFlowSettings(min_post_score=0.2)
    )
    app.dependency_overrides[get_answer_retriever] = lambda: FakeRetriever(
        [
            RetrievedPost(
                post_id="post-123",
                text="The answer flow uses LangGraph to orchestrate retrieval and evidence gating.",
                permalink="https://example.com/posts/123",
                score=0.91,
            )
        ]
    )
    app.dependency_overrides[get_answer_model] = lambda: FakeAnswerModel(
        "The answer flow uses LangGraph for orchestration. [post-123]"
    )

    response = await client.post(
        "/api/v1/answers",
        json={"user_id": "user-1", "question": "How does the answer flow work?"},
    )

    assert response.status_code == 200
    assert response.json()["is_fallback"] is False
    assert response.json()["citations"][0]["post_id"] == "post-123"
    app.dependency_overrides.clear()


async def test_answer_question_returns_fallback_for_weak_evidence(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """Weak evidence should skip model generation and return the fallback."""

    app.dependency_overrides[get_answer_service] = lambda: AnswerService(
        flow_settings=AnswerFlowSettings(min_post_score=0.5)
    )
    app.dependency_overrides[get_answer_retriever] = lambda: FakeRetriever(
        [RetrievedPost(post_id="post-weak", text="Short note only.", score=0.1)]
    )
    app.dependency_overrides[get_answer_model] = lambda: FakeAnswerModel(
        "This should never be returned."
    )

    response = await client.post(
        "/api/v1/answers",
        json={"user_id": "user-1", "question": "What is my posting strategy?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Not enough information from your posts to answer that.",
        "is_fallback": True,
        "citations": [],
    }
    app.dependency_overrides.clear()
