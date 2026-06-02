"""Telemetry helper tests."""

from __future__ import annotations

import json
import logging

import pytest
from _pytest.logging import LogCaptureFixture
from pytest import MonkeyPatch

from app.core.logging import JsonFormatter
from app.core.telemetry import ChatTelemetry, TelemetryEmitter, compute_citation_coverage


def test_emitter_formats_structured_fields_and_drops_sensitive_content(
    caplog: LogCaptureFixture,
) -> None:
    """Structured logs should preserve safe fields and omit private free text."""

    logger = logging.getLogger("tests.telemetry.structured")
    emitter = TelemetryEmitter(logger=logger)

    with caplog.at_level(logging.INFO, logger=logger.name):
        emitter.emit(
            "chat.response",
            request_id="req-1",
            citation_count=2,
            prompt="private prompt",
            metadata={
                "retrieval_result_count": 2,
                "snippet_text": "private snippet",
            },
        )

    assert len(caplog.records) == 1
    payload = json.loads(JsonFormatter().format(caplog.records[0]))
    assert payload["event"] == "chat.response"
    assert payload["request_id"] == "req-1"
    assert payload["citation_count"] == 2
    assert payload["metadata"] == {"retrieval_result_count": 2}
    assert "prompt" not in payload


def test_chat_telemetry_emits_success_path_events(
    caplog: LogCaptureFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """Request, retrieval, generation, and response events should be emitted on success."""

    logger = logging.getLogger("tests.telemetry.success")
    telemetry = ChatTelemetry(emitter=TelemetryEmitter(logger=logger))
    _set_perf_counter(
        monkeypatch,
        [
            0.0,
            0.010,
            0.030,
            0.040,
            0.090,
            0.100,
        ],
    )

    with (
        caplog.at_level(logging.INFO, logger=logger.name),
        telemetry.track_request(request_id="req-1", route="/api/v1/chat"),
    ):
        with telemetry.track_retrieval(
            request_id="req-1",
            retrieval_candidate_count=3,
            retrieval_result_count=2,
            retrieval_used_count=2,
        ):
            pass
        with telemetry.track_generation(
            request_id="req-1",
            provider="openai",
            model="gpt-4.1-mini",
        ):
            pass
        telemetry.record_response(
            request_id="req-1",
            citation_count=2,
            citation_opportunity_count=4,
        )

    payloads = _format_payloads(caplog)
    assert [payload["event"] for payload in payloads] == [
        "chat.retrieval",
        "chat.generation",
        "chat.response",
        "chat.request",
    ]
    assert payloads[0]["duration_ms"] == 20.0
    assert payloads[0]["retrieval_miss"] is False
    assert payloads[1]["duration_ms"] == 50.0
    assert payloads[1]["provider"] == "openai"
    assert payloads[2]["citation_coverage"] == 0.5
    assert payloads[3]["duration_ms"] == 100.0
    assert payloads[3]["status"] == "success"


def test_chat_telemetry_emits_retrieval_miss_and_fallback_counters(
    caplog: LogCaptureFixture,
) -> None:
    """Retrieval misses and insufficient-evidence fallbacks should be countable from logs."""

    logger = logging.getLogger("tests.telemetry.fallback")
    telemetry = ChatTelemetry(emitter=TelemetryEmitter(logger=logger))

    with caplog.at_level(logging.INFO, logger=logger.name):
        telemetry.record_retrieval(
            request_id="req-2",
            duration_ms=12.5,
            status="success",
            retrieval_candidate_count=4,
            retrieval_result_count=0,
            retrieval_used_count=0,
        )
        telemetry.record_insufficient_evidence(request_id="req-2")
        telemetry.record_response(
            request_id="req-2",
            citation_count=0,
            citation_opportunity_count=0,
            insufficient_evidence=True,
        )

    payloads = _format_payloads(caplog)
    assert [payload["event"] for payload in payloads] == [
        "chat.retrieval",
        "chat.metric",
        "chat.insufficient_evidence",
        "chat.metric",
        "chat.response",
    ]
    assert payloads[0]["retrieval_miss"] is True
    assert payloads[1]["metric_name"] == "chat.retrieval_miss"
    assert payloads[1]["metric_value"] == 1
    assert payloads[2]["insufficient_evidence"] is True
    assert payloads[3]["metric_name"] == "chat.insufficient_evidence_fallback"
    assert payloads[4]["citation_coverage"] == 1.0


def test_chat_telemetry_emits_model_failure_and_request_error(
    caplog: LogCaptureFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    """Provider/model failures should emit safe failure telemetry once per hook."""

    logger = logging.getLogger("tests.telemetry.failure")
    telemetry = ChatTelemetry(emitter=TelemetryEmitter(logger=logger))
    _set_perf_counter(monkeypatch, [0.0, 0.010, 0.030, 0.050])

    with (
        caplog.at_level(logging.INFO, logger=logger.name),
        pytest.raises(RuntimeError),
        telemetry.track_request(
            request_id="req-3",
            prompt="private prompt",
            answer_text="private answer",
        ),
        telemetry.track_generation(
            request_id="req-3",
            provider="openai",
            model="gpt-4.1-mini",
            messages=[{"content": "private content"}],
        ),
    ):
        raise RuntimeError("provider timeout")

    payloads = _format_payloads(caplog)
    assert [payload["event"] for payload in payloads] == [
        "chat.generation",
        "chat.metric",
        "chat.request",
    ]
    assert payloads[0]["status"] == "error"
    assert payloads[0]["error_type"] == "RuntimeError"
    assert payloads[1]["metric_name"] == "chat.model_failure"
    assert payloads[1]["provider"] == "openai"
    assert payloads[2]["status"] == "error"
    assert all("prompt" not in payload and "answer_text" not in payload for payload in payloads)


def test_compute_citation_coverage_validates_inputs() -> None:
    """Citation coverage should reject invalid counts."""

    with pytest.raises(ValueError):
        compute_citation_coverage(citation_count=-1, citation_opportunity_count=1)

    with pytest.raises(ValueError):
        compute_citation_coverage(citation_count=1, citation_opportunity_count=-1)


def _format_payloads(caplog: LogCaptureFixture) -> list[dict[str, object]]:
    """Format captured records as structured JSON payloads."""

    formatter = JsonFormatter()
    return [json.loads(formatter.format(record)) for record in caplog.records]


def _set_perf_counter(monkeypatch: MonkeyPatch, values: list[float]) -> None:
    """Patch perf_counter with deterministic values for duration assertions."""

    iterator = iter(values)
    monkeypatch.setattr("app.core.telemetry.perf_counter", lambda: next(iterator))
