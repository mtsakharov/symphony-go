"""Pytest fixtures."""

from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.endpoints.chat import get_chat_service
from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.database import models as database_models  # noqa: F401
from app.database.base import Base
from app.database.session import get_db_session
from app.main import create_app


@pytest.fixture
def db_session_factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    """Return a session factory backed by a temporary SQLite database."""

    database_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def app(db_session_factory: sessionmaker[Session]) -> FastAPI:
    """Return a configured FastAPI application for tests."""

    application = create_app()

    def override_get_db_session() -> Iterator[Session]:
        with db_session_factory() as session:
            yield session

    application.dependency_overrides[get_db_session] = override_get_db_session
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Return an async HTTP client bound to the test application."""

    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as async_client,
    ):
        yield async_client


@pytest.fixture
def override_chat_dependencies(
    app: FastAPI,
) -> Iterator[Callable[[Any, str], None]]:
    """Override chat dependencies for a test and clean up afterward."""

    def _override(service: Any, user_id: str = "user-123") -> None:
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id=user_id)
        app.dependency_overrides[get_chat_service] = lambda: service

    try:
        yield _override
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_chat_service, None)
