"""Integration tests for permission endpoints."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def create_permission(
    client: AsyncClient,
    *,
    name: str = "users.read",
    description: str | None = "Read users",
) -> dict[str, object]:
    """Create a permission through the API and return the response payload."""

    response = await client.post(
        "/api/v1/permissions",
        json={"name": name, "description": description},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


@pytest.mark.asyncio
async def test_create_permission_returns_created_permission(client: AsyncClient) -> None:
    """Creating a permission should return the serialized entity."""

    payload = await create_permission(client)

    assert payload["name"] == "users.read"
    assert payload["description"] == "Read users"
    assert "id" in payload
    assert "created_at" in payload
    assert "updated_at" in payload


@pytest.mark.asyncio
async def test_create_permission_rejects_duplicate_name(client: AsyncClient) -> None:
    """Creating a permission with an existing name should fail with 409."""

    await create_permission(client)

    response = await client.post(
        "/api/v1/permissions",
        json={"name": "users.read", "description": "Duplicate"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Permission with this name already exists"}


@pytest.mark.asyncio
async def test_list_permissions_returns_paginated_payload(client: AsyncClient) -> None:
    """Listing permissions should include pagination metadata."""

    await create_permission(client, name="users.read")
    await create_permission(client, name="users.write")

    response = await client.get("/api/v1/permissions", params={"page": 1, "limit": 1})

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert response.json()["limit"] == 1
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1


@pytest.mark.asyncio
async def test_get_permission_by_id_returns_permission(client: AsyncClient) -> None:
    """Fetching a permission by id should return the record."""

    created_permission = await create_permission(client)

    response = await client.get(f"/api/v1/permissions/{created_permission['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created_permission["id"]


@pytest.mark.asyncio
async def test_update_permission_returns_updated_permission(client: AsyncClient) -> None:
    """Updating a permission should persist the requested changes."""

    created_permission = await create_permission(client)

    response = await client.patch(
        f"/api/v1/permissions/{created_permission['id']}",
        json={"description": "Read user records"},
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Read user records"


@pytest.mark.asyncio
async def test_delete_permission_removes_permission(client: AsyncClient) -> None:
    """Deleting a permission should remove it from later reads."""

    created_permission = await create_permission(client)

    delete_response = await client.delete(f"/api/v1/permissions/{created_permission['id']}")
    get_response = await client.get(f"/api/v1/permissions/{created_permission['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Permission deleted successfully"}
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Permission not found"}


@pytest.mark.asyncio
async def test_get_permission_by_id_returns_not_found(client: AsyncClient) -> None:
    """Fetching a missing permission should return 404."""

    response = await client.get(f"/api/v1/permissions/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Permission not found"}
