"""Pydantic schemas for role and permission endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NameField = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
OptionalNameField = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]
    | None
)
DescriptionField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
OptionalDescriptionField = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    ]
    | None
)


class PermissionCreate(BaseModel):
    """Payload for creating a permission."""

    name: NameField
    description: OptionalDescriptionField = None


class PermissionUpdate(BaseModel):
    """Payload for updating a permission."""

    name: OptionalNameField = None
    description: OptionalDescriptionField = None


class PermissionResponse(BaseModel):
    """Serialized permission returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class PermissionListResponse(BaseModel):
    """Paginated permissions list response."""

    items: list[PermissionResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)


class DeletePermissionResponse(BaseModel):
    """Delete permission response payload."""

    message: str


class RoleSummaryResponse(BaseModel):
    """Serialized role summary used in nested responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None


class RoleCreate(BaseModel):
    """Payload for creating a role."""

    name: NameField
    description: OptionalDescriptionField = None
    permission_ids: list[UUID] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Payload for updating a role."""

    name: OptionalNameField = None
    description: OptionalDescriptionField = None
    permission_ids: list[UUID] | None = None


class RoleResponse(BaseModel):
    """Serialized role returned by the API."""

    id: UUID
    name: str
    description: str | None
    permissions: list[PermissionResponse]
    created_at: datetime
    updated_at: datetime


class RoleListResponse(BaseModel):
    """Paginated roles list response."""

    items: list[RoleResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)


class DeleteRoleResponse(BaseModel):
    """Delete role response payload."""

    message: str
