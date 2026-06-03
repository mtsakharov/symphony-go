"""Service layer for tweet requests."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.tweet_requests.exceptions import TweetRequestNotFoundError
from app.tweet_requests.models import TweetRequest, TweetRequestStatus
from app.tweet_requests.repository import TweetRequestRepository
from app.tweet_requests.schemas import (
    MissingReadinessField,
    ReadinessBlocker,
    TweetRequestCreate,
    TweetRequestResponse,
    TweetRequestStatusEvaluationResponse,
    TweetRequestUpdate,
    TweetRequestValidation,
)

_REQUIRED_FIELD_MESSAGES: dict[str, str] = {
    "brief": "Provide the core brief before writing can start.",
    "target_audience": "Specify the target audience for the tweet.",
    "objective": "Clarify the tweet objective before writing can start.",
}
_REVIEW_GATED_FIELDS = (
    "brief",
    "target_audience",
    "objective",
    "tone",
    "call_to_action",
)


@dataclass(frozen=True)
class TweetRequestReadiness:
    """Derived readiness state for a tweet request."""

    status: TweetRequestStatus
    validation: TweetRequestValidation


class TweetRequestService:
    """Business logic for tweet request drafts."""

    def __init__(self, repository: TweetRequestRepository | None = None) -> None:
        self.repository = repository or TweetRequestRepository()

    def create_tweet_request(
        self,
        session: Session,
        payload: TweetRequestCreate,
    ) -> TweetRequestResponse:
        """Create a new tweet request draft from a partial intake payload."""

        tweet_request = TweetRequest(**payload.model_dump())
        readiness = self._evaluate_readiness(tweet_request)
        tweet_request.status = readiness.status.value

        self.repository.create(session, tweet_request=tweet_request)
        session.commit()
        session.refresh(tweet_request)

        return self._build_response(tweet_request, readiness)

    def update_tweet_request(
        self,
        session: Session,
        tweet_request_id: UUID,
        payload: TweetRequestUpdate,
    ) -> TweetRequestResponse:
        """Apply incremental updates to a tweet request draft."""

        tweet_request = self.repository.get_by_id(session, tweet_request_id)
        if tweet_request is None:
            raise TweetRequestNotFoundError("Tweet request not found")

        update_data = payload.model_dump(exclude_unset=True)

        if self._changes_review_gated_content(tweet_request, update_data):
            if "approved_by_compliance" not in update_data:
                tweet_request.approved_by_compliance = None
            if "approved_by_reviewer" not in update_data:
                tweet_request.approved_by_reviewer = None

        for field_name, value in update_data.items():
            setattr(tweet_request, field_name, value)

        readiness = self._evaluate_readiness(tweet_request)
        tweet_request.status = readiness.status.value

        session.add(tweet_request)
        session.commit()
        session.refresh(tweet_request)

        return self._build_response(tweet_request, readiness)

    def get_tweet_request(
        self,
        session: Session,
        tweet_request_id: UUID,
    ) -> TweetRequestResponse:
        """Return a tweet request with its derived readiness details."""

        tweet_request = self._get_tweet_request_or_raise(session, tweet_request_id)
        return self._build_response(tweet_request)

    def evaluate_status(
        self,
        session: Session,
        tweet_request_id: UUID,
    ) -> TweetRequestStatusEvaluationResponse:
        """Return the current derived status and validation details."""

        tweet_request = self._get_tweet_request_or_raise(session, tweet_request_id)
        readiness = self._evaluate_readiness(tweet_request)
        return TweetRequestStatusEvaluationResponse(
            id=tweet_request.id,
            status=readiness.status,
            validation=readiness.validation,
        )

    def _evaluate_readiness(self, tweet_request: TweetRequest) -> TweetRequestReadiness:
        """Compute the current readiness state for a tweet request."""

        missing_fields = [
            MissingReadinessField(field=field_name, message=message)
            for field_name, message in _REQUIRED_FIELD_MESSAGES.items()
            if getattr(tweet_request, field_name) is None
        ]

        blockers: list[ReadinessBlocker] = []
        if not missing_fields:
            if tweet_request.approved_by_compliance is not True:
                blockers.append(
                    ReadinessBlocker(
                        code="compliance_approval_required",
                        message="Compliance approval is required before writing can start.",
                    )
                )
            if tweet_request.approved_by_reviewer is not True:
                blockers.append(
                    ReadinessBlocker(
                        code="reviewer_approval_required",
                        message="Reviewer approval is required before writing can start.",
                    )
                )

        has_intake_content = any(
            getattr(tweet_request, field_name) is not None
            for field_name in (
                "brief",
                "target_audience",
                "objective",
                "tone",
                "call_to_action",
                "reviewer_notes",
            )
        )

        if not has_intake_content:
            status = TweetRequestStatus.DRAFT
        elif missing_fields:
            status = TweetRequestStatus.NEEDS_CLARIFICATION
        elif blockers:
            status = TweetRequestStatus.BLOCKED_REVIEW
        else:
            status = TweetRequestStatus.READY_FOR_WRITING

        validation = TweetRequestValidation(
            is_ready=status is TweetRequestStatus.READY_FOR_WRITING,
            missing_fields=missing_fields,
            blockers=blockers,
        )
        return TweetRequestReadiness(status=status, validation=validation)

    def _changes_review_gated_content(
        self,
        tweet_request: TweetRequest,
        update_data: dict[str, object],
    ) -> bool:
        """Return whether the update changes fields that require fresh approvals."""

        return any(
            field_name in update_data
            and getattr(tweet_request, field_name) != update_data[field_name]
            for field_name in _REVIEW_GATED_FIELDS
        )

    def _get_tweet_request_or_raise(
        self,
        session: Session,
        tweet_request_id: UUID,
    ) -> TweetRequest:
        """Load a tweet request or raise the domain not-found error."""

        tweet_request = self.repository.get_by_id(session, tweet_request_id)
        if tweet_request is None:
            raise TweetRequestNotFoundError("Tweet request not found")
        return tweet_request

    def _build_response(
        self,
        tweet_request: TweetRequest,
        readiness: TweetRequestReadiness | None = None,
    ) -> TweetRequestResponse:
        """Serialize a tweet request and its derived validation output."""

        resolved_readiness = readiness or self._evaluate_readiness(tweet_request)
        return TweetRequestResponse(
            id=tweet_request.id,
            brief=tweet_request.brief,
            target_audience=tweet_request.target_audience,
            objective=tweet_request.objective,
            tone=tweet_request.tone,
            call_to_action=tweet_request.call_to_action,
            reviewer_notes=tweet_request.reviewer_notes,
            approved_by_compliance=tweet_request.approved_by_compliance,
            approved_by_reviewer=tweet_request.approved_by_reviewer,
            status=resolved_readiness.status,
            validation=resolved_readiness.validation,
            created_at=tweet_request.created_at,
            updated_at=tweet_request.updated_at,
        )
