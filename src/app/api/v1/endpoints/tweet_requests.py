"""Tweet request endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.tweet_requests.exceptions import TweetRequestNotFoundError
from app.tweet_requests.schemas import (
    TweetRequestCreate,
    TweetRequestResponse,
    TweetRequestStatusEvaluationResponse,
    TweetRequestUpdate,
)
from app.tweet_requests.service import TweetRequestService

router = APIRouter()


def get_tweet_request_service() -> TweetRequestService:
    """Return a tweet request service instance."""

    return TweetRequestService()


@router.post(
    "",
    response_model=TweetRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tweet request draft",
    description=(
        "Create a tweet request draft from a partial intake payload and return "
        "structured readiness feedback."
    ),
    operation_id="createTweetRequest",
)
def create_tweet_request(
    payload: TweetRequestCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[TweetRequestService, Depends(get_tweet_request_service)],
) -> TweetRequestResponse:
    """Create a new tweet request draft."""

    return service.create_tweet_request(session, payload)


@router.patch(
    "/{tweet_request_id}",
    response_model=TweetRequestResponse,
    summary="Update tweet request draft",
    description=(
        "Apply partial updates to a tweet request draft and recompute structured "
        "readiness feedback."
    ),
    operation_id="updateTweetRequest",
)
def update_tweet_request(
    tweet_request_id: UUID,
    payload: TweetRequestUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[TweetRequestService, Depends(get_tweet_request_service)],
) -> TweetRequestResponse:
    """Update an existing tweet request draft."""

    try:
        return service.update_tweet_request(session, tweet_request_id, payload)
    except TweetRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/{tweet_request_id}",
    response_model=TweetRequestResponse,
    summary="Fetch tweet request draft",
    description=(
        "Return a tweet request draft with its current derived readiness feedback."
    ),
    operation_id="getTweetRequest",
)
def get_tweet_request(
    tweet_request_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[TweetRequestService, Depends(get_tweet_request_service)],
) -> TweetRequestResponse:
    """Fetch an existing tweet request draft."""

    try:
        return service.get_tweet_request(session, tweet_request_id)
    except TweetRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/{tweet_request_id}/status",
    response_model=TweetRequestStatusEvaluationResponse,
    summary="Evaluate tweet request status",
    description=(
        "Recompute the derived readiness state for a tweet request without mutating "
        "the draft payload."
    ),
    operation_id="evaluateTweetRequestStatus",
)
def evaluate_tweet_request_status(
    tweet_request_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[TweetRequestService, Depends(get_tweet_request_service)],
) -> TweetRequestStatusEvaluationResponse:
    """Return the current derived status evaluation for a tweet request."""

    try:
        return service.evaluate_status(session, tweet_request_id)
    except TweetRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
