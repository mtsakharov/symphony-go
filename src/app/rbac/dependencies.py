"""RBAC-backed authentication and authorization dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.rbac.exceptions import RbacUserNotFoundError
from app.rbac.service import RbacService

ACTOR_HEADER_NAME = "X-User-Id"
ACTOR_SECURITY_SCHEME_NAME = "XUserIdHeader"

actor_header = APIKeyHeader(
    name=ACTOR_HEADER_NAME,
    scheme_name=ACTOR_SECURITY_SCHEME_NAME,
    description="UUID of the acting user performing the request.",
    auto_error=False,
)

AUTH_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Missing or invalid X-User-Id request header."},
    403: {"description": "The acting user lacks the required permission."},
}


@dataclass(frozen=True)
class AuthenticatedActor:
    """Authenticated request actor and their effective permissions."""

    user_id: UUID
    permissions: frozenset[str]


def get_rbac_service() -> RbacService:
    """Return an RBAC service instance."""

    return RbacService()


def require_permission(
    permission: str,
    *,
    allow_bootstrap_if_no_users: bool = False,
) -> Callable[..., AuthenticatedActor | None]:
    """Return a dependency that enforces a specific permission."""

    def dependency(
        session: Annotated[Session, Depends(get_db_session)],
        service: Annotated[RbacService, Depends(get_rbac_service)],
        actor_id_header: Annotated[str | None, Security(actor_header)],
    ) -> AuthenticatedActor | None:
        if allow_bootstrap_if_no_users and service.repository.count_users(session) == 0:
            return None

        service.ensure_seed_data(session)

        if actor_id_header is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"{ACTOR_HEADER_NAME} header is required",
            )

        try:
            actor_id = UUID(actor_id_header)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"{ACTOR_HEADER_NAME} header must be a valid UUID",
            ) from exc

        try:
            permissions = service.get_effective_permission_codes(session, actor_id)
        except RbacUserNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated user not found",
            ) from exc

        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )

        return AuthenticatedActor(user_id=actor_id, permissions=frozenset(permissions))

    return dependency
