"""Integration tests for user endpoints."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def create_user(
    client: AsyncClient,
    *,
    email: str = "user@example.com",
    first_name: str = "John",
    last_name: str = "Doe",
) -> dict[str, object]:
    """Create a user through the API and return the response payload."""

    response = await client.post(
        "/api/v1/users",
        json={"email": email, "first_name": first_name, "last_name": last_name},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


@pytest.mark.asyncio
async def test_create_user_returns_created_user(client: AsyncClient) -> None:
    """Creating a user should return the serialized entity."""

    payload = await create_user(client)

    assert payload["email"] == "user@example.com"
    assert payload["first_name"] == "John"
    assert payload["last_name"] == "Doe"
    assert payload["is_active"] is True
    assert "id" in payload
    assert "created_at" in payload
    assert "updated_at" in payload


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email(client: AsyncClient) -> None:
    """Creating a user with an existing email should fail with 409."""

    await create_user(client)

    response = await client.post(
        "/api/v1/users",
        json={"email": "user@example.com", "first_name": "Jane", "last_name": "Doe"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "User with this email already exists"}


@pytest.mark.asyncio
async def test_list_users_returns_paginated_payload(client: AsyncClient) -> None:
    """Listing users should include pagination metadata."""

    await create_user(client, email="john@example.com", first_name="John", last_name="Doe")
    await create_user(client, email="jane@example.com", first_name="Jane", last_name="Doe")

    response = await client.get("/api/v1/users", params={"page": 1, "limit": 1})

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert response.json()["limit"] == 1
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1


@pytest.mark.asyncio
async def test_get_user_feed_returns_newest_users_first(client: AsyncClient) -> None:
    """The user feed should expose paginated users ordered by newest first."""

    first_user = await create_user(client, email="first@example.com", first_name="First")
    second_user = await create_user(client, email="second@example.com", first_name="Second")

    response = await client.get("/api/v1/users/feed", params={"page": 1, "limit": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["limit"] == 2
    assert payload["total"] == 2
    assert [item["id"] for item in payload["items"]] == [second_user["id"], first_user["id"]]


@pytest.mark.asyncio
async def test_get_user_by_id_returns_user(client: AsyncClient) -> None:
    """Fetching a user by id should return the record."""

    created_user = await create_user(client)

    response = await client.get(f"/api/v1/users/{created_user['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created_user["id"]


@pytest.mark.asyncio
async def test_get_user_by_id_returns_not_found(client: AsyncClient) -> None:
    """Fetching a missing user should return 404."""

    response = await client.get(f"/api/v1/users/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


@pytest.mark.asyncio
async def test_update_user_returns_updated_user(client: AsyncClient) -> None:
    """Updating a user should persist the requested changes."""

    created_user = await create_user(client)

    response = await client.patch(
        f"/api/v1/users/{created_user['id']}",
        json={"first_name": "Jane", "is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Jane"
    assert response.json()["last_name"] == "Doe"
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_user_rejects_duplicate_email(client: AsyncClient) -> None:
    """Updating a user to an existing email should fail with 409."""

    first_user = await create_user(client, email="first@example.com")
    await create_user(client, email="second@example.com")

    response = await client.patch(
        f"/api/v1/users/{first_user['id']}",
        json={"email": "second@example.com"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "User with this email already exists"}


@pytest.mark.asyncio
async def test_delete_user_removes_user(client: AsyncClient) -> None:
    """Deleting a user should remove it from later reads."""

    created_user = await create_user(client)

    delete_response = await client.delete(f"/api/v1/users/{created_user['id']}")
    get_response = await client.get(f"/api/v1/users/{created_user['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "User deleted successfully"}
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_openapi_schema_includes_user_feed_endpoint(client: AsyncClient) -> None:
    """OpenAPI should advertise the user feed endpoint."""

    response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/users/feed" in schema["paths"]
    assert schema["paths"]["/api/v1/users/feed"]["get"]["operationId"] == "getUserFeed"
