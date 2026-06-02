"""Authenticated chat endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.chat.client import LangGraphClient
from app.chat.exceptions import (
    ChatUpstreamError,
    MalformedUpstreamResponseError,
    SessionAccessError,
)
from app.chat.schemas import ChatQuestionRequest, ChatQuestionResponse, ErrorResponse
from app.chat.service import ChatService
from app.core.config import Settings, get_settings

router = APIRouter()


def get_chat_service(settings: Annotated[Settings, Depends(get_settings)]) -> ChatService:
    """Return a chat service instance."""

    client = LangGraphClient(
        api_url=settings.langgraph_api_url,
        timeout_seconds=settings.langgraph_timeout_seconds,
        bearer_token=settings.langgraph_bearer_token,
    )
    return ChatService(client)


@router.post(
    "/qa",
    response_model=ChatQuestionResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Authentication is required to query the chat API.",
        },
        403: {
            "model": ErrorResponse,
            "description": "The supplied session does not belong to the authenticated user.",
        },
        502: {
            "model": ErrorResponse,
            "description": "The LangGraph answer flow failed upstream.",
        },
    },
    summary="Answer a post-grounded question",
    description=(
        "Accept a user question and optional session id, invoke the LangGraph answer flow, "
        "and return normalized answer text plus citation metadata."
    ),
    operation_id="answerPostGroundedQuestion",
)
async def answer_question(
    payload: ChatQuestionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatQuestionResponse:
    """Answer a post-grounded question for the authenticated user."""

    try:
        return await service.answer_question(
            user_id=current_user.user_id,
            question=payload.question,
            session_id=payload.session_id,
        )
    except SessionAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_error_detail("chat_session_forbidden", str(exc)),
        ) from exc
    except MalformedUpstreamResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_error_detail(
                "chat_upstream_invalid_response",
                "Chat answer service returned an invalid response.",
            ),
        ) from exc
    except ChatUpstreamError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_error_detail(
                "chat_upstream_failure",
                "Chat answer service is unavailable.",
            ),
        ) from exc


def _error_detail(code: str, message: str) -> dict[str, Any]:
    """Return a structured API error payload."""

    return {"code": code, "message": message}
