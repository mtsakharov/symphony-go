"""Application lifespan management."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from time import monotonic

from fastapi import FastAPI

from app.core.config import Settings
from app.core.logging import get_logger, setup_logging
from app.database.session import get_session_factory
from app.media.repository import MediaRepository
from app.media.service import MediaCleanupService
from app.media.storage import LocalMediaStorage

LOGGER = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI, settings: Settings) -> AsyncIterator[None]:
    """Manage application startup and shutdown events."""

    setup_logging(settings.debug)
    app.state.started_at_monotonic = monotonic()
    app.state.ready = True
    cleanup_task = _start_media_cleanup_task(app, settings)
    LOGGER.info("Application startup completed.")
    try:
        yield
    finally:
        if cleanup_task is not None:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task
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


def _start_media_cleanup_task(app: FastAPI, settings: Settings) -> asyncio.Task[None] | None:
    """Start the optional background cleanup loop."""

    if settings.media_cleanup_interval_seconds <= 0:
        return None

    storage = LocalMediaStorage(storage_dir=Path(settings.media_storage_dir))
    service = MediaCleanupService(
        repository=MediaRepository(),
        storage=storage,
        settings=settings,
    )
    session_factory = get_session_factory()

    async def _run_loop() -> None:
        while True:
            try:
                with session_factory() as session:
                    service.run_once(session)
            except Exception:
                LOGGER.error("Background media cleanup sweep failed", exc_info=True)
            await asyncio.sleep(settings.media_cleanup_interval_seconds)

    task = asyncio.create_task(_run_loop(), name="media-cleanup-sweeper")
    app.state.media_cleanup_task = task
    return task
