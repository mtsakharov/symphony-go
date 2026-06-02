"""Thin posts chat API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.chat.client import PostsChatClient
from app.chat.exceptions import ChatError
from app.chat.schemas import PostsChatRequest, PostsChatResponse
from app.chat.service import ChatService
from app.core.config import Settings, get_settings

router = APIRouter()


def get_chat_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatService:
    """Return the posts chat service."""

    return ChatService(client=PostsChatClient.from_settings(settings))


@router.post(
    "/posts",
    response_model=PostsChatResponse,
    summary="Ask about the signed-in user's posts",
    description=(
        "Proxy a posts question to the upstream chat API and normalize the "
        "response into explicit UI states plus visible citations."
    ),
    operation_id="askPostsQuestion",
)
async def ask_posts_question(
    payload: PostsChatRequest,
    request: Request,
    service: Annotated[ChatService, Depends(get_chat_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PostsChatResponse:
    """Submit a posts question and return the normalized result."""

    try:
        return await service.ask_about_posts(
            payload,
            forwarded_headers=_build_forward_headers(request, settings),
        )
    except ChatError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def _build_forward_headers(request: Request, settings: Settings) -> dict[str, str]:
    """Return inbound auth/context headers to forward upstream."""

    headers: dict[str, str] = {}
    for name in _parse_forward_headers(settings.chat_api_forward_headers):
        value = request.headers.get(name)
        if value:
            headers[name] = value
    return headers


def _parse_forward_headers(raw_value: str) -> list[str]:
    """Return configured header names as lowercase strings."""

    return [item.strip().lower() for item in raw_value.split(",") if item.strip()]
