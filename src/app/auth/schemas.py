"""Pydantic schemas for auth endpoints and token claims."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, StringConstraints

PasswordField = Annotated[str, StringConstraints(min_length=8, max_length=128)]
DeviceIdentifierField = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=255),
]
DeviceSecretField = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class UserTokenRequest(BaseModel):
    """Payload for user/password authentication."""

    email: EmailStr
    password: PasswordField


class DeviceTokenRequest(BaseModel):
    """Payload for device/secret authentication."""

    identifier: DeviceIdentifierField
    secret: DeviceSecretField


class TokenResponse(BaseModel):
    """Serialized bearer token response."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class TokenClaims(BaseModel):
    """Validated JWT claims used by the application."""

    sub: str
    subject_type: Literal["user", "device"]
    iat: int
    exp: int
