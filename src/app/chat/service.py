"""Service layer for post-grounded chat questions."""

from __future__ import annotations

from typing import Any, Protocol

from app.chat.exceptions import MalformedUpstreamResponseError, SessionAccessError
from app.chat.schemas import ChatCitation, ChatQuestionResponse, ChatResponseStatus

STATUS_ALIASES = {
    "answer": ChatResponseStatus.ANSWERED,
    "answered": ChatResponseStatus.ANSWERED,
    "ok": ChatResponseStatus.ANSWERED,
    "success": ChatResponseStatus.ANSWERED,
    "empty": ChatResponseStatus.EMPTY_STATE,
    "empty_state": ChatResponseStatus.EMPTY_STATE,
    "no_context": ChatResponseStatus.EMPTY_STATE,
    "no_data": ChatResponseStatus.EMPTY_STATE,
    "no_documents": ChatResponseStatus.EMPTY_STATE,
    "no_posts": ChatResponseStatus.EMPTY_STATE,
    "insufficient-context": ChatResponseStatus.INSUFFICIENT_EVIDENCE,
    "insufficient_context": ChatResponseStatus.INSUFFICIENT_EVIDENCE,
    "insufficient_evidence": ChatResponseStatus.INSUFFICIENT_EVIDENCE,
    "needs_more_context": ChatResponseStatus.INSUFFICIENT_EVIDENCE,
    "no_answer": ChatResponseStatus.INSUFFICIENT_EVIDENCE,
}


class LangGraphAnswerClient(Protocol):
    """Protocol implemented by LangGraph client adapters."""

    async def answer_question(
        self,
        *,
        user_id: str,
        question: str,
        session_id: str | None,
    ) -> dict[str, Any]:
        """Submit a question to the LangGraph answer flow."""


class ChatService:
    """Normalize LangGraph answers into the public API contract."""

    def __init__(self, client: LangGraphAnswerClient) -> None:
        self.client = client

    async def answer_question(
        self,
        *,
        user_id: str,
        question: str,
        session_id: str | None,
    ) -> ChatQuestionResponse:
        """Return a normalized answer for the authenticated user."""

        scoped_session_id = _scope_session_id(user_id, session_id)
        payload = await self.client.answer_question(
            user_id=user_id,
            question=question,
            session_id=scoped_session_id,
        )
        return _normalize_payload(payload)


def _scope_session_id(user_id: str, session_id: str | None) -> str | None:
    """Scope a client-provided session id to the current user."""

    if session_id is None:
        return None

    normalized_session_id = session_id.strip()
    if ":" in normalized_session_id:
        session_owner, raw_session_id = normalized_session_id.split(":", 1)
        if session_owner != user_id or not raw_session_id:
            raise SessionAccessError("Session does not belong to the authenticated user")
        normalized_session_id = raw_session_id

    return f"{user_id}:{normalized_session_id}"


def _normalize_payload(payload: dict[str, Any]) -> ChatQuestionResponse:
    """Normalize a raw LangGraph payload into the API response schema."""

    answer_text = _extract_answer_text(payload)
    citations = _extract_citations(payload)
    status = _extract_status(payload, answer_text=answer_text, citations=citations)

    if status is ChatResponseStatus.ANSWERED and answer_text is None:
        raise MalformedUpstreamResponseError("Answered responses must include answer text")

    if status is not ChatResponseStatus.ANSWERED:
        answer_text = answer_text or None

    return ChatQuestionResponse(
        answer_text=answer_text,
        citations=citations,
        status=status,
    )


def _extract_answer_text(payload: dict[str, Any]) -> str | None:
    """Return the first non-empty answer-like field from the payload."""

    for key in ("answer_text", "answer", "response"):
        candidate = payload.get(key)
        if isinstance(candidate, str):
            normalized = candidate.strip()
            if normalized:
                return normalized
    return None


def _extract_status(
    payload: dict[str, Any],
    *,
    answer_text: str | None,
    citations: list[ChatCitation],
) -> ChatResponseStatus:
    """Infer the public response status from the upstream payload."""

    raw_status = payload.get("status")
    if isinstance(raw_status, str):
        mapped_status = STATUS_ALIASES.get(raw_status.strip().lower())
        if mapped_status is not None:
            return mapped_status

    if payload.get("empty_state") is True or payload.get("has_posts") is False:
        return ChatResponseStatus.EMPTY_STATE

    if payload.get("insufficient_evidence") is True or payload.get("fallback") is True:
        return ChatResponseStatus.INSUFFICIENT_EVIDENCE

    if answer_text is not None:
        return ChatResponseStatus.ANSWERED

    if citations:
        return ChatResponseStatus.INSUFFICIENT_EVIDENCE

    return ChatResponseStatus.EMPTY_STATE


def _extract_citations(payload: dict[str, Any]) -> list[ChatCitation]:
    """Normalize stable citation metadata from common upstream fields."""

    citation_candidates = payload.get("citations")
    if not isinstance(citation_candidates, list):
        citation_candidates = payload.get("posts")
    if not isinstance(citation_candidates, list):
        citation_candidates = payload.get("sources")
    if not isinstance(citation_candidates, list):
        return []

    citations: list[ChatCitation] = []
    for item in citation_candidates:
        citation = _normalize_citation(item)
        if citation is not None:
            citations.append(citation)
    return citations


def _normalize_citation(item: Any) -> ChatCitation | None:
    """Normalize a citation item and drop records without a stable post id."""

    if not isinstance(item, dict):
        return None

    nested_post = item.get("post")
    if not isinstance(nested_post, dict):
        nested_post = {}

    post_id = item.get("post_id") or item.get("id") or nested_post.get("id")
    if post_id is None:
        return None

    return ChatCitation(
        post_id=str(post_id),
        title=_string_or_none(
            item.get("title") or item.get("post_title") or nested_post.get("title")
        ),
        url=_string_or_none(item.get("url") or nested_post.get("url")),
        snippet=_string_or_none(item.get("snippet") or item.get("excerpt") or item.get("quote")),
        source=_string_or_none(item.get("source") or item.get("site_name")),
    )


def _string_or_none(value: Any) -> str | None:
    """Return a normalized string value if present."""

    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return None
