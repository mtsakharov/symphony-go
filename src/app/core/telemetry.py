"""Structured telemetry helpers for tweet request lifecycle observability."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger

SENSITIVE_FIELD_NAMES = frozenset(
    {
        "body",
        "clarification_answer",
        "clarification_response",
        "content",
        "draft",
        "draft_text",
        "message",
        "messages",
        "prompt",
        "response_text",
        "text",
        "tweet_body",
        "tweet_brief",
        "tweet_content",
        "tweet_text",
    }
)
_SEQUENCE_TYPES = (list, tuple, set, frozenset)


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
    """Emit structured telemetry through the application logger."""

    logger: logging.Logger = field(default_factory=lambda: get_logger("app.telemetry"))

    def emit(self, event: str, **fields: Any) -> None:
        """Emit a structured telemetry event."""

        payload = sanitize_telemetry_fields(fields)
        payload["event"] = event
        self.logger.info(event, extra=payload)

    def counter(self, name: str, value: int = 1, **fields: Any) -> None:
        """Emit a counter-style telemetry event."""

        self.emit(
            "tweet_request.metric",
            metric_name=name,
            metric_type="counter",
            metric_value=value,
            **fields,
        )


@dataclass(slots=True)
class TweetRequestTelemetry:
    """Emit tweet-request lifecycle telemetry and transition audit logs."""

    emitter: TelemetryEmitter = field(default_factory=TelemetryEmitter)

    def record_created(self, *, request_id: str, **fields: Any) -> None:
        """Emit request creation telemetry."""

        self.emitter.emit("tweet_request.created", request_id=request_id, **fields)
        self.emitter.counter("tweet_request.created", request_id=request_id, **fields)

    def record_clarification_loop(
        self,
        *,
        request_id: str,
        clarification_count: int,
        loop_state: str,
        **fields: Any,
    ) -> None:
        """Emit clarification-loop telemetry."""

        self.emitter.emit(
            "tweet_request.clarification_loop",
            request_id=request_id,
            clarification_count=clarification_count,
            loop_state=loop_state,
            **fields,
        )
        self.emitter.counter(
            "tweet_request.clarification_loop",
            request_id=request_id,
            clarification_count=clarification_count,
            loop_state=loop_state,
            **fields,
        )

    def record_readiness_evaluation(
        self,
        *,
        request_id: str,
        readiness_state: str,
        is_writable: bool,
        blocker_summary: str | None = None,
        blocker_codes: list[str] | None = None,
        **fields: Any,
    ) -> None:
        """Emit readiness evaluation telemetry."""

        self.emitter.emit(
            "tweet_request.readiness_evaluated",
            request_id=request_id,
            readiness_state=readiness_state,
            is_writable=is_writable,
            blocker_summary=blocker_summary,
            blocker_codes=blocker_codes or [],
            **fields,
        )
        self.emitter.counter(
            "tweet_request.readiness_evaluated",
            request_id=request_id,
            readiness_state=readiness_state,
            is_writable=is_writable,
            blocker_summary=blocker_summary,
            blocker_codes=blocker_codes or [],
            **fields,
        )
        if not is_writable:
            self.emitter.counter(
                "tweet_request.not_writable",
                request_id=request_id,
                readiness_state=readiness_state,
                blocker_summary=blocker_summary,
                blocker_codes=blocker_codes or [],
                **fields,
            )

    def record_drop_decision(
        self,
        *,
        request_id: str,
        drop_reason: str,
        blocker_summary: str | None = None,
        **fields: Any,
    ) -> None:
        """Emit drop-decision telemetry."""

        self.emitter.emit(
            "tweet_request.drop_decision",
            request_id=request_id,
            drop_reason=drop_reason,
            blocker_summary=blocker_summary,
            **fields,
        )
        self.emitter.counter(
            "tweet_request.drop_decision",
            request_id=request_id,
            drop_reason=drop_reason,
            blocker_summary=blocker_summary,
            **fields,
        )

    def record_compliance_blocked(
        self,
        *,
        request_id: str,
        blocked_transition: str,
        blocker_summary: str,
        blocker_codes: list[str] | None = None,
        **fields: Any,
    ) -> None:
        """Emit compliance-blocked telemetry."""

        self.emitter.emit(
            "tweet_request.compliance_blocked",
            request_id=request_id,
            blocked_transition=blocked_transition,
            blocker_summary=blocker_summary,
            blocker_codes=blocker_codes or [],
            **fields,
        )
        self.emitter.counter(
            "tweet_request.compliance_blocked",
            request_id=request_id,
            blocked_transition=blocked_transition,
            blocker_summary=blocker_summary,
            blocker_codes=blocker_codes or [],
            **fields,
        )

    def record_status_transition(
        self,
        *,
        request_id: str,
        from_status: str,
        to_status: str,
        blocker_summary: str | None = None,
        blocker_codes: list[str] | None = None,
        transition_reason: str | None = None,
        **fields: Any,
    ) -> None:
        """Emit an audit-style status transition log."""

        self.emitter.emit(
            "tweet_request.status_transition",
            request_id=request_id,
            from_status=from_status,
            to_status=to_status,
            blocker_summary=blocker_summary,
            blocker_codes=blocker_codes or [],
            transition_reason=transition_reason,
            audit_log=True,
            **fields,
        )


def _is_sensitive_field_name(name: str) -> bool:
    """Return whether the telemetry field name is sensitive."""

    normalized_name = name.lower()
    return normalized_name in SENSITIVE_FIELD_NAMES or normalized_name.endswith(
        (
            "_body",
            "_brief",
            "_clarification",
            "_content",
            "_draft",
            "_message",
            "_messages",
            "_prompt",
            "_response",
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
