"""Integration tests for RBAC endpoints."""

from __future__ import annotations

from typing import cast

from httpx import AsyncClient


def actor_headers(user_id: str) -> dict[str, str]:
    """Return request headers for an authenticated actor."""

    return {"X-User-Id": user_id}


async def bootstrap_admin(client: AsyncClient) -> dict[str, object]:
    """Create the first user, which becomes the bootstrap admin."""

    response = await client.post(
        "/api/v1/users",
        json={"email": "admin@example.com", "first_name": "Admin", "last_name": "User"},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def create_user_as_admin(
    client: AsyncClient,
    *,
    actor_id: str,
    email: str,
    first_name: str = "Member",
    last_name: str = "User",
) -> dict[str, object]:
    """Create a user using an authenticated admin actor."""

    response = await client.post(
        "/api/v1/users",
        json={"email": email, "first_name": first_name, "last_name": last_name},
        headers=actor_headers(actor_id),
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def create_role_as_admin(
    client: AsyncClient,
    *,
    actor_id: str,
    name: str,
    description: str,
) -> dict[str, object]:
    """Create an RBAC role using an authenticated admin actor."""

    response = await client.post(
        "/api/v1/rbac/roles",
        json={"name": name, "description": description},
        headers=actor_headers(actor_id),
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def test_list_permissions_returns_seeded_permissions(client: AsyncClient) -> None:
    """Listing permissions should return the seeded RBAC catalogue."""

    admin_user = await bootstrap_admin(client)

    response = await client.get(
        "/api/v1/rbac/permissions",
        headers=actor_headers(cast(str, admin_user["id"])),
    )

    assert response.status_code == 200
    permission_codes = {item["code"] for item in response.json()["items"]}
    assert permission_codes == {
        "rbac:read",
        "rbac:write",
        "users:create",
        "users:delete",
        "users:read",
        "users:update",
    }


async def test_role_crud_round_trip(client: AsyncClient) -> None:
    """RBAC role CRUD operations should succeed for an admin actor."""

    admin_user = await bootstrap_admin(client)
    admin_id = cast(str, admin_user["id"])

    created_role = await create_role_as_admin(
        client,
        actor_id=admin_id,
        name="auditor",
        description="Read-only audit access",
    )

    get_response = await client.get(
        f"/api/v1/rbac/roles/{created_role['id']}",
        headers=actor_headers(admin_id),
    )
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "auditor"

    patch_response = await client.patch(
        f"/api/v1/rbac/roles/{created_role['id']}",
        json={"description": "Updated description"},
        headers=actor_headers(admin_id),
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["description"] == "Updated description"

    delete_response = await client.delete(
        f"/api/v1/rbac/roles/{created_role['id']}",
        headers=actor_headers(admin_id),
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Role deleted successfully"}


async def test_assigning_duplicate_permission_to_role_returns_conflict(
    client: AsyncClient,
) -> None:
    """Assigning the same permission twice should return 409."""

    admin_user = await bootstrap_admin(client)
    admin_id = cast(str, admin_user["id"])
    created_role = await create_role_as_admin(
        client,
        actor_id=admin_id,
        name="operator",
        description="Operator role",
    )

    permissions_response = await client.get(
        "/api/v1/rbac/permissions",
        headers=actor_headers(admin_id),
    )
    permission_id = next(
        item["id"] for item in permissions_response.json()["items"] if item["code"] == "users:read"
    )

    first_assignment = await client.post(
        f"/api/v1/rbac/roles/{created_role['id']}/permissions",
        json={"permission_id": permission_id},
        headers=actor_headers(admin_id),
    )
    assert first_assignment.status_code == 200
    assert [permission["code"] for permission in first_assignment.json()["permissions"]] == [
        "users:read"
    ]

    duplicate_assignment = await client.post(
        f"/api/v1/rbac/roles/{created_role['id']}/permissions",
        json={"permission_id": permission_id},
        headers=actor_headers(admin_id),
    )
    assert duplicate_assignment.status_code == 409
    assert duplicate_assignment.json() == {"detail": "Permission is already assigned to this role"}

    removal_response = await client.delete(
        f"/api/v1/rbac/roles/{created_role['id']}/permissions/{permission_id}",
        headers=actor_headers(admin_id),
    )
    assert removal_response.status_code == 200
    assert removal_response.json()["permissions"] == []


async def test_assigning_duplicate_role_to_user_returns_conflict(client: AsyncClient) -> None:
    """Assigning the same role twice should return 409."""

    admin_user = await bootstrap_admin(client)
    admin_id = cast(str, admin_user["id"])
    member_user = await create_user_as_admin(
        client,
        actor_id=admin_id,
        email="member@example.com",
    )
    created_role = await create_role_as_admin(
        client,
        actor_id=admin_id,
        name="support",
        description="Support role",
    )

    first_assignment = await client.post(
        f"/api/v1/rbac/users/{member_user['id']}/roles",
        json={"role_id": created_role["id"]},
        headers=actor_headers(admin_id),
    )
    assert first_assignment.status_code == 200
    assert [role["name"] for role in first_assignment.json()["items"]] == ["support"]

    duplicate_assignment = await client.post(
        f"/api/v1/rbac/users/{member_user['id']}/roles",
        json={"role_id": created_role["id"]},
        headers=actor_headers(admin_id),
    )
    assert duplicate_assignment.status_code == 409
    assert duplicate_assignment.json() == {"detail": "Role is already assigned to this user"}

    removal_response = await client.delete(
        f"/api/v1/rbac/users/{member_user['id']}/roles/{created_role['id']}",
        headers=actor_headers(admin_id),
    )
    assert removal_response.status_code == 200
    assert removal_response.json()["items"] == []


async def test_rbac_routes_forbid_users_without_permission(client: AsyncClient) -> None:
    """RBAC routes should reject authenticated users without RBAC permissions."""

    admin_user = await bootstrap_admin(client)
    regular_user = await create_user_as_admin(
        client,
        actor_id=cast(str, admin_user["id"]),
        email="member@example.com",
    )

    response = await client.get(
        "/api/v1/rbac/roles",
        headers=actor_headers(cast(str, regular_user["id"])),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing required permission: rbac:read"}


async def test_openapi_schema_exposes_rbac_security_metadata(client: AsyncClient) -> None:
    """OpenAPI should advertise RBAC paths, tag metadata, and auth requirements."""

    response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    assert "/api/v1/rbac/permissions" in schema["paths"]
    assert "/api/v1/rbac/roles" in schema["paths"]
    assert "/api/v1/rbac/users/{user_id}/roles" in schema["paths"]
    assert any(tag["name"] == "RBAC" for tag in schema["tags"])
    assert schema["components"]["securitySchemes"]["XUserIdHeader"]["type"] == "apiKey"
    assert schema["components"]["securitySchemes"]["XUserIdHeader"]["name"] == "X-User-Id"

    list_users_operation = schema["paths"]["/api/v1/users"]["get"]
    assert list_users_operation["security"] == [{"XUserIdHeader": []}]
    assert "401" in list_users_operation["responses"]
    assert "403" in list_users_operation["responses"]

    list_roles_operation = schema["paths"]["/api/v1/rbac/roles"]["get"]
    assert list_roles_operation["security"] == [{"XUserIdHeader": []}]
    assert "401" in list_roles_operation["responses"]
    assert "403" in list_roles_operation["responses"]
