"""Service layer for the thin posts chat integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.chat.client import PostsChatClient
from app.chat.exceptions import ChatUpstreamError
from app.chat.schemas import ChatState, Citation, PostsChatRequest, PostsChatResponse

_NO_POSTS_MARKERS = (
    "no posts",
    "no post",
    "don't have any posts",
    "do not have any posts",
    "haven't posted",
    "have not posted",
)
_INSUFFICIENT_EVIDENCE_MARKERS = (
    "not enough information from your posts",
    "not enough information in your posts",
    "insufficient evidence",
    "insufficient information",
)


class ChatService:
    """Orchestrate calls to the upstream posts chat API."""

    def __init__(self, client: PostsChatClient) -> None:
        self._client = client

    async def ask_about_posts(
        self,
        payload: PostsChatRequest,
        *,
        forwarded_headers: Mapping[str, str],
    ) -> PostsChatResponse:
        """Submit a posts question and normalize the upstream result."""

        response = await self._client.ask_posts_question(
            question=payload.question,
            session_id=payload.session_id,
            forwarded_headers=forwarded_headers,
        )
        return self._normalize_response(response)

    def _normalize_response(self, response: Mapping[str, Any]) -> PostsChatResponse:
        """Map the upstream response to the thin UI contract."""

        answer = self._extract_answer(response)
        citations = self._extract_citations(response)
        state = self._infer_state(response, answer=answer, citations=citations)
        session_id = self._extract_session_id(response)

        if state is ChatState.ANSWERED and not citations:
            raise ChatUpstreamError("Answered responses must include at least one citation")

        normalized_answer = answer or _default_answer_for_state(state)
        return PostsChatResponse(
            answer=normalized_answer,
            state=state,
            session_id=session_id,
            citations=citations,
        )

    def _extract_answer(self, response: Mapping[str, Any]) -> str:
        """Return the answer text from the upstream payload."""

        for key in ("answer", "response", "message", "content"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _extract_session_id(self, response: Mapping[str, Any]) -> str | None:
        """Return the upstream session id when present."""

        for key in ("session_id", "sessionId", "conversation_id", "conversationId"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _infer_state(
        self,
        response: Mapping[str, Any],
        *,
        answer: str,
        citations: list[Citation],
    ) -> ChatState:
        """Infer the normalized UI state."""

        raw_state = self._normalized_state_value(response)
        if raw_state in {"answered", "answer", "grounded", "groundedanswer"}:
            return ChatState.ANSWERED
        if raw_state in {"noposts", "emptystate", "empty", "nopostsfound"}:
            return ChatState.NO_POSTS
        if raw_state in {
            "insufficientevidence",
            "notenoughinformation",
            "notenoughinformationfromyourposts",
        }:
            return ChatState.INSUFFICIENT_EVIDENCE

        answer_lower = answer.lower()
        if any(marker in answer_lower for marker in _NO_POSTS_MARKERS):
            return ChatState.NO_POSTS
        if any(marker in answer_lower for marker in _INSUFFICIENT_EVIDENCE_MARKERS):
            return ChatState.INSUFFICIENT_EVIDENCE
        if citations or answer:
            return ChatState.ANSWERED
        raise ChatUpstreamError("Chat API returned an empty response")

    def _normalized_state_value(self, response: Mapping[str, Any]) -> str:
        """Return a normalized upstream state/status value."""

        for key in ("state", "status", "outcome", "type"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return "".join(char for char in value.lower() if char.isalnum())
        return ""

    def _extract_citations(self, response: Mapping[str, Any]) -> list[Citation]:
        """Return visible citations from the upstream payload."""

        raw_citations = response.get(
            "citations",
            response.get("sources", response.get("references")),
        )
        if not isinstance(raw_citations, list):
            return []

        citations: list[Citation] = []
        for item in raw_citations:
            if not isinstance(item, dict):
                continue

            title = self._first_string(item, "title", "post_title", "label", "name")
            if title is None:
                continue

            citations.append(
                Citation(
                    title=title,
                    url=self._first_string(item, "url", "href", "permalink"),
                    excerpt=self._first_string(item, "excerpt", "snippet", "quote"),
                    post_id=self._first_string(item, "post_id", "postId", "id"),
                )
            )

        return citations

    def _first_string(self, payload: Mapping[str, Any], *keys: str) -> str | None:
        """Return the first non-empty string value for the requested keys."""

        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None


def _default_answer_for_state(state: ChatState) -> str:
    """Return fallback copy for non-answer states."""

    if state is ChatState.NO_POSTS:
        return "You do not have any posts yet, so there is nothing to cite."
    if state is ChatState.INSUFFICIENT_EVIDENCE:
        return "There is not enough information from your posts to answer that yet."
    raise ChatUpstreamError("Answered responses must include answer text")
