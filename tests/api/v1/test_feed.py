"""Integration tests for user feed endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session, sessionmaker
from tests.api.v1.test_users import create_user

from app.feed.models import FeedItem


def seed_feed_item(
    db_session_factory: sessionmaker[Session],
    *,
    user_id: UUID,
    title: str,
    body: str,
    created_at: datetime,
) -> FeedItem:
    """Persist a feed item directly for integration tests."""

    item = FeedItem(
        id=uuid4(),
        user_id=user_id,
        title=title,
        body=body,
        created_at=created_at,
    )
    with db_session_factory() as session:
        session.add(item)
        session.commit()
    return item


@pytest.mark.asyncio
async def test_list_user_feed_returns_empty_page_for_existing_user(client: AsyncClient) -> None:
    """Existing users should receive an empty feed payload when no items exist."""

    created_user = await create_user(client)

    response = await client.get(f"/api/v1/users/{created_user['id']}/feed")

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "limit": 20, "total": 0}


@pytest.mark.asyncio
async def test_list_user_feed_returns_items_in_newest_first_order(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Feed items should be ordered newest-first and respect pagination."""

    created_user = await create_user(client)
    user_id = UUID(str(created_user["id"]))
    base_time = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    oldest = seed_feed_item(
        db_session_factory,
        user_id=user_id,
        title="Oldest",
        body="First event",
        created_at=base_time,
    )
    middle = seed_feed_item(
        db_session_factory,
        user_id=user_id,
        title="Middle",
        body="Second event",
        created_at=base_time + timedelta(minutes=1),
    )
    newest = seed_feed_item(
        db_session_factory,
        user_id=user_id,
        title="Newest",
        body="Third event",
        created_at=base_time + timedelta(minutes=2),
    )

    response = await client.get(
        f"/api/v1/users/{created_user['id']}/feed",
        params={"page": 1, "limit": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["limit"] == 2
    assert payload["total"] == 3
    assert [item["id"] for item in payload["items"]] == [str(newest.id), str(middle.id)]
    assert str(oldest.id) not in [item["id"] for item in payload["items"]]


@pytest.mark.asyncio
async def test_list_user_feed_returns_not_found_for_missing_user(client: AsyncClient) -> None:
    """Missing users should return 404."""

    response = await client.get(f"/api/v1/users/{uuid4()}/feed")

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


@pytest.mark.asyncio
async def test_openapi_exposes_feed_endpoint_and_tag(client: AsyncClient) -> None:
    """OpenAPI should document the feed path and tag."""

    response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert "/api/v1/users/{user_id}/feed" in payload["paths"]
    assert any(tag["name"] == "Feed" for tag in payload["tags"])
