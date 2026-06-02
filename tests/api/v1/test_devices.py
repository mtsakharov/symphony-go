"""Integration tests for device endpoints."""

from __future__ import annotations

from typing import cast

import pytest
from httpx import AsyncClient


async def create_device(
    client: AsyncClient,
    *,
    identifier: str = "device-001",
    secret: str = "device-secret",
) -> dict[str, object]:
    """Register a device and return the response payload."""

    response = await client.post(
        "/api/v1/devices",
        json={"identifier": identifier, "secret": secret},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


@pytest.mark.asyncio
async def test_create_device_returns_registered_device(client: AsyncClient) -> None:
    """Registering a device should return the serialized entity."""

    payload = await create_device(client)

    assert payload["identifier"] == "device-001"
    assert payload["is_active"] is True
    assert "id" in payload
    assert "created_at" in payload
    assert "updated_at" in payload
    assert "secret" not in payload
    assert "secret_hash" not in payload


@pytest.mark.asyncio
async def test_create_device_rejects_duplicate_identifier(client: AsyncClient) -> None:
    """Registering a device with an existing identifier should fail with 409."""

    await create_device(client)

    response = await client.post(
        "/api/v1/devices",
        json={"identifier": "device-001", "secret": "other-secret"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Device with this identifier already exists"}
