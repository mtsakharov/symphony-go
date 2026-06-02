"""Chat endpoints."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, status

from app.chat.schemas import ChatRequest, ChatResponse
from app.chat.service import (
    ChatResponder,
    ChatService,
    GroundedTemplateResponder,
    NullPostRetriever,
    PostRetriever,
)
from app.chat.session_store import InMemorySessionContextStore

router = APIRouter()


def get_session_context_store(request: Request) -> InMemorySessionContextStore:
    """Return the process-local session store from application state."""

    return cast(InMemorySessionContextStore, request.app.state.session_context_store)


def get_post_retriever() -> PostRetriever:
    """Return the active post retriever implementation."""

    return NullPostRetriever()


def get_chat_responder() -> ChatResponder:
    """Return the active chat responder implementation."""

    return GroundedTemplateResponder()


def get_chat_service(
    session_store: Annotated[InMemorySessionContextStore, Depends(get_session_context_store)],
    retriever: Annotated[PostRetriever, Depends(get_post_retriever)],
    responder: Annotated[ChatResponder, Depends(get_chat_responder)],
) -> ChatService:
    """Return a chat service instance."""

    return ChatService(
        retriever=retriever,
        responder=responder,
        session_store=session_store,
    )


@router.post(
    "/respond",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate grounded chat response",
    description=(
        "Answer a user message using fresh retrieval over indexed posts plus a bounded "
        "window of recent turns for the provided session."
    ),
    operation_id="respondToChatMessage",
)
def respond_to_chat_message(
    payload: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """Return a grounded answer for the incoming chat turn."""

    return service.answer(payload)
