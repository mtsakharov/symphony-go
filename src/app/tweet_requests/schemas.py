"""Schemas for tweet request intake and readiness contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TweetFormat(StrEnum):
    """Supported tweet request formats."""

    ORGANIC = "organic"
    PAID = "paid"
    THREAD = "thread"
    REPLY = "reply"


class TweetRequestStatus(StrEnum):
    """Stable readiness states for tweet requests."""

    DRAFT = "draft"
    NEEDS_CLARIFICATION = "needs_clarification"
    READY_FOR_WRITING = "ready_for_writing"
    BLOCKED_REVIEW = "blocked_review"
    DROPPED = "dropped"


class TweetRequestIssueCode(StrEnum):
    """Machine-readable readiness issue codes."""

    MISSING_PRODUCT_OR_CAMPAIGN = "missing_product_or_campaign"
    MISSING_AUDIENCE = "missing_audience"
    MISSING_INTENDED_ACTION = "missing_intended_action"
    MISSING_FORMAT = "missing_format"
    MISSING_TWEET_COUNT = "missing_tweet_count"
    INVALID_TWEET_COUNT = "invalid_tweet_count"
    MISSING_VARIANTS_PER_TWEET = "missing_variants_per_tweet"
    INVALID_VARIANTS_PER_TWEET = "invalid_variants_per_tweet"
    MISSING_CONTEXT = "missing_context"
    THREAD_REQUIRES_MULTIPLE_TWEETS = "thread_requires_multiple_tweets"
    THREAD_DISALLOWS_VARIANTS = "thread_disallows_variants"
    REPLY_REQUIRES_PARENT_TWEET_ID = "reply_requires_parent_tweet_id"
    REPLY_REQUIRES_PARENT_AUTHOR_HANDLE = "reply_requires_parent_author_handle"
    PAID_REQUIRES_APPROVAL = "paid_requires_approval"
    PAID_REQUIRES_COMPLIANCE_OWNER = "paid_requires_compliance_owner"


def _normalize_optional_text(value: Any) -> Any:
    """Trim optional text fields and treat blank strings as missing."""

    if not isinstance(value, str):
        return value

    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _normalize_string_list(value: Any) -> Any:
    """Trim list items and drop blank string entries."""

    if value is None:
        return []
    if not isinstance(value, list):
        return value

    normalized_items: list[Any] = []
    for item in value:
        if isinstance(item, str):
            normalized = item.strip()
            if normalized:
                normalized_items.append(normalized)
            continue
        normalized_items.append(item)
    return normalized_items


class TweetRequestContext(BaseModel):
    """Source context used to write tweets."""

    brief: str | None = Field(
        default=None,
        description="Short writing brief or messaging summary for the request.",
    )
    source_materials: list[str] = Field(
        default_factory=list,
        description="Named source documents or assets the writer should use.",
    )

    @field_validator("brief", mode="before")
    @classmethod
    def normalize_brief(cls, value: Any) -> Any:
        """Normalize the optional brief field."""

        return _normalize_optional_text(value)

    @field_validator("source_materials", mode="before")
    @classmethod
    def normalize_source_materials(cls, value: Any) -> Any:
        """Normalize source-material entries."""

        return _normalize_string_list(value)

    def has_writable_context(self) -> bool:
        """Return whether the payload includes enough context to write from."""

        return self.brief is not None or bool(self.source_materials)


class TweetRequestReview(BaseModel):
    """Review and approval metadata for a tweet request."""

    approval_required: bool | None = Field(
        default=None,
        description="Whether approval is required before writing or publishing.",
    )
    approver: str | None = Field(
        default=None,
        description="Named approver for the request when one is assigned.",
    )
    compliance_owner: str | None = Field(
        default=None,
        description="Owner responsible for compliance review on paid requests.",
    )

    @field_validator("approver", "compliance_owner", mode="before")
    @classmethod
    def normalize_optional_review_text(cls, value: Any) -> Any:
        """Normalize optional review metadata."""

        return _normalize_optional_text(value)


class TweetRequestCompliance(BaseModel):
    """Compliance metadata attached to a tweet request."""

    regulated_claims: bool | None = Field(
        default=None,
        description="Whether the request touches regulated or legally sensitive claims.",
    )
    brand_safety_notes: str | None = Field(
        default=None,
        description="Optional notes covering brand-safety or public-response concerns.",
    )

    @field_validator("brand_safety_notes", mode="before")
    @classmethod
    def normalize_brand_safety_notes(cls, value: Any) -> Any:
        """Normalize optional compliance notes."""

        return _normalize_optional_text(value)


class TweetRequest(BaseModel):
    """Top-level tweet intake payload captured before writing begins."""

    product_or_campaign: str | None = Field(
        default=None,
        description="Human-readable product, launch, or campaign name.",
    )
    audience: str | None = Field(
        default=None,
        description="The intended audience for the tweets.",
    )
    intended_action: str | None = Field(
        default=None,
        description="The user action the copy should drive.",
    )
    format: TweetFormat | None = Field(
        default=None,
        description="Requested tweet format and scope.",
    )
    tweet_count: int | None = Field(
        default=None,
        description="Requested tweet slots, replies, or thread length depending on format.",
    )
    variants_per_tweet: int | None = Field(
        default=None,
        description="Alternate phrasings per tweet slot or reply slot.",
    )
    tone: str | None = Field(
        default=None,
        description="Optional tone guidance for the writing pass.",
    )
    cta: str | None = Field(
        default=None,
        description="Optional explicit call to action.",
    )
    deadline: str | None = Field(
        default=None,
        description="Optional delivery deadline as captured by the intake surface.",
    )
    success_metric: str | None = Field(
        default=None,
        description="Optional metric used to judge whether the request worked.",
    )
    reply_to_tweet_id: str | None = Field(
        default=None,
        description="Parent tweet id required for reply-format requests.",
    )
    reply_to_author_handle: str | None = Field(
        default=None,
        description="Parent tweet author handle required for reply-format requests.",
    )
    context: TweetRequestContext = Field(
        default_factory=TweetRequestContext,
        description="Context writers should use when producing tweet copy.",
    )
    review: TweetRequestReview = Field(
        default_factory=TweetRequestReview,
        description="Review metadata required for sensitive or paid requests.",
    )
    compliance: TweetRequestCompliance = Field(
        default_factory=TweetRequestCompliance,
        description="Compliance metadata attached to the request.",
    )

    @field_validator(
        "product_or_campaign",
        "audience",
        "intended_action",
        "tone",
        "cta",
        "deadline",
        "success_metric",
        "reply_to_tweet_id",
        "reply_to_author_handle",
        mode="before",
    )
    @classmethod
    def normalize_optional_text_fields(cls, value: Any) -> Any:
        """Normalize optional free-text fields."""

        return _normalize_optional_text(value)


class TweetRequestIssue(BaseModel):
    """Stable issue payload used by the readiness contract."""

    code: TweetRequestIssueCode
    message: str


class TweetRequestReadiness(BaseModel):
    """Readiness evaluation for a tweet request."""

    status: TweetRequestStatus
    is_ready: bool
    expected_deliverables: int | None = Field(
        default=None,
        ge=1,
        description="Total outputs implied by the request scope and count semantics.",
    )
    issues: list[TweetRequestIssue] = Field(default_factory=list)
