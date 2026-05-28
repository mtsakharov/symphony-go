"""Integration tests for role endpoints."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.api.v1.test_permissions import create_permission


async def create_role(
    client: AsyncClient,
    *,
    name: str = "admin",
    description: str | None = "Administrators",
    permission_ids: list[str] | None = None,
) -> dict[str, object]:
    """Create a role through the API and return the response payload."""

    response = await client.post(
        "/api/v1/roles",
        json={
            "name": name,
            "description": description,
            "permission_ids": permission_ids or [],
        },
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


@pytest.mark.asyncio
async def test_create_role_returns_created_role_with_permissions(client: AsyncClient) -> None:
    """Creating a role should return the serialized entity."""

    permission = await create_permission(client)
    payload = await create_role(client, permission_ids=[cast(str, permission["id"])])
    permissions = cast(list[dict[str, object]], payload["permissions"])

    assert payload["name"] == "admin"
    assert payload["description"] == "Administrators"
    assert len(permissions) == 1
    assert permissions[0]["id"] == permission["id"]
    assert "id" in payload


@pytest.mark.asyncio
async def test_create_role_rejects_duplicate_name(client: AsyncClient) -> None:
    """Creating a role with an existing name should fail with 409."""

    await create_role(client)

    response = await client.post(
        "/api/v1/roles",
        json={"name": "admin", "description": "Duplicate", "permission_ids": []},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Role with this name already exists"}


@pytest.mark.asyncio
async def test_create_role_rejects_unknown_permission_ids(client: AsyncClient) -> None:
    """Creating a role with missing permissions should fail with 404."""

    missing_id = str(uuid4())
    response = await client.post(
        "/api/v1/roles",
        json={"name": "admin", "description": "Administrators", "permission_ids": [missing_id]},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": f"Permissions not found: {missing_id}"}


@pytest.mark.asyncio
async def test_list_roles_returns_paginated_payload(client: AsyncClient) -> None:
    """Listing roles should include pagination metadata."""

    await create_role(client, name="admin")
    await create_role(client, name="editor")

    response = await client.get("/api/v1/roles", params={"page": 1, "limit": 1})

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert response.json()["limit"] == 1
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1


@pytest.mark.asyncio
async def test_get_role_by_id_returns_role(client: AsyncClient) -> None:
    """Fetching a role by id should return the record."""

    created_role = await create_role(client)

    response = await client.get(f"/api/v1/roles/{created_role['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created_role["id"]


@pytest.mark.asyncio
async def test_update_role_returns_updated_role(client: AsyncClient) -> None:
    """Updating a role should persist the requested changes."""

    first_permission = await create_permission(client, name="users.read")
    second_permission = await create_permission(client, name="users.write")
    created_role = await create_role(client, permission_ids=[cast(str, first_permission["id"])])

    response = await client.patch(
        f"/api/v1/roles/{created_role['id']}",
        json={
            "description": "Editors",
            "permission_ids": [cast(str, second_permission["id"])],
        },
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Editors"
    assert [permission["id"] for permission in response.json()["permissions"]] == [
        second_permission["id"]
    ]


@pytest.mark.asyncio
async def test_delete_role_removes_role(client: AsyncClient) -> None:
    """Deleting a role should remove it from later reads."""

    created_role = await create_role(client)

    delete_response = await client.delete(f"/api/v1/roles/{created_role['id']}")
    get_response = await client.get(f"/api/v1/roles/{created_role['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Role deleted successfully"}
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Role not found"}
