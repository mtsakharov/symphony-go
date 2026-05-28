"""Integration tests for tag endpoints."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def create_tag(
    client: AsyncClient,
    *,
    name: str = "backend",
    description: str | None = "Backend-facing resources",
) -> dict[str, object]:
    """Create a tag through the API and return the response payload."""

    response = await client.post("/api/v1/tags", json={"name": name, "description": description})
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


@pytest.mark.asyncio
async def test_create_tag_returns_created_tag(client: AsyncClient) -> None:
    """Creating a tag should return the serialized entity."""

    payload = await create_tag(client)

    assert payload["name"] == "backend"
    assert payload["description"] == "Backend-facing resources"
    assert "id" in payload
    assert "created_at" in payload
    assert "updated_at" in payload


@pytest.mark.asyncio
async def test_create_tag_rejects_duplicate_name(client: AsyncClient) -> None:
    """Creating a tag with an existing name should fail with 409."""

    await create_tag(client)

    response = await client.post(
        "/api/v1/tags",
        json={"name": "backend", "description": "Duplicate"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Tag with this name already exists"}


@pytest.mark.asyncio
async def test_list_tags_returns_paginated_payload(client: AsyncClient) -> None:
    """Listing tags should include pagination metadata."""

    await create_tag(client, name="backend")
    await create_tag(client, name="frontend")

    response = await client.get("/api/v1/tags", params={"page": 1, "limit": 1})

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert response.json()["limit"] == 1
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1


@pytest.mark.asyncio
async def test_get_tag_by_id_returns_tag(client: AsyncClient) -> None:
    """Fetching a tag by id should return the record."""

    created_tag = await create_tag(client)

    response = await client.get(f"/api/v1/tags/{created_tag['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created_tag["id"]


@pytest.mark.asyncio
async def test_get_tag_by_id_returns_not_found(client: AsyncClient) -> None:
    """Fetching a missing tag should return 404."""

    response = await client.get(f"/api/v1/tags/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Tag not found"}


@pytest.mark.asyncio
async def test_update_tag_returns_updated_tag(client: AsyncClient) -> None:
    """Updating a tag should persist the requested changes."""

    created_tag = await create_tag(client)

    response = await client.patch(
        f"/api/v1/tags/{created_tag['id']}",
        json={"name": "api", "description": "API-facing resources"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "api"
    assert response.json()["description"] == "API-facing resources"


@pytest.mark.asyncio
async def test_update_tag_rejects_duplicate_name(client: AsyncClient) -> None:
    """Updating a tag to an existing name should fail with 409."""

    first_tag = await create_tag(client, name="backend")
    await create_tag(client, name="frontend")

    response = await client.patch(
        f"/api/v1/tags/{first_tag['id']}",
        json={"name": "frontend"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Tag with this name already exists"}


@pytest.mark.asyncio
async def test_delete_tag_removes_tag(client: AsyncClient) -> None:
    """Deleting a tag should remove it from later reads."""

    created_tag = await create_tag(client)

    delete_response = await client.delete(f"/api/v1/tags/{created_tag['id']}")
    get_response = await client.get(f"/api/v1/tags/{created_tag['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Tag deleted successfully"}
    assert get_response.status_code == 404
