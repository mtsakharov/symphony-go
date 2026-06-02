"""Structured telemetry helpers for chat-style orchestration."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from app.core.logging import get_logger

SENSITIVE_FIELD_NAMES = frozenset(
    {
        "answer",
        "answer_text",
        "completion",
        "completion_text",
        "content",
        "message",
        "messages",
        "post_text",
        "post_body",
        "prompt",
        "prompt_text",
        "raw_messages",
        "response_text",
        "retrieved_content",
        "retrieved_post_text",
        "retrieved_snippet",
        "retrieved_snippet_text",
        "snippet",
        "snippet_text",
    }
)
_SEQUENCE_TYPES = (list, tuple, set, frozenset)


def compute_citation_coverage(
    citation_count: int,
    citation_opportunity_count: int,
) -> float:
    """Return the share of citation opportunities that were grounded."""

    if citation_count < 0:
        msg = "citation_count must be non-negative"
        raise ValueError(msg)
    if citation_opportunity_count < 0:
        msg = "citation_opportunity_count must be non-negative"
        raise ValueError(msg)
    if citation_opportunity_count == 0:
        return 1.0
    return round(citation_count / citation_opportunity_count, 6)


def sanitize_telemetry_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    """Drop sensitive free-text fields and normalize values for JSON logging."""

    sanitized: dict[str, Any] = {}
    for key, value in fields.items():
        if _is_sensitive_field_name(key):
            continue
        sanitized[key] = _normalize_telemetry_value(value)
    return sanitized


@dataclass(slots=True)
class TelemetryEmitter:
    """Emit structured telemetry events through the application logger."""

    logger: logging.Logger = field(default_factory=lambda: get_logger("app.telemetry"))

    def emit(self, event: str, **fields: Any) -> None:
        """Emit a structured telemetry event."""

        payload = sanitize_telemetry_fields(fields)
        payload["event"] = event
        self.logger.info(event, extra=payload)

    def counter(self, name: str, value: int = 1, **fields: Any) -> None:
        """Emit a counter-style telemetry event."""

        self.emit(
            "chat.metric",
            metric_name=name,
            metric_type="counter",
            metric_value=value,
            **fields,
        )


@dataclass(slots=True)
class ChatTelemetry:
    """Helper for emitting chat pipeline observability events."""

    emitter: TelemetryEmitter = field(default_factory=TelemetryEmitter)

    @contextmanager
    def track_request(self, **fields: Any) -> Iterator[None]:
        """Emit end-to-end request latency telemetry."""

        start = perf_counter()
        try:
            yield
        except Exception as exc:
            self.record_request(
                duration_ms=_elapsed_ms(start),
                status="error",
                error_type=type(exc).__name__,
                **fields,
            )
            raise
        else:
            self.record_request(duration_ms=_elapsed_ms(start), status="success", **fields)

    @contextmanager
    def track_retrieval(self, **fields: Any) -> Iterator[None]:
        """Emit retrieval stage latency telemetry and misses."""

        start = perf_counter()
        try:
            yield
        except Exception as exc:
            self.record_retrieval(
                duration_ms=_elapsed_ms(start),
                status="error",
                error_type=type(exc).__name__,
                **fields,
            )
            raise
        else:
            self.record_retrieval(duration_ms=_elapsed_ms(start), status="success", **fields)

    @contextmanager
    def track_generation(self, **fields: Any) -> Iterator[None]:
        """Emit generation stage latency telemetry and provider failures."""

        start = perf_counter()
        try:
            yield
        except Exception as exc:
            self.record_generation(
                duration_ms=_elapsed_ms(start),
                status="error",
                error_type=type(exc).__name__,
                **fields,
            )
            raise
        else:
            self.record_generation(duration_ms=_elapsed_ms(start), status="success", **fields)

    def record_request(
        self,
        *,
        duration_ms: float,
        status: str,
        **fields: Any,
    ) -> None:
        """Emit end-to-end request telemetry."""

        self.emitter.emit(
            "chat.request",
            duration_ms=round(duration_ms, 3),
            status=status,
            **fields,
        )

    def record_retrieval(
        self,
        *,
        duration_ms: float,
        status: str,
        retrieval_result_count: int = 0,
        retrieval_candidate_count: int = 0,
        retrieval_used_count: int = 0,
        error_type: str | None = None,
        **fields: Any,
    ) -> None:
        """Emit retrieval stage telemetry and retrieval misses."""

        retrieval_miss = retrieval_result_count == 0
        self.emitter.emit(
            "chat.retrieval",
            stage="retrieval",
            duration_ms=round(duration_ms, 3),
            status=status,
            retrieval_candidate_count=retrieval_candidate_count,
            retrieval_result_count=retrieval_result_count,
            retrieval_used_count=retrieval_used_count,
            retrieval_miss=retrieval_miss,
            error_type=error_type,
            **fields,
        )
        if status == "success" and retrieval_miss:
            self.emitter.counter("chat.retrieval_miss", error_type=error_type, **fields)

    def record_generation(
        self,
        *,
        duration_ms: float,
        status: str,
        provider: str | None = None,
        model: str | None = None,
        error_type: str | None = None,
        **fields: Any,
    ) -> None:
        """Emit generation stage telemetry and provider/model failures."""

        self.emitter.emit(
            "chat.generation",
            stage="generation",
            duration_ms=round(duration_ms, 3),
            status=status,
            provider=provider,
            model=model,
            error_type=error_type,
            **fields,
        )
        if status == "error":
            self.emitter.counter(
                "chat.model_failure",
                provider=provider,
                model=model,
                error_type=error_type,
                **fields,
            )

    def record_insufficient_evidence(self, **fields: Any) -> None:
        """Emit insufficient-evidence fallback telemetry."""

        self.emitter.emit(
            "chat.insufficient_evidence",
            insufficient_evidence=True,
            **fields,
        )
        self.emitter.counter(
            "chat.insufficient_evidence_fallback",
            insufficient_evidence=True,
            **fields,
        )

    def record_response(
        self,
        *,
        citation_count: int,
        citation_opportunity_count: int,
        insufficient_evidence: bool = False,
        **fields: Any,
    ) -> None:
        """Emit per-response citation grounding telemetry."""

        self.emitter.emit(
            "chat.response",
            citation_count=citation_count,
            citation_opportunity_count=citation_opportunity_count,
            citation_coverage=compute_citation_coverage(
                citation_count=citation_count,
                citation_opportunity_count=citation_opportunity_count,
            ),
            insufficient_evidence=insufficient_evidence,
            **fields,
        )


def _elapsed_ms(start: float) -> float:
    """Return elapsed milliseconds from a perf-counter start point."""

    return (perf_counter() - start) * 1000


def _is_sensitive_field_name(name: str) -> bool:
    """Return whether the telemetry field name is sensitive."""

    normalized_name = name.lower()
    return normalized_name in SENSITIVE_FIELD_NAMES or normalized_name.endswith(
        (
            "_content",
            "_messages",
            "_post_body",
            "_post_text",
            "_prompt",
            "_response_text",
            "_snippet",
            "_snippet_text",
            "_text",
        )
    )


def _normalize_telemetry_value(value: Any) -> Any:
    """Return a JSON-safe structured telemetry value."""

    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC).isoformat()
        return value.astimezone(UTC).isoformat()
    if isinstance(value, BaseException):
        return type(value).__name__
    if isinstance(value, Mapping):
        return sanitize_telemetry_fields({str(key): item for key, item in value.items()})
    if isinstance(value, _SEQUENCE_TYPES):
        return [_normalize_telemetry_value(item) for item in value]
    return str(value)
