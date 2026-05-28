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
    role_ids: list[str] | None = None,
) -> dict[str, object]:
    """Create a user through the API and return the response payload."""

    response = await client.post(
        "/api/v1/users",
        json={
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role_ids": role_ids or [],
        },
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
    assert payload["roles"] == []
    assert payload["permissions"] == []
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
async def test_create_user_includes_assigned_roles_and_permissions(client: AsyncClient) -> None:
    """Creating a user with roles should expose assigned roles and effective permissions."""

    permission_response = await client.post(
        "/api/v1/permissions",
        json={"name": "users.read", "description": "Read users"},
    )
    permission = cast(dict[str, object], permission_response.json())
    role_response = await client.post(
        "/api/v1/roles",
        json={
            "name": "admin",
            "description": "Administrators",
            "permission_ids": [permission["id"]],
        },
    )
    role = cast(dict[str, object], role_response.json())

    payload = await create_user(client, role_ids=[cast(str, role["id"])])
    roles = cast(list[dict[str, object]], payload["roles"])
    permissions = cast(list[dict[str, object]], payload["permissions"])

    assert [item["name"] for item in roles] == ["admin"]
    assert [item["name"] for item in permissions] == ["users.read"]


@pytest.mark.asyncio
async def test_update_user_replaces_assigned_roles(client: AsyncClient) -> None:
    """Updating a user should replace the assigned roles when role_ids are supplied."""

    permission_one = await client.post(
        "/api/v1/permissions",
        json={"name": "users.read", "description": "Read users"},
    )
    permission_two = await client.post(
        "/api/v1/permissions",
        json={"name": "users.write", "description": "Write users"},
    )
    role_one = await client.post(
        "/api/v1/roles",
        json={
            "name": "viewer",
            "description": "Viewers",
            "permission_ids": [permission_one.json()["id"]],
        },
    )
    role_two = await client.post(
        "/api/v1/roles",
        json={
            "name": "editor",
            "description": "Editors",
            "permission_ids": [permission_two.json()["id"]],
        },
    )
    created_user = await create_user(client, role_ids=[role_one.json()["id"]])

    response = await client.patch(
        f"/api/v1/users/{created_user['id']}",
        json={"role_ids": [role_two.json()["id"]]},
    )

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["roles"]] == ["editor"]
    assert [item["name"] for item in response.json()["permissions"]] == ["users.write"]


@pytest.mark.asyncio
async def test_create_user_rejects_unknown_role_ids(client: AsyncClient) -> None:
    """Creating a user with missing roles should fail with 404."""

    missing_id = str(uuid4())
    response = await client.post(
        "/api/v1/users",
        json={
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role_ids": [missing_id],
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": f"Roles not found: {missing_id}"}


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
