"""Integration tests for post endpoints."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.api.v1.test_users import create_user

from app.posts.models import PostIndexRecord


async def create_post(
    client: AsyncClient,
    *,
    author_id: str,
    body: str = "Hello world",
    visibility: str = "public",
) -> dict[str, Any]:
    """Create a post through the API and return the response payload."""

    response = await client.post(
        "/api/v1/posts",
        json={"author_id": author_id, "body": body, "visibility": visibility},
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def get_index_record(
    db_session_factory: sessionmaker[Session],
    *,
    post_id: str,
) -> PostIndexRecord:
    """Return the single index record for a post."""

    with db_session_factory() as session:
        statement = select(PostIndexRecord).where(PostIndexRecord.post_id == UUID(post_id))
        return session.execute(statement).scalar_one()


@pytest.mark.asyncio
async def test_create_post_returns_created_post(client: AsyncClient) -> None:
    """Creating a post should return the serialized post and index state."""

    user = await create_user(client)

    payload = await create_post(client, author_id=cast(str, user["id"]))

    assert payload["author_id"] == user["id"]
    assert payload["body"] == "Hello world"
    assert payload["visibility"] == "public"
    assert payload["index_record"]["is_active"] is True


@pytest.mark.asyncio
async def test_update_post_visibility_invalidates_index_record(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Privacy changes should invalidate the current active index record."""

    user = await create_user(client)
    created = await create_post(client, author_id=cast(str, user["id"]))

    response = await client.patch(
        f"/api/v1/posts/{created['id']}",
        json={"visibility": "private"},
    )

    assert response.status_code == 200
    assert response.json()["visibility"] == "private"
    assert response.json()["index_record"]["is_active"] is False
    assert response.json()["index_record"]["invalidation_reason"] == "visibility_changed"

    record = get_index_record(db_session_factory, post_id=cast(str, created["id"]))
    assert record.is_active is False


@pytest.mark.asyncio
async def test_delete_post_invalidates_index_record(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Deleting a post should invalidate the corresponding index state."""

    user = await create_user(client)
    created = await create_post(client, author_id=cast(str, user["id"]))

    response = await client.delete(f"/api/v1/posts/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {"message": "Post deleted successfully"}

    record = get_index_record(db_session_factory, post_id=cast(str, created["id"]))
    assert record.is_active is False
    assert record.invalidation_reason == "post_deleted"
