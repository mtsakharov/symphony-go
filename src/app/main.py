"""Application entrypoint."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.lifespan import lifespan


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Production-ready FastAPI service exposing health checks, user "
            "management endpoints, posts CRUD APIs, and OpenAPI documentation."
        ),
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=_build_lifespan(settings),
        contact={
            "name": "Service Maintainers",
            "email": "maintainers@example.com",
        },
        license_info={
            "name": "MIT",
            "identifier": "MIT",
        },
        openapi_tags=[
            {
                "name": "Health",
                "description": "Operational health endpoints for liveness and readiness probes.",
            },
            {
                "name": "Users",
                "description": "CRUD operations for managing application users.",
            },
            {
                "name": "Posts",
                "description": "CRUD operations for managing draft and published posts.",
            },
        ],
    )
    app.include_router(api_router, prefix=_get_api_root_prefix(settings))
    app.openapi_schema = _build_openapi_schema(app, settings)
    return app


def run() -> None:
    """Run the FastAPI application with uvicorn."""

    settings = get_settings()
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


def _get_api_root_prefix(settings: Settings) -> str:
    """Return the root API prefix derived from the v1 prefix."""

    if settings.api_v1_prefix.endswith("/v1"):
        return settings.api_v1_prefix.removesuffix("/v1")
    return settings.api_v1_prefix


def _build_lifespan(
    settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Return a lifespan callable bound to the current settings."""

    def _lifespan(app: FastAPI) -> AbstractAsyncContextManager[None]:
        return lifespan(app, settings)

    return _lifespan


def _build_openapi_schema(app: FastAPI, settings: Settings) -> dict[str, Any]:
    """Build the OpenAPI schema for the application."""

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["servers"] = [
        {
            "url": f"http://{settings.host}:{settings.port}",
            "description": f"{settings.environment} environment",
        }
    ]
    schema["info"]["contact"] = {
        "name": "Service Maintainers",
        "email": "maintainers@example.com",
    }
    schema["info"]["license"] = {
        "name": "MIT",
        "identifier": "MIT",
    }
    schema["tags"] = [
        {
            "name": "Health",
            "description": "Operational health endpoints for liveness and readiness probes.",
        },
        {
            "name": "Users",
            "description": "CRUD operations for managing application users.",
        },
        {
            "name": "Posts",
            "description": "CRUD operations for managing draft and published posts.",
        },
    ]
    return schema
