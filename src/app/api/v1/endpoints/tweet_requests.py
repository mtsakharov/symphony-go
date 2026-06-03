"""Tweet request readiness endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.tweet_requests.draft_exceptions import TweetRequestDraftNotFoundError
from app.tweet_requests.draft_schemas import (
    TweetRequestDraftCreate,
    TweetRequestDraftResponse,
    TweetRequestDraftUpdate,
)
from app.tweet_requests.draft_service import TweetRequestDraftService
from app.tweet_requests.schemas import TweetRequest, TweetRequestReadiness
from app.tweet_requests.service import TweetRequestService

router = APIRouter()


def get_tweet_request_service() -> TweetRequestService:
    """Return a tweet request service instance."""

    return TweetRequestService()


def get_tweet_request_draft_service() -> TweetRequestDraftService:
    """Return a tweet request draft service instance."""

    return TweetRequestDraftService()


@router.post(
    "",
    response_model=TweetRequestDraftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tweet request draft",
    description=(
        "Create a tweet request draft from a partial brief and return structured "
        "readiness plus review-gating feedback."
    ),
    operation_id="createTweetRequest",
)
def create_tweet_request(
    payload: TweetRequestDraftCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[TweetRequestDraftService, Depends(get_tweet_request_draft_service)],
) -> TweetRequestDraftResponse:
    """Create a new tweet request draft."""

    return service.create_tweet_request(session, payload)


@router.patch(
    "/{tweet_request_id}",
    response_model=TweetRequestDraftResponse,
    summary="Update tweet request draft",
    description=(
        "Apply partial updates to a tweet request draft, resetting approvals when "
        "gated brief content changes."
    ),
    operation_id="updateTweetRequest",
)
def update_tweet_request(
    tweet_request_id: UUID,
    payload: TweetRequestDraftUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[TweetRequestDraftService, Depends(get_tweet_request_draft_service)],
) -> TweetRequestDraftResponse:
    """Update an existing tweet request draft."""

    try:
        return service.update_tweet_request(session, tweet_request_id, payload)
    except TweetRequestDraftNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/readiness",
    response_model=TweetRequestReadiness,
    summary="Evaluate tweet request readiness",
    description=(
        "Validate a tweet intake payload against the canonical format and readiness rules."
    ),
    operation_id="evaluateTweetRequestReadiness",
)
def evaluate_tweet_request_readiness(
    payload: TweetRequest,
    service: Annotated[TweetRequestService, Depends(get_tweet_request_service)],
) -> TweetRequestReadiness:
    """Evaluate whether a tweet request is ready for writing."""

    return service.evaluate_readiness(payload)
