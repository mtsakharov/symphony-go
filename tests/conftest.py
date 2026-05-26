"""Pytest fixtures."""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app() -> FastAPI:
    """Return a configured FastAPI application for tests."""

    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Return an async HTTP client bound to the test application."""

    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app), AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as async_client:
        yield async_client
