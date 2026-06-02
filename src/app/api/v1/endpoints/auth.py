"""JWT authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_auth_service
from app.auth.exceptions import InvalidCredentialsError, PrincipalInactiveError
from app.auth.schemas import DeviceTokenRequest, TokenResponse, UserTokenRequest
from app.auth.service import AuthService
from app.database.session import get_db_session

router = APIRouter()


def _unauthorized(detail: str) -> HTTPException:
    """Return a standard 401 auth error."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/users/token",
    response_model=TokenResponse,
    summary="Create user access token",
    description="Authenticate a user with email and password and return a bearer token.",
    operation_id="createUserAccessToken",
)
def create_user_access_token(
    payload: UserTokenRequest,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate a user and return a JWT."""

    try:
        return service.authenticate_user(session, payload)
    except InvalidCredentialsError as exc:
        raise _unauthorized(str(exc)) from exc
    except PrincipalInactiveError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post(
    "/devices/token",
    response_model=TokenResponse,
    summary="Create device access token",
    description=(
        "Authenticate a device with its identifier and shared secret and return a bearer token."
    ),
    operation_id="createDeviceAccessToken",
)
def create_device_access_token(
    payload: DeviceTokenRequest,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate a device and return a JWT."""

    try:
        return service.authenticate_device(session, payload)
    except InvalidCredentialsError as exc:
        raise _unauthorized(str(exc)) from exc
    except PrincipalInactiveError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
