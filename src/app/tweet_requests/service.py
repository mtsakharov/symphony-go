"""Readiness evaluation for tweet request intake payloads."""

from __future__ import annotations

from app.tweet_requests.schemas import (
    TweetFormat,
    TweetRequest,
    TweetRequestIssue,
    TweetRequestIssueCode,
    TweetRequestReadiness,
    TweetRequestStatus,
)


class TweetRequestService:
    """Evaluate tweet request payloads against the readiness contract."""

    def evaluate_readiness(self, payload: TweetRequest) -> TweetRequestReadiness:
        """Return the current readiness state for a tweet request payload."""

        draft_issues = self._collect_draft_issues(payload)
        clarification_issues = self._collect_clarification_issues(payload)
        blocked_issues = self._collect_blocked_review_issues(payload)

        if draft_issues:
            status = TweetRequestStatus.DRAFT
            expected_deliverables = None
            issues = draft_issues + clarification_issues
        elif clarification_issues:
            status = TweetRequestStatus.NEEDS_CLARIFICATION
            expected_deliverables = None
            issues = clarification_issues
        elif blocked_issues:
            status = TweetRequestStatus.BLOCKED_REVIEW
            expected_deliverables = _expected_deliverables(payload)
            issues = blocked_issues
        else:
            status = TweetRequestStatus.READY_FOR_WRITING
            expected_deliverables = _expected_deliverables(payload)
            issues = []

        return TweetRequestReadiness(
            status=status,
            is_ready=status is TweetRequestStatus.READY_FOR_WRITING,
            expected_deliverables=expected_deliverables,
            issues=issues,
        )

    def _collect_draft_issues(self, payload: TweetRequest) -> list[TweetRequestIssue]:
        """Return missing-core-field issues that keep a request in draft."""

        issues: list[TweetRequestIssue] = []

        if payload.product_or_campaign is None:
            issues.append(
                _issue(
                    TweetRequestIssueCode.MISSING_PRODUCT_OR_CAMPAIGN,
                    "Provide `product_or_campaign` before the request can be written.",
                )
            )
        if payload.audience is None:
            issues.append(
                _issue(
                    TweetRequestIssueCode.MISSING_AUDIENCE,
                    "Provide `audience` before the request can be written.",
                )
            )
        if payload.intended_action is None:
            issues.append(
                _issue(
                    TweetRequestIssueCode.MISSING_INTENDED_ACTION,
                    "Provide `intended_action` before the request can be written.",
                )
            )
        if payload.format is None:
            issues.append(
                _issue(
                    TweetRequestIssueCode.MISSING_FORMAT,
                    "Provide `format` to define the request scope.",
                )
            )
        if payload.tweet_count is None:
            issues.append(
                _issue(
                    TweetRequestIssueCode.MISSING_TWEET_COUNT,
                    "Provide `tweet_count` to define the requested scope.",
                )
            )
        if payload.variants_per_tweet is None:
            issues.append(
                _issue(
                    TweetRequestIssueCode.MISSING_VARIANTS_PER_TWEET,
                    "Provide `variants_per_tweet` to define the alternate-count semantics.",
                )
            )
        if not payload.context.has_writable_context():
            issues.append(
                _issue(
                    TweetRequestIssueCode.MISSING_CONTEXT,
                    "Provide `context.brief` or at least one `context.source_materials` entry.",
                )
            )

        return issues

    def _collect_clarification_issues(self, payload: TweetRequest) -> list[TweetRequestIssue]:
        """Return semantic validation issues for an otherwise present payload."""

        issues: list[TweetRequestIssue] = []

        if payload.tweet_count is not None and payload.tweet_count < 1:
            issues.append(
                _issue(
                    TweetRequestIssueCode.INVALID_TWEET_COUNT,
                    "`tweet_count` must be greater than or equal to 1.",
                )
            )
        if payload.variants_per_tweet is not None and payload.variants_per_tweet < 1:
            issues.append(
                _issue(
                    TweetRequestIssueCode.INVALID_VARIANTS_PER_TWEET,
                    "`variants_per_tweet` must be greater than or equal to 1.",
                )
            )

        if payload.format is TweetFormat.THREAD:
            if payload.tweet_count is not None and payload.tweet_count < 2:
                issues.append(
                    _issue(
                        TweetRequestIssueCode.THREAD_REQUIRES_MULTIPLE_TWEETS,
                        "Thread requests must include at least 2 tweets.",
                    )
                )
            if payload.variants_per_tweet is not None and payload.variants_per_tweet != 1:
                issues.append(
                    _issue(
                        TweetRequestIssueCode.THREAD_DISALLOWS_VARIANTS,
                        "Thread requests must set `variants_per_tweet` to 1.",
                    )
                )

        if payload.format is TweetFormat.REPLY:
            if payload.reply_to_tweet_id is None:
                issues.append(
                    _issue(
                        TweetRequestIssueCode.REPLY_REQUIRES_PARENT_TWEET_ID,
                        "Reply requests require `reply_to_tweet_id`.",
                    )
                )
            if payload.reply_to_author_handle is None:
                issues.append(
                    _issue(
                        TweetRequestIssueCode.REPLY_REQUIRES_PARENT_AUTHOR_HANDLE,
                        "Reply requests require `reply_to_author_handle`.",
                    )
                )

        return issues

    def _collect_blocked_review_issues(self, payload: TweetRequest) -> list[TweetRequestIssue]:
        """Return issues that block a fully specified request on review metadata."""

        if payload.format is not TweetFormat.PAID:
            return []

        issues: list[TweetRequestIssue] = []
        if payload.review.approval_required is not True:
            issues.append(
                _issue(
                    TweetRequestIssueCode.PAID_REQUIRES_APPROVAL,
                    "Paid requests require `review.approval_required = true`.",
                )
            )
        if payload.review.compliance_owner is None:
            issues.append(
                _issue(
                    TweetRequestIssueCode.PAID_REQUIRES_COMPLIANCE_OWNER,
                    "Paid requests require `review.compliance_owner` before writing.",
                )
            )
        return issues


def _expected_deliverables(payload: TweetRequest) -> int | None:
    """Return the total requested outputs implied by the payload."""

    if payload.format is None or payload.tweet_count is None or payload.variants_per_tweet is None:
        return None
    if payload.tweet_count < 1 or payload.variants_per_tweet < 1:
        return None

    if payload.format is TweetFormat.THREAD:
        if payload.tweet_count < 2 or payload.variants_per_tweet != 1:
            return None
        return payload.tweet_count

    return payload.tweet_count * payload.variants_per_tweet


def _issue(code: TweetRequestIssueCode, message: str) -> TweetRequestIssue:
    """Build a stable readiness issue payload."""

    return TweetRequestIssue(code=code, message=message)
