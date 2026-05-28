"""Permissions CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.access.exceptions import PermissionConflictError, PermissionNotFoundError
from app.access.schemas import (
    DeletePermissionResponse,
    PermissionCreate,
    PermissionListResponse,
    PermissionResponse,
    PermissionUpdate,
)
from app.access.service import PermissionService
from app.database.session import get_db_session

router = APIRouter()


def get_permission_service() -> PermissionService:
    """Return a permissions service instance."""

    return PermissionService()


@router.post(
    "",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create permission",
    description="Create a new permission with a unique name.",
    operation_id="createPermission",
)
def create_permission(
    payload: PermissionCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PermissionService, Depends(get_permission_service)],
) -> PermissionResponse:
    """Create a permission."""

    try:
        return service.create_permission(session, payload)
    except PermissionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "",
    response_model=PermissionListResponse,
    summary="List permissions",
    description="Return a paginated list of permissions.",
    operation_id="listPermissions",
)
def list_permissions(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PermissionService, Depends(get_permission_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> PermissionListResponse:
    """List permissions."""

    return service.list_permissions(session, page=page, limit=limit)


@router.get(
    "/{permission_id}",
    response_model=PermissionResponse,
    summary="Get permission",
    description="Return a permission by id.",
    operation_id="getPermissionById",
)
def get_permission(
    permission_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PermissionService, Depends(get_permission_service)],
) -> PermissionResponse:
    """Get a permission by id."""

    try:
        return service.get_permission(session, permission_id)
    except PermissionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/{permission_id}",
    response_model=PermissionResponse,
    summary="Update permission",
    description="Apply partial updates to a permission.",
    operation_id="updatePermission",
)
def update_permission(
    permission_id: UUID,
    payload: PermissionUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PermissionService, Depends(get_permission_service)],
) -> PermissionResponse:
    """Update a permission."""

    try:
        return service.update_permission(session, permission_id, payload)
    except PermissionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete(
    "/{permission_id}",
    response_model=DeletePermissionResponse,
    summary="Delete permission",
    description="Delete a permission by id.",
    operation_id="deletePermission",
)
def delete_permission(
    permission_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PermissionService, Depends(get_permission_service)],
) -> DeletePermissionResponse:
    """Delete a permission."""

    try:
        service.delete_permission(session, permission_id)
    except PermissionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DeletePermissionResponse(message="Permission deleted successfully")
