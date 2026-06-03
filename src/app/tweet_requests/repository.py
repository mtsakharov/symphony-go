"""Repository layer for tweet requests."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.tweet_requests.models import TweetRequest


class TweetRequestRepository:
    """Persist and query tweet requests."""

    def get_by_id(self, session: Session, tweet_request_id: UUID) -> TweetRequest | None:
        """Return a tweet request by id if present."""

        return session.get(TweetRequest, tweet_request_id)

    def create(self, session: Session, *, tweet_request: TweetRequest) -> TweetRequest:
        """Persist a new tweet request."""

        session.add(tweet_request)
        session.flush()
        return tweet_request
