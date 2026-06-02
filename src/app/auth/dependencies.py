"""Authentication dependencies for API endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Authenticated API principal."""

    user_id: str


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    """Resolve the authenticated user from a bearer JWT."""

    if credentials is None:
        raise _build_unauthorized_error("Authentication required")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.auth_jwt_secret,
            algorithms=[settings.auth_jwt_algorithm],
            audience=settings.auth_jwt_audience,
            issuer=settings.auth_jwt_issuer,
            options={"verify_aud": settings.auth_jwt_audience is not None},
        )
    except jwt.InvalidTokenError as exc:
        raise _build_unauthorized_error("Invalid authentication credentials") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise _build_unauthorized_error("Invalid authentication credentials")

    return AuthenticatedUser(user_id=subject)


def _build_unauthorized_error(message: str) -> HTTPException:
    """Return a stable 401 response payload."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_error_detail("unauthorized", message),
        headers={"WWW-Authenticate": "Bearer"},
    )


def _error_detail(code: str, message: str) -> dict[str, Any]:
    """Return a structured API error payload."""

    return {"code": code, "message": message}
