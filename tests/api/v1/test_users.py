"""Integration tests for user endpoints."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from httpx import AsyncClient


def actor_headers(user_id: str) -> dict[str, str]:
    """Return request headers for an authenticated actor."""

    return {"X-User-Id": user_id}


async def create_user(
    client: AsyncClient,
    *,
    email: str = "user@example.com",
    first_name: str = "John",
    last_name: str = "Doe",
    actor_id: str | None = None,
) -> dict[str, object]:
    """Create a user through the API and return the response payload."""

    response = await client.post(
        "/api/v1/users",
        json={"email": email, "first_name": first_name, "last_name": last_name},
        headers=actor_headers(actor_id) if actor_id is not None else None,
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

    admin_user = await create_user(client)

    response = await client.post(
        "/api/v1/users",
        json={"email": "user@example.com", "first_name": "Jane", "last_name": "Doe"},
        headers=actor_headers(cast(str, admin_user["id"])),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "User with this email already exists"}


@pytest.mark.asyncio
async def test_list_users_returns_paginated_payload(client: AsyncClient) -> None:
    """Listing users should include pagination metadata."""

    admin_user = await create_user(client, email="admin@example.com")
    admin_id = cast(str, admin_user["id"])
    await create_user(
        client,
        email="john@example.com",
        first_name="John",
        last_name="Doe",
        actor_id=admin_id,
    )
    await create_user(
        client,
        email="jane@example.com",
        first_name="Jane",
        last_name="Doe",
        actor_id=admin_id,
    )

    response = await client.get(
        "/api/v1/users",
        params={"page": 1, "limit": 1},
        headers=actor_headers(admin_id),
    )

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert response.json()["limit"] == 1
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 1


@pytest.mark.asyncio
async def test_get_user_by_id_returns_user(client: AsyncClient) -> None:
    """Fetching a user by id should return the record."""

    admin_user = await create_user(client, email="admin@example.com")
    created_user = await create_user(
        client, email="member@example.com", actor_id=cast(str, admin_user["id"])
    )

    response = await client.get(
        f"/api/v1/users/{created_user['id']}",
        headers=actor_headers(cast(str, admin_user["id"])),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created_user["id"]


@pytest.mark.asyncio
async def test_get_user_by_id_returns_not_found(client: AsyncClient) -> None:
    """Fetching a missing user should return 404."""

    admin_user = await create_user(client, email="admin@example.com")

    response = await client.get(
        f"/api/v1/users/{uuid4()}",
        headers=actor_headers(cast(str, admin_user["id"])),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


@pytest.mark.asyncio
async def test_update_user_returns_updated_user(client: AsyncClient) -> None:
    """Updating a user should persist the requested changes."""

    admin_user = await create_user(client, email="admin@example.com")
    created_user = await create_user(
        client, email="member@example.com", actor_id=cast(str, admin_user["id"])
    )

    response = await client.patch(
        f"/api/v1/users/{created_user['id']}",
        json={"first_name": "Jane", "is_active": False},
        headers=actor_headers(cast(str, admin_user["id"])),
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Jane"
    assert response.json()["last_name"] == "Doe"
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_user_rejects_duplicate_email(client: AsyncClient) -> None:
    """Updating a user to an existing email should fail with 409."""

    admin_user = await create_user(client, email="admin@example.com")
    admin_id = cast(str, admin_user["id"])
    first_user = await create_user(client, email="first@example.com", actor_id=admin_id)
    await create_user(client, email="second@example.com", actor_id=admin_id)

    response = await client.patch(
        f"/api/v1/users/{first_user['id']}",
        json={"email": "second@example.com"},
        headers=actor_headers(admin_id),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "User with this email already exists"}


@pytest.mark.asyncio
async def test_delete_user_removes_user(client: AsyncClient) -> None:
    """Deleting a user should remove it from later reads."""

    admin_user = await create_user(client, email="admin@example.com")
    admin_id = cast(str, admin_user["id"])
    created_user = await create_user(client, email="member@example.com", actor_id=admin_id)

    delete_response = await client.delete(
        f"/api/v1/users/{created_user['id']}",
        headers=actor_headers(admin_id),
    )
    get_response = await client.get(
        f"/api/v1/users/{created_user['id']}",
        headers=actor_headers(admin_id),
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "User deleted successfully"}
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_protected_user_routes_require_actor_header(client: AsyncClient) -> None:
    """Protected user routes should require the actor header after bootstrap."""

    await create_user(client, email="admin@example.com")

    response = await client.get("/api/v1/users")

    assert response.status_code == 401
    assert response.json() == {"detail": "X-User-Id header is required"}


@pytest.mark.asyncio
async def test_user_routes_forbid_users_without_permission(client: AsyncClient) -> None:
    """Authenticated users without the permission should receive 403."""

    admin_user = await create_user(client, email="admin@example.com")
    regular_user = await create_user(
        client,
        email="member@example.com",
        actor_id=cast(str, admin_user["id"]),
    )

    response = await client.get(
        "/api/v1/users",
        headers=actor_headers(cast(str, regular_user["id"])),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing required permission: users:read"}


@pytest.mark.asyncio
async def test_first_user_bootstrap_assigns_admin_role(client: AsyncClient) -> None:
    """The first created user should be bootstrapped with the admin role."""

    first_user = await create_user(client, email="admin@example.com")

    response = await client.get(
        f"/api/v1/rbac/users/{first_user['id']}/roles",
        headers=actor_headers(cast(str, first_user["id"])),
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == first_user["id"]
    assert [role["name"] for role in response.json()["items"]] == ["admin"]
