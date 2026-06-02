"""Unit tests for the auth service and token helpers."""

from __future__ import annotations

from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.auth.exceptions import InvalidCredentialsError, InvalidTokenError, PrincipalInactiveError
from app.auth.schemas import DeviceTokenRequest, UserTokenRequest
from app.auth.security import create_access_token, decode_access_token, hash_secret
from app.auth.service import AuthService
from app.devices.models import Device
from app.devices.repository import DeviceRepository
from app.users.models import User
from app.users.repository import UserRepository


def build_user(*, email: str = "user@example.com", is_active: bool = True) -> User:
    """Return a user with a hashed password for auth tests."""

    return User(
        id=uuid4(),
        email=email,
        first_name="John",
        last_name="Doe",
        password_hash=hash_secret("password123"),
        is_active=is_active,
    )


def build_device(*, identifier: str = "device-001", is_active: bool = True) -> Device:
    """Return a device with a hashed secret for auth tests."""

    return Device(
        id=uuid4(),
        identifier=identifier,
        secret_hash=hash_secret("device-secret"),
        is_active=is_active,
    )


def test_authenticate_user_returns_token_for_valid_credentials() -> None:
    """Service should return a signed token for a valid user login."""

    repository = Mock(spec=UserRepository)
    user = build_user()
    repository.get_by_email.return_value = user
    service = AuthService(user_repository=repository)

    response = service.authenticate_user(
        Mock(),
        UserTokenRequest(email="user@example.com", password="password123"),
    )

    claims = decode_access_token(response.access_token)
    assert response.token_type == "bearer"
    assert response.expires_in == 3600
    assert claims.sub == str(user.id)
    assert claims.subject_type == "user"


@pytest.mark.parametrize(
    ("email", "password"),
    [("missing@example.com", "password123"), ("user@example.com", "wrongpass")],
)
def test_authenticate_user_rejects_unknown_email_or_wrong_password(
    email: str,
    password: str,
) -> None:
    """Service should reject invalid user credentials."""

    repository = Mock(spec=UserRepository)
    repository.get_by_email.return_value = build_user() if email == "user@example.com" else None
    service = AuthService(user_repository=repository)

    with pytest.raises(InvalidCredentialsError, match="Invalid email or password"):
        service.authenticate_user(Mock(), UserTokenRequest(email=email, password=password))


def test_authenticate_user_rejects_inactive_user() -> None:
    """Service should reject inactive users after credential verification."""

    repository = Mock(spec=UserRepository)
    repository.get_by_email.return_value = build_user(is_active=False)
    service = AuthService(user_repository=repository)

    with pytest.raises(PrincipalInactiveError, match="User account is inactive"):
        service.authenticate_user(
            Mock(),
            UserTokenRequest(email="user@example.com", password="password123"),
        )


def test_authenticate_device_returns_token_for_valid_credentials() -> None:
    """Service should return a signed token for a valid device login."""

    repository = Mock(spec=DeviceRepository)
    device = build_device()
    repository.get_by_identifier.return_value = device
    service = AuthService(device_repository=repository)

    response = service.authenticate_device(
        Mock(),
        DeviceTokenRequest(identifier="device-001", secret="device-secret"),
    )

    claims = decode_access_token(response.access_token)
    assert response.token_type == "bearer"
    assert response.expires_in == 3600
    assert claims.sub == str(device.id)
    assert claims.subject_type == "device"


@pytest.mark.parametrize(
    ("identifier", "secret"),
    [("missing-device", "device-secret"), ("device-001", "wrongpass")],
)
def test_authenticate_device_rejects_unknown_identifier_or_wrong_secret(
    identifier: str,
    secret: str,
) -> None:
    """Service should reject invalid device credentials."""

    repository = Mock(spec=DeviceRepository)
    repository.get_by_identifier.return_value = (
        build_device() if identifier == "device-001" else None
    )
    service = AuthService(device_repository=repository)

    with pytest.raises(InvalidCredentialsError, match="Invalid device identifier or secret"):
        service.authenticate_device(
            Mock(),
            DeviceTokenRequest(identifier=identifier, secret=secret),
        )


def test_authenticate_device_rejects_inactive_device() -> None:
    """Service should reject inactive devices after credential verification."""

    repository = Mock(spec=DeviceRepository)
    repository.get_by_identifier.return_value = build_device(is_active=False)
    service = AuthService(device_repository=repository)

    with pytest.raises(PrincipalInactiveError, match="Device is inactive"):
        service.authenticate_device(
            Mock(),
            DeviceTokenRequest(identifier="device-001", secret="device-secret"),
        )


def test_decode_access_token_rejects_invalid_token() -> None:
    """Token decoding should reject malformed payloads."""

    with pytest.raises(InvalidTokenError, match="Token is invalid"):
        decode_access_token("not-a-jwt")


def test_decode_access_token_rejects_expired_token() -> None:
    """Token decoding should reject expired JWTs."""

    token, _ = create_access_token(
        subject=str(uuid4()),
        subject_type="user",
        expires_in_seconds=-1,
    )

    with pytest.raises(InvalidTokenError, match="Token has expired"):
        decode_access_token(token)
