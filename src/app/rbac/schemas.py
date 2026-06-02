"""Pydantic schemas for RBAC endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

RoleNameField = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
DescriptionField = (
    Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)] | None
)


class PermissionResponse(BaseModel):
    """Serialized permission returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    description: str
    created_at: datetime
    updated_at: datetime


class PermissionListResponse(BaseModel):
    """List of available permissions."""

    items: list[PermissionResponse]


class RoleCreate(BaseModel):
    """Payload for creating a role."""

    name: RoleNameField
    description: DescriptionField = None


class RoleUpdate(BaseModel):
    """Payload for updating a role."""

    name: RoleNameField | None = None
    description: DescriptionField = None


class RoleResponse(BaseModel):
    """Serialized role returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    permissions: list[PermissionResponse] = Field(default_factory=list)


class RoleListResponse(BaseModel):
    """List of RBAC roles."""

    items: list[RoleResponse]


class DeleteRoleResponse(BaseModel):
    """Delete role response payload."""

    message: str


class RolePermissionAssign(BaseModel):
    """Payload for assigning a permission to a role."""

    permission_id: UUID


class UserRoleAssign(BaseModel):
    """Payload for assigning a role to a user."""

    role_id: UUID


class UserRoleListResponse(BaseModel):
    """List of roles assigned to a user."""

    user_id: UUID
    items: list[RoleResponse]
