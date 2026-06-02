"""Integration tests for auth endpoints."""

from __future__ import annotations

from typing import cast

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.auth.security import decode_access_token
from app.devices.models import Device


async def create_user(
    client: AsyncClient,
    *,
    email: str = "user@example.com",
    password: str = "password123",
) -> dict[str, object]:
    """Create a user to authenticate in tests."""

    response = await client.post(
        "/api/v1/users",
        json={
            "email": email,
            "first_name": "John",
            "last_name": "Doe",
            "password": password,
        },
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def create_device(
    client: AsyncClient,
    *,
    identifier: str = "device-001",
    secret: str = "device-secret",
) -> dict[str, object]:
    """Register a device to authenticate in tests."""

    response = await client.post(
        "/api/v1/devices",
        json={"identifier": identifier, "secret": secret},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


@pytest.mark.asyncio
async def test_create_user_token_returns_bearer_token(client: AsyncClient) -> None:
    """Authenticating a user should return a bearer token payload."""

    user = await create_user(client)

    response = await client.post(
        "/api/v1/auth/users/token",
        json={"email": "user@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    payload = response.json()
    claims = decode_access_token(payload["access_token"])
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 3600
    assert claims.sub == user["id"]
    assert claims.subject_type == "user"


@pytest.mark.asyncio
async def test_create_user_token_rejects_invalid_credentials(client: AsyncClient) -> None:
    """Authenticating with a wrong password should fail with 401."""

    await create_user(client)

    response = await client.post(
        "/api/v1/auth/users/token",
        json={"email": "user@example.com", "password": "wrongpass"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


@pytest.mark.asyncio
async def test_create_user_token_rejects_inactive_user(client: AsyncClient) -> None:
    """Authenticating an inactive user should fail with 403."""

    user = await create_user(client)
    patch_response = await client.patch(f"/api/v1/users/{user['id']}", json={"is_active": False})
    assert patch_response.status_code == 200

    response = await client.post(
        "/api/v1/auth/users/token",
        json={"email": "user@example.com", "password": "password123"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "User account is inactive"}


@pytest.mark.asyncio
async def test_create_device_token_returns_bearer_token(client: AsyncClient) -> None:
    """Authenticating a device should return a bearer token payload."""

    device = await create_device(client)

    response = await client.post(
        "/api/v1/auth/devices/token",
        json={"identifier": "device-001", "secret": "device-secret"},
    )

    assert response.status_code == 200
    payload = response.json()
    claims = decode_access_token(payload["access_token"])
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 3600
    assert claims.sub == device["id"]
    assert claims.subject_type == "device"


@pytest.mark.asyncio
async def test_create_device_token_rejects_invalid_credentials(client: AsyncClient) -> None:
    """Authenticating with a wrong device secret should fail with 401."""

    await create_device(client)

    response = await client.post(
        "/api/v1/auth/devices/token",
        json={"identifier": "device-001", "secret": "wrongpass"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid device identifier or secret"}


@pytest.mark.asyncio
async def test_create_device_token_rejects_inactive_device(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """Authenticating an inactive device should fail with 403."""

    await create_device(client)

    with db_session_factory() as session:
        device = session.execute(
            select(Device).where(Device.identifier == "device-001")
        ).scalar_one()
        device.is_active = False
        session.add(device)
        session.commit()

    response = await client.post(
        "/api/v1/auth/devices/token",
        json={"identifier": "device-001", "secret": "device-secret"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Device is inactive"}
