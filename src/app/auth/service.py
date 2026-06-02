"""Service layer for authentication flows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.exceptions import InvalidCredentialsError, PrincipalInactiveError
from app.auth.schemas import DeviceTokenRequest, TokenResponse, UserTokenRequest
from app.auth.security import create_access_token, verify_secret
from app.devices.repository import DeviceRepository
from app.users.repository import UserRepository


class AuthService:
    """Business logic for issuing JWTs to users and devices."""

    def __init__(
        self,
        *,
        user_repository: UserRepository | None = None,
        device_repository: DeviceRepository | None = None,
    ) -> None:
        self.user_repository = user_repository or UserRepository()
        self.device_repository = device_repository or DeviceRepository()

    def authenticate_user(self, session: Session, payload: UserTokenRequest) -> TokenResponse:
        """Validate a user's credentials and return a bearer token."""

        user = self.user_repository.get_by_email(session, str(payload.email))
        if user is None or not verify_secret(payload.password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_active:
            raise PrincipalInactiveError("User account is inactive")

        access_token, expires_in = create_access_token(subject=str(user.id), subject_type="user")
        return TokenResponse(access_token=access_token, expires_in=expires_in)

    def authenticate_device(self, session: Session, payload: DeviceTokenRequest) -> TokenResponse:
        """Validate device credentials and return a bearer token."""

        device = self.device_repository.get_by_identifier(session, payload.identifier)
        if device is None or not verify_secret(payload.secret, device.secret_hash):
            raise InvalidCredentialsError("Invalid device identifier or secret")
        if not device.is_active:
            raise PrincipalInactiveError("Device is inactive")

        access_token, expires_in = create_access_token(
            subject=str(device.id),
            subject_type="device",
        )
        return TokenResponse(access_token=access_token, expires_in=expires_in)
