"""Grounded answer endpoints."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.answers.contracts import (
    AnswerChatModel,
    AnswerRetriever,
    ModelMessage,
    RetrievedPost,
)
from app.answers.exceptions import AnswerDependencyNotConfiguredError
from app.answers.flow import AnswerFlowSettings
from app.answers.schemas import AnswerRequest, AnswerResponse
from app.answers.service import AnswerService
from app.core.config import Settings, get_settings

router = APIRouter()


class UnconfiguredAnswerRetriever:
    """Placeholder retriever used until the real integration is wired."""

    def retrieve(self, *, user_id: str, question: str) -> Sequence[RetrievedPost]:
        raise AnswerDependencyNotConfiguredError("Answer retriever is not configured")


class UnconfiguredAnswerModel:
    """Placeholder model adapter used until the real integration is wired."""

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        raise AnswerDependencyNotConfiguredError("Answer model is not configured")


def get_answer_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnswerService:
    """Return an answer service configured from shared settings."""

    return AnswerService(flow_settings=AnswerFlowSettings.from_settings(settings))


def get_answer_retriever() -> AnswerRetriever:
    """Return the configured answer retriever."""

    return UnconfiguredAnswerRetriever()


def get_answer_model() -> AnswerChatModel:
    """Return the configured answer model adapter."""

    return UnconfiguredAnswerModel()


@router.post(
    "",
    response_model=AnswerResponse,
    summary="Answer a question from retrieved posts",
    description=(
        "Retrieve user-scoped post evidence, gate unsupported questions, and return a "
        "grounded answer with citation-ready references."
    ),
    operation_id="answerQuestion",
)
def answer_question(
    payload: AnswerRequest,
    service: Annotated[AnswerService, Depends(get_answer_service)],
    retriever: Annotated[AnswerRetriever, Depends(get_answer_retriever)],
    model: Annotated[AnswerChatModel, Depends(get_answer_model)],
) -> AnswerResponse:
    """Answer a question using grounded post evidence."""

    try:
        return service.answer_question(
            user_id=payload.user_id,
            question=payload.question,
            retriever=retriever,
            model=model,
        )
    except AnswerDependencyNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
