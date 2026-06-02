"""Application lifespan management."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic

from fastapi import FastAPI

from app.chat.session_store import InMemorySessionContextStore
from app.core.config import Settings
from app.core.logging import get_logger, setup_logging

LOGGER = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI, settings: Settings) -> AsyncIterator[None]:
    """Manage application startup and shutdown events."""

    setup_logging(settings.debug)
    app.state.started_at_monotonic = monotonic()
    app.state.session_context_store = InMemorySessionContextStore(
        max_turns=settings.chat_session_max_turns
    )
    app.state.ready = True
    LOGGER.info("Application startup completed.")
    try:
        yield
    finally:
        app.state.ready = False
        LOGGER.info("Application shutdown completed.")


def get_uptime_seconds(app: FastAPI) -> float:
    """Return the application uptime in seconds."""

    started_at = getattr(app.state, "started_at_monotonic", None)
    if started_at is None:
        return 0.0
    return round(monotonic() - float(started_at), 6)


def is_application_ready(app: FastAPI) -> bool:
    """Return whether the application is ready to serve traffic."""

    return bool(getattr(app.state, "ready", False))
