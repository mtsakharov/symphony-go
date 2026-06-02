"""Tests for the canonical assistant contract."""

from app.assistant import (
    V1_ASSISTANT_CONTRACT,
    ContentInvalidationReason,
    EligiblePostSourceOfTruth,
    SessionPersistenceMode,
)


def test_v1_assistant_contract_matches_planned_retrieval_rules() -> None:
    """The canonical contract should encode the approved retrieval constraints."""

    assert (
        V1_ASSISTANT_CONTRACT.eligible_post_source_of_truth
        == EligiblePostSourceOfTruth.CURRENT_PERSISTED_POST_SNAPSHOT
    )
    assert V1_ASSISTANT_CONTRACT.exclude_drafts is True
    assert V1_ASSISTANT_CONTRACT.ignore_edit_history is True
    assert V1_ASSISTANT_CONTRACT.request_time_access_recheck is True
    assert V1_ASSISTANT_CONTRACT.session_persistence == SessionPersistenceMode.EPHEMERAL


def test_v1_assistant_contract_includes_required_invalidation_reasons() -> None:
    """The contract should invalidate deleted, private, moderated, or blocked content."""

    assert V1_ASSISTANT_CONTRACT.invalidation_reasons == frozenset(
        {
            ContentInvalidationReason.DELETED,
            ContentInvalidationReason.PRIVACY_REDUCED,
            ContentInvalidationReason.MODERATION_REMOVED,
            ContentInvalidationReason.BLOCKED_ACCESS,
        }
    )


def test_v1_assistant_contract_disables_sensitive_logging_and_retention() -> None:
    """The privacy policy should prohibit logging sensitive retrieval artifacts."""

    policy = V1_ASSISTANT_CONTRACT.privacy_logging_policy

    assert policy.log_raw_embedding_vectors is False
    assert policy.log_prompt_bodies is False
    assert policy.log_citation_text is False
    assert policy.retain_private_or_deleted_content_outside_operational_stores is False
