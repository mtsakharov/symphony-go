"""Pytest fixtures."""

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
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
def app(
    db_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[FastAPI]:
    """Return a configured FastAPI application for tests."""

    monkeypatch.setenv("MEDIA_STORAGE_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("MEDIA_MAX_SIZE_BYTES", "1024")
    get_settings.cache_clear()
    application = create_app()

    def override_get_db_session() -> Iterator[Session]:
        with db_session_factory() as session:
            yield session

    application.dependency_overrides[get_db_session] = override_get_db_session
    yield application
    get_settings.cache_clear()


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
