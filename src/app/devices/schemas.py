"""Pydantic schemas for device endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

DeviceIdentifierField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=255),
]
DeviceSecretField = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class DeviceCreate(BaseModel):
    """Payload for registering a device."""

    identifier: DeviceIdentifierField
    secret: DeviceSecretField


class DeviceResponse(BaseModel):
    """Serialized device returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
