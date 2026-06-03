"""Unit tests for tweet request draft gating."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.tweet_requests.draft_exceptions import TweetRequestDraftNotFoundError
from app.tweet_requests.draft_models import TweetRequestDraft
from app.tweet_requests.draft_repository import TweetRequestDraftRepository
from app.tweet_requests.draft_schemas import TweetRequestDraftCreate, TweetRequestDraftUpdate
from app.tweet_requests.draft_service import TweetRequestDraftService
from app.tweet_requests.schemas import TweetRequestStatus


def build_tweet_request(**overrides: object) -> TweetRequestDraft:
    """Return a hydrated tweet request model for service tests."""

    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "id": uuid4(),
        "brief": None,
        "target_audience": None,
        "objective": None,
        "tone": None,
        "call_to_action": None,
        "reviewer_notes": None,
        "approved_by_compliance": None,
        "approved_by_reviewer": None,
        "status": TweetRequestStatus.DRAFT.value,
        "created_at": now,
        "updated_at": now,
    }
    payload.update(overrides)
    return TweetRequestDraft(**payload)


def test_create_tweet_request_marks_empty_intake_as_draft() -> None:
    """Service should accept empty intake and return structured missing fields."""

    repository = Mock(spec=TweetRequestDraftRepository)

    def create_tweet_request(
        session: Mock,
        *,
        tweet_request: TweetRequestDraft,
    ) -> TweetRequestDraft:
        now = datetime.now(UTC)
        tweet_request.id = uuid4()
        tweet_request.created_at = now
        tweet_request.updated_at = now
        return tweet_request

    repository.create.side_effect = create_tweet_request
    service = TweetRequestDraftService(repository=repository)
    session = Mock()

    response = service.create_tweet_request(session, TweetRequestDraftCreate())

    assert response.status is TweetRequestStatus.DRAFT
    assert [field.field for field in response.validation.missing_fields] == [
        "brief",
        "target_audience",
        "objective",
    ]
    assert response.validation.blockers == []
    session.commit.assert_called_once()


def test_create_tweet_request_blocks_complete_brief_pending_review() -> None:
    """Service should surface review blockers once the brief is otherwise complete."""

    repository = Mock(spec=TweetRequestDraftRepository)

    def create_tweet_request(
        session: Mock,
        *,
        tweet_request: TweetRequestDraft,
    ) -> TweetRequestDraft:
        now = datetime.now(UTC)
        tweet_request.id = uuid4()
        tweet_request.created_at = now
        tweet_request.updated_at = now
        return tweet_request

    repository.create.side_effect = create_tweet_request
    service = TweetRequestDraftService(repository=repository)
    session = Mock()

    response = service.create_tweet_request(
        session,
        TweetRequestDraftCreate(
            brief="Announce the summer release.",
            target_audience="Existing enterprise customers",
            objective="Drive signups for the waitlist",
        ),
    )

    assert response.status is TweetRequestStatus.BLOCKED_REVIEW
    assert [blocker.code for blocker in response.validation.blockers] == [
        "compliance_approval_required",
        "reviewer_approval_required",
    ]


def test_update_tweet_request_can_become_ready_for_writing() -> None:
    """Service should recompute status after an incremental update."""

    repository = Mock(spec=TweetRequestDraftRepository)
    repository.get_by_id.return_value = build_tweet_request(brief="Announce the summer release.")
    service = TweetRequestDraftService(repository=repository)
    session = Mock()

    response = service.update_tweet_request(
        session,
        repository.get_by_id.return_value.id,
        TweetRequestDraftUpdate(
            target_audience="Existing enterprise customers",
            objective="Drive signups for the waitlist",
            approved_by_compliance=True,
            approved_by_reviewer=True,
        ),
    )

    assert response.status is TweetRequestStatus.READY_FOR_WRITING
    assert response.validation.is_ready is True
    assert response.validation.missing_fields == []
    assert response.validation.blockers == []
    session.commit.assert_called_once()


def test_update_tweet_request_resets_approvals_after_brief_change() -> None:
    """Changing the approved brief content should require fresh approvals."""

    repository = Mock(spec=TweetRequestDraftRepository)
    repository.get_by_id.return_value = build_tweet_request(
        brief="Announce the summer release.",
        target_audience="Existing enterprise customers",
        objective="Drive signups for the waitlist",
        approved_by_compliance=True,
        approved_by_reviewer=True,
        status=TweetRequestStatus.READY_FOR_WRITING.value,
    )
    service = TweetRequestDraftService(repository=repository)
    session = Mock()

    response = service.update_tweet_request(
        session,
        repository.get_by_id.return_value.id,
        TweetRequestDraftUpdate(brief="Announce the fall release."),
    )

    assert response.approved_by_compliance is None
    assert response.approved_by_reviewer is None
    assert response.status is TweetRequestStatus.BLOCKED_REVIEW
    assert [blocker.code for blocker in response.validation.blockers] == [
        "compliance_approval_required",
        "reviewer_approval_required",
    ]
    session.commit.assert_called_once()


def test_update_tweet_request_raises_not_found_when_missing() -> None:
    """Service should raise a domain error when a tweet request does not exist."""

    repository = Mock(spec=TweetRequestDraftRepository)
    repository.get_by_id.return_value = None
    service = TweetRequestDraftService(repository=repository)
    session = Mock()

    with pytest.raises(TweetRequestDraftNotFoundError, match="Tweet request not found"):
        service.update_tweet_request(
            session,
            uuid4(),
            TweetRequestDraftUpdate(objective="Drive signups for the waitlist"),
        )
