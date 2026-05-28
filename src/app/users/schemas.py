"""Pydantic schemas for user endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.access.schemas import PermissionResponse, RoleSummaryResponse

NameField = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
OptionalNameField = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]
    | None
)


class UserCreate(BaseModel):
    """Payload for creating a user."""

    email: EmailStr
    first_name: NameField
    last_name: NameField
    role_ids: list[UUID] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """Payload for updating a user."""

    email: EmailStr | None = None
    first_name: OptionalNameField = None
    last_name: OptionalNameField = None
    is_active: bool | None = None
    role_ids: list[UUID] | None = None


class UserResponse(BaseModel):
    """Serialized user returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    is_active: bool
    roles: list[RoleSummaryResponse]
    permissions: list[PermissionResponse]
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    """Paginated users list response."""

    items: list[UserResponse]
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)


class DeleteUserResponse(BaseModel):
    """Delete user response payload."""

    message: str
