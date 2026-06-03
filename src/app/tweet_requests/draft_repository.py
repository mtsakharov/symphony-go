"""Repository layer for tweet request drafts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.tweet_requests.draft_models import TweetRequestDraft


class TweetRequestDraftRepository:
    """Persist and query tweet request drafts."""

    def get_by_id(self, session: Session, tweet_request_id: UUID) -> TweetRequestDraft | None:
        """Return a tweet request draft by id if present."""

        return session.get(TweetRequestDraft, tweet_request_id)

    def create(
        self,
        session: Session,
        *,
        tweet_request: TweetRequestDraft,
    ) -> TweetRequestDraft:
        """Persist a new tweet request draft."""

        session.add(tweet_request)
        session.flush()
        return tweet_request
