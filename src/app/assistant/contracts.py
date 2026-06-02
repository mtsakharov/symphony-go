"""Canonical v1 assistant retrieval and session contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EligiblePostSourceOfTruth(StrEnum):
    """Authoritative post snapshot used for retrieval decisions."""

    CURRENT_PERSISTED_POST_SNAPSHOT = "current_persisted_post_snapshot"


class SessionPersistenceMode(StrEnum):
    """Supported chat session persistence modes."""

    EPHEMERAL = "ephemeral"
    PERSISTED = "persisted"


class ContentInvalidationReason(StrEnum):
    """Events that revoke or invalidate indexed post content."""

    DELETED = "deleted"
    PRIVACY_REDUCED = "privacy_reduced"
    MODERATION_REMOVED = "moderation_removed"
    BLOCKED_ACCESS = "blocked_access"


@dataclass(frozen=True, slots=True)
class PrivacyLoggingPolicy:
    """Logging and retention restrictions for retrieval operations."""

    log_raw_embedding_vectors: bool
    log_prompt_bodies: bool
    log_citation_text: bool
    retain_private_or_deleted_content_outside_operational_stores: bool


@dataclass(frozen=True, slots=True)
class V1AssistantContract:
    """Canonical v1 policy decisions for retrieval and session handling."""

    eligible_post_source_of_truth: EligiblePostSourceOfTruth
    exclude_drafts: bool
    ignore_edit_history: bool
    request_time_access_recheck: bool
    session_persistence: SessionPersistenceMode
    invalidation_reasons: frozenset[ContentInvalidationReason]
    privacy_logging_policy: PrivacyLoggingPolicy


V1_PRIVACY_LOGGING_POLICY = PrivacyLoggingPolicy(
    log_raw_embedding_vectors=False,
    log_prompt_bodies=False,
    log_citation_text=False,
    retain_private_or_deleted_content_outside_operational_stores=False,
)


V1_ASSISTANT_CONTRACT = V1AssistantContract(
    eligible_post_source_of_truth=EligiblePostSourceOfTruth.CURRENT_PERSISTED_POST_SNAPSHOT,
    exclude_drafts=True,
    ignore_edit_history=True,
    request_time_access_recheck=True,
    session_persistence=SessionPersistenceMode.EPHEMERAL,
    invalidation_reasons=frozenset(
        {
            ContentInvalidationReason.DELETED,
            ContentInvalidationReason.PRIVACY_REDUCED,
            ContentInvalidationReason.MODERATION_REMOVED,
            ContentInvalidationReason.BLOCKED_ACCESS,
        }
    ),
    privacy_logging_policy=V1_PRIVACY_LOGGING_POLICY,
)
