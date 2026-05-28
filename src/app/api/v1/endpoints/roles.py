"""Roles CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.access.exceptions import (
    PermissionNotFoundError,
    RoleConflictError,
    RoleNotFoundError,
)
from app.access.schemas import (
    DeleteRoleResponse,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
)
from app.access.service import RoleService
from app.database.session import get_db_session

router = APIRouter()


def get_role_service() -> RoleService:
    """Return a roles service instance."""

    return RoleService()


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create role",
    description="Create a new role with a unique name and linked permissions.",
    operation_id="createRole",
)
def create_role(
    payload: RoleCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RoleService, Depends(get_role_service)],
) -> RoleResponse:
    """Create a role."""

    try:
        return service.create_role(session, payload)
    except RoleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PermissionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "",
    response_model=RoleListResponse,
    summary="List roles",
    description="Return a paginated list of roles.",
    operation_id="listRoles",
)
def list_roles(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RoleService, Depends(get_role_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> RoleListResponse:
    """List roles."""

    return service.list_roles(session, page=page, limit=limit)


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Get role",
    description="Return a role by id.",
    operation_id="getRoleById",
)
def get_role(
    role_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RoleService, Depends(get_role_service)],
) -> RoleResponse:
    """Get a role by id."""

    try:
        return service.get_role(session, role_id)
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Update role",
    description="Apply partial updates to a role.",
    operation_id="updateRole",
)
def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RoleService, Depends(get_role_service)],
) -> RoleResponse:
    """Update a role."""

    try:
        return service.update_role(session, role_id, payload)
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RoleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PermissionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{role_id}",
    response_model=DeleteRoleResponse,
    summary="Delete role",
    description="Delete a role by id.",
    operation_id="deleteRole",
)
def delete_role(
    role_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RoleService, Depends(get_role_service)],
) -> DeleteRoleResponse:
    """Delete a role."""

    try:
        service.delete_role(session, role_id)
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DeleteRoleResponse(message="Role deleted successfully")
