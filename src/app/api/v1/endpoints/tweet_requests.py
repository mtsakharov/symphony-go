"""Tweet request readiness endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.tweet_requests.schemas import TweetRequest, TweetRequestReadiness
from app.tweet_requests.service import TweetRequestService

router = APIRouter()


def get_tweet_request_service() -> TweetRequestService:
    """Return a tweet request service instance."""

    return TweetRequestService()


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
