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
async def test_list_users_returns_paginated_payload_across_pages(client: AsyncClient) -> None:
    """Listing users should return deterministic page slices with pagination metadata."""

    await create_user(client, email="john@example.com", first_name="John", last_name="Doe")
    await create_user(client, email="jane@example.com", first_name="Jane", last_name="Doe")
    await create_user(client, email="alex@example.com", first_name="Alex", last_name="Doe")

    first_page_response = await client.get("/api/v1/users", params={"page": 1, "limit": 2})
    second_page_response = await client.get("/api/v1/users", params={"page": 2, "limit": 2})

    assert first_page_response.status_code == 200
    assert first_page_response.json()["page"] == 1
    assert first_page_response.json()["limit"] == 2
    assert first_page_response.json()["total"] == 3
    assert [item["email"] for item in first_page_response.json()["items"]] == [
        "alex@example.com",
        "jane@example.com",
    ]

    assert second_page_response.status_code == 200
    assert second_page_response.json()["page"] == 2
    assert second_page_response.json()["limit"] == 2
    assert second_page_response.json()["total"] == 3
    assert [item["email"] for item in second_page_response.json()["items"]] == [
        "john@example.com"
    ]


@pytest.mark.asyncio
async def test_list_users_returns_empty_items_for_out_of_range_page(client: AsyncClient) -> None:
    """Listing users should return an empty page instead of an error."""

    await create_user(client, email="john@example.com")
    await create_user(client, email="jane@example.com")

    response = await client.get("/api/v1/users", params={"page": 3, "limit": 1})

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 3, "limit": 1, "total": 2}


@pytest.mark.asyncio
async def test_list_users_returns_empty_dataset_when_no_users_exist(client: AsyncClient) -> None:
    """Listing users should return an empty paginated envelope for a new database."""

    response = await client.get("/api/v1/users")

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "limit": 20, "total": 0}


@pytest.mark.asyncio
async def test_list_users_rejects_invalid_pagination_params(client: AsyncClient) -> None:
    """Listing users should validate page and limit boundaries."""

    invalid_page_response = await client.get("/api/v1/users", params={"page": 0})
    invalid_limit_response = await client.get("/api/v1/users", params={"limit": 0})
    excessive_limit_response = await client.get("/api/v1/users", params={"limit": 101})

    assert invalid_page_response.status_code == 422
    assert invalid_limit_response.status_code == 422
    assert excessive_limit_response.status_code == 422


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
async def test_openapi_schema_includes_user_pagination_contract(client: AsyncClient) -> None:
    """OpenAPI should advertise the paginated users list parameters and response."""

    response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    list_users_operation = schema["paths"]["/api/v1/users"]["get"]

    assert list_users_operation["operationId"] == "listUsers"
    assert {parameter["name"] for parameter in list_users_operation["parameters"]} == {
        "page",
        "limit",
    }
    assert (
        list_users_operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/UserListResponse"
    )
