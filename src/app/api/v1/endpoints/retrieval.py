"""Retrieval endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_authenticated_user_id
from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.retrieval.schemas import RetrievalQuery, RetrievalResult
from app.retrieval.service import RetrievalService

router = APIRouter()


def get_retrieval_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RetrievalService:
    """Return a retrieval service configured from application settings."""

    return RetrievalService(
        default_top_k=settings.retrieval_default_top_k,
        max_top_k=settings.retrieval_max_top_k,
        candidate_overfetch=settings.retrieval_candidate_overfetch,
        default_token_budget=settings.retrieval_default_token_budget,
    )


@router.post(
    "/query",
    response_model=RetrievalResult,
    summary="Retrieve evidence",
    description="Search indexed post content for the authenticated user only.",
    operation_id="retrieveEvidence",
)
def retrieve_evidence(
    payload: RetrievalQuery,
    session: Annotated[Session, Depends(get_db_session)],
    user_id: Annotated[UUID, Depends(get_authenticated_user_id)],
    service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> RetrievalResult:
    """Return ranked evidence for the authenticated user."""

    return service.retrieve(
        session,
        user_id=user_id,
        query_text=payload.query,
        top_k=payload.top_k,
        token_budget=payload.token_budget,
    )
