"""Health check endpoints."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.lifespan import get_uptime_seconds, is_application_ready

router = APIRouter()


class LivenessResponse(BaseModel):
    """Response model for the liveness probe."""

    status: Literal["ok"]
    timestamp: datetime


class ComponentStatus(BaseModel):
    """Health details for a single service component."""

    name: str
    status: Literal["healthy", "degraded", "unhealthy"]
    latency_ms: float | None = None
    details: str | None = None


class ReadinessResponse(BaseModel):
    """Response model for the readiness probe."""

    status: Literal["ready", "not_ready"]
    version: str
    uptime_seconds: float = Field(ge=0)
    timestamp: datetime
    components: list[ComponentStatus]


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Check service liveness",
    description="Returns whether the FastAPI process is alive and able to answer requests.",
    tags=["Health"],
    operation_id="getLivenessProbe",
)
async def get_liveness() -> LivenessResponse:
    """Return a liveness status for the running process."""

    return LivenessResponse(status="ok", timestamp=datetime.now(UTC))


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "Service not ready"}},
    summary="Check service readiness",
    description=(
        "Returns whether the service is ready to accept traffic and component health details."
    ),
    tags=["Health"],
    operation_id="getReadinessProbe",
)
async def get_readiness(request: Request, response: Response) -> ReadinessResponse:
    """Return readiness information for the application."""

    settings = get_settings()
    ready = is_application_ready(request.app)
    components = [
        ComponentStatus(
            name="application",
            status="healthy" if ready else "unhealthy",
            latency_ms=0.0,
            details=(
                "FastAPI application startup completed."
                if ready
                else "Application startup incomplete."
            ),
        )
    ]
    payload = ReadinessResponse(
        status="ready" if ready else "not_ready",
        version=settings.app_version,
        uptime_seconds=get_uptime_seconds(request.app),
        timestamp=datetime.now(UTC),
        components=components,
    )
    if payload.status != "ready":
        response.status_code = 503
    return payload
