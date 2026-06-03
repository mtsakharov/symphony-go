"""Unit tests for tweet request readiness evaluation."""

from __future__ import annotations

from app.tweet_requests.schemas import (
    TweetFormat,
    TweetRequest,
    TweetRequestIssueCode,
    TweetRequestStatus,
)
from app.tweet_requests.service import TweetRequestService


def build_payload(*, format: TweetFormat = TweetFormat.ORGANIC) -> TweetRequest:
    """Return a minimally complete tweet request payload."""

    payload: dict[str, object] = {
        "product_or_campaign": "Acme Analytics launch",
        "audience": "B2B SaaS founders",
        "intended_action": "Book a demo",
        "format": format,
        "tweet_count": 2,
        "variants_per_tweet": 2,
        "context": {"brief": "Launch-day tweet copy."},
        "review": {
            "approval_required": False,
            "approver": None,
            "compliance_owner": None,
        },
        "compliance": {
            "regulated_claims": False,
            "brand_safety_notes": None,
        },
    }
    if format is TweetFormat.REPLY:
        payload["reply_to_tweet_id"] = "1796543210123456789"
        payload["reply_to_author_handle"] = "@customer_handle"
    return TweetRequest.model_validate(payload)


def test_evaluate_readiness_returns_draft_for_missing_core_fields() -> None:
    """Missing shared intake fields should keep the request in draft."""

    service = TweetRequestService()

    result = service.evaluate_readiness(TweetRequest.model_validate({}))
    codes = {issue.code for issue in result.issues}

    assert result.status is TweetRequestStatus.DRAFT
    assert result.is_ready is False
    assert result.expected_deliverables is None
    assert TweetRequestIssueCode.MISSING_AUDIENCE in codes
    assert TweetRequestIssueCode.MISSING_INTENDED_ACTION in codes
    assert TweetRequestIssueCode.MISSING_CONTEXT in codes


def test_evaluate_readiness_returns_needs_clarification_for_invalid_thread() -> None:
    """Invalid thread count and variants should trigger clarification issues."""

    service = TweetRequestService()
    payload = build_payload(format=TweetFormat.THREAD).model_copy(
        update={"tweet_count": 1, "variants_per_tweet": 2}
    )

    result = service.evaluate_readiness(payload)
    codes = {issue.code for issue in result.issues}

    assert result.status is TweetRequestStatus.NEEDS_CLARIFICATION
    assert result.is_ready is False
    assert result.expected_deliverables is None
    assert TweetRequestIssueCode.THREAD_REQUIRES_MULTIPLE_TWEETS in codes
    assert TweetRequestIssueCode.THREAD_DISALLOWS_VARIANTS in codes


def test_evaluate_readiness_returns_blocked_review_for_incomplete_paid_review() -> None:
    """Paid requests stay blocked when approval metadata is incomplete."""

    service = TweetRequestService()
    payload = build_payload(format=TweetFormat.PAID)

    result = service.evaluate_readiness(payload)
    codes = {issue.code for issue in result.issues}

    assert result.status is TweetRequestStatus.BLOCKED_REVIEW
    assert result.is_ready is False
    assert result.expected_deliverables == 4
    assert TweetRequestIssueCode.PAID_REQUIRES_APPROVAL in codes
    assert TweetRequestIssueCode.PAID_REQUIRES_COMPLIANCE_OWNER in codes


def test_evaluate_readiness_returns_ready_for_reply_request() -> None:
    """A fully specified reply request should be ready for writing."""

    service = TweetRequestService()
    payload = build_payload(format=TweetFormat.REPLY)

    result = service.evaluate_readiness(payload)

    assert result.status is TweetRequestStatus.READY_FOR_WRITING
    assert result.is_ready is True
    assert result.expected_deliverables == 4
    assert result.issues == []
