"""Telemetry helper tests."""

from __future__ import annotations

import json
import logging

from _pytest.logging import LogCaptureFixture

from app.core.logging import JsonFormatter
from app.core.telemetry import TelemetryEmitter, TweetRequestTelemetry


def test_emitter_formats_structured_fields_and_drops_sensitive_tweet_content(
    caplog: LogCaptureFixture,
) -> None:
    """Structured logs should preserve safe fields and omit private tweet text."""

    logger = logging.getLogger("tests.telemetry.structured")
    emitter = TelemetryEmitter(logger=logger)

    with caplog.at_level(logging.INFO, logger=logger.name):
        emitter.emit(
            "tweet_request.created",
            request_id="req-1",
            tweet_body="private text",
            metadata={
                "channel": "api",
                "tweet_text": "private copy",
            },
        )

    payload = _single_payload(caplog)
    assert payload["event"] == "tweet_request.created"
    assert payload["request_id"] == "req-1"
    assert payload["metadata"] == {"channel": "api"}
    assert "tweet_body" not in payload


def test_tweet_request_telemetry_emits_lifecycle_events_and_counters(
    caplog: LogCaptureFixture,
) -> None:
    """Lifecycle helpers should emit the event/counter pairs needed for operators."""

    logger = logging.getLogger("tests.telemetry.lifecycle")
    telemetry = TweetRequestTelemetry(emitter=TelemetryEmitter(logger=logger))

    with caplog.at_level(logging.INFO, logger=logger.name):
        telemetry.record_created(request_id="req-2", source="api")
        telemetry.record_clarification_loop(
            request_id="req-2",
            clarification_count=2,
            loop_state="awaiting_user",
        )
        telemetry.record_readiness_evaluation(
            request_id="req-2",
            readiness_state="needs_clarification",
            is_writable=False,
            blocker_summary="Missing product angle",
            blocker_codes=["missing_context"],
        )
        telemetry.record_drop_decision(
            request_id="req-2",
            drop_reason="duplicate_request",
            blocker_summary="Superseded by req-3",
        )
        telemetry.record_compliance_blocked(
            request_id="req-2",
            blocked_transition="ready_to_writable",
            blocker_summary="Missing reviewer approval",
            blocker_codes=["review_required"],
        )

    payloads = _format_payloads(caplog)
    assert [payload["event"] for payload in payloads] == [
        "tweet_request.created",
        "tweet_request.metric",
        "tweet_request.clarification_loop",
        "tweet_request.metric",
        "tweet_request.readiness_evaluated",
        "tweet_request.metric",
        "tweet_request.metric",
        "tweet_request.drop_decision",
        "tweet_request.metric",
        "tweet_request.compliance_blocked",
        "tweet_request.metric",
    ]
    assert payloads[0]["source"] == "api"
    assert payloads[2]["clarification_count"] == 2
    assert payloads[4]["is_writable"] is False
    assert payloads[4]["blocker_summary"] == "Missing product angle"
    assert payloads[6]["metric_name"] == "tweet_request.not_writable"
    assert payloads[6]["blocker_codes"] == ["missing_context"]
    assert payloads[8]["drop_reason"] == "duplicate_request"
    assert payloads[10]["blocked_transition"] == "ready_to_writable"


def test_status_transition_audit_log_preserves_request_id_and_blocker_summary(
    caplog: LogCaptureFixture,
) -> None:
    """Status transition logs should be queryable as audit records."""

    logger = logging.getLogger("tests.telemetry.transition")
    telemetry = TweetRequestTelemetry(emitter=TelemetryEmitter(logger=logger))

    with caplog.at_level(logging.INFO, logger=logger.name):
        telemetry.record_status_transition(
            request_id="req-3",
            from_status="needs_clarification",
            to_status="blocked",
            blocker_summary="Reviewer rejected unsafe claim",
            blocker_codes=["unsafe_claim"],
            transition_reason="compliance_review_failed",
            tweet_brief="private prompt",
        )

    payload = _single_payload(caplog)
    assert payload["event"] == "tweet_request.status_transition"
    assert payload["request_id"] == "req-3"
    assert payload["from_status"] == "needs_clarification"
    assert payload["to_status"] == "blocked"
    assert payload["blocker_summary"] == "Reviewer rejected unsafe claim"
    assert payload["blocker_codes"] == ["unsafe_claim"]
    assert payload["transition_reason"] == "compliance_review_failed"
    assert payload["audit_log"] is True
    assert "tweet_brief" not in payload


def _format_payloads(caplog: LogCaptureFixture) -> list[dict[str, object]]:
    """Format captured records as structured JSON payloads."""

    formatter = JsonFormatter()
    return [json.loads(formatter.format(record)) for record in caplog.records]


def _single_payload(caplog: LogCaptureFixture) -> dict[str, object]:
    """Return the single structured payload emitted during a test."""

    payloads = _format_payloads(caplog)
    assert len(payloads) == 1
    return payloads[0]
