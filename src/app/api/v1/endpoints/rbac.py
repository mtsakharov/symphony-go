"""RBAC management endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.rbac.dependencies import AUTH_ERROR_RESPONSES, get_rbac_service, require_permission
from app.rbac.exceptions import (
    PermissionNotFoundError,
    RbacUserNotFoundError,
    RoleNameConflictError,
    RoleNotFoundError,
    RolePermissionConflictError,
    RolePermissionNotFoundAssignmentError,
    UserRoleConflictError,
    UserRoleNotFoundAssignmentError,
)
from app.rbac.schemas import (
    DeleteRoleResponse,
    PermissionListResponse,
    RoleCreate,
    RoleListResponse,
    RolePermissionAssign,
    RoleResponse,
    RoleUpdate,
    UserRoleAssign,
    UserRoleListResponse,
)
from app.rbac.service import RbacService

router = APIRouter()


@router.get(
    "/permissions",
    response_model=PermissionListResponse,
    summary="List permissions",
    description="Return the full RBAC permission catalogue.",
    operation_id="listRbacPermissions",
    responses=AUTH_ERROR_RESPONSES,
)
def list_permissions(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _actor: Annotated[object, Depends(require_permission("rbac:read"))],
) -> PermissionListResponse:
    """List RBAC permissions."""

    return service.list_permissions(session)


@router.get(
    "/roles",
    response_model=RoleListResponse,
    summary="List roles",
    description="Return all RBAC roles with their permissions.",
    operation_id="listRbacRoles",
    responses=AUTH_ERROR_RESPONSES,
)
def list_roles(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _actor: Annotated[object, Depends(require_permission("rbac:read"))],
) -> RoleListResponse:
    """List RBAC roles."""

    return service.list_roles(session)


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create role",
    description="Create a new RBAC role.",
    operation_id="createRbacRole",
    responses=AUTH_ERROR_RESPONSES | {409: {"description": "Role name already exists."}},
)
def create_role(
    payload: RoleCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _actor: Annotated[object, Depends(require_permission("rbac:write"))],
) -> RoleResponse:
    """Create an RBAC role."""

    try:
        return service.create_role(session, payload)
    except RoleNameConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Get role",
    description="Return a role by id.",
    operation_id="getRbacRoleById",
    responses=AUTH_ERROR_RESPONSES | {404: {"description": "Role not found."}},
)
def get_role(
    role_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _actor: Annotated[object, Depends(require_permission("rbac:read"))],
) -> RoleResponse:
    """Get a single RBAC role."""

    try:
        return service.get_role(session, role_id)
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Update role",
    description="Apply partial updates to an RBAC role.",
    operation_id="updateRbacRole",
    responses=AUTH_ERROR_RESPONSES
    | {
        404: {"description": "Role not found."},
        409: {"description": "Role name already exists."},
    },
)
def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _actor: Annotated[object, Depends(require_permission("rbac:write"))],
) -> RoleResponse:
    """Update an RBAC role."""

    try:
        return service.update_role(session, role_id, payload)
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RoleNameConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete(
    "/roles/{role_id}",
    response_model=DeleteRoleResponse,
    summary="Delete role",
    description="Delete an RBAC role.",
    operation_id="deleteRbacRole",
    responses=AUTH_ERROR_RESPONSES | {404: {"description": "Role not found."}},
)
def delete_role(
    role_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _actor: Annotated[object, Depends(require_permission("rbac:write"))],
) -> DeleteRoleResponse:
    """Delete an RBAC role."""

    try:
        service.delete_role(session, role_id)
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DeleteRoleResponse(message="Role deleted successfully")


@router.post(
    "/roles/{role_id}/permissions",
    response_model=RoleResponse,
    summary="Assign role permission",
    description="Assign an existing permission to a role.",
    operation_id="assignPermissionToRole",
    responses=AUTH_ERROR_RESPONSES
    | {
        404: {"description": "Role or permission not found."},
        409: {"description": "Permission is already assigned to this role."},
    },
)
def assign_permission_to_role(
    role_id: UUID,
    payload: RolePermissionAssign,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _actor: Annotated[object, Depends(require_permission("rbac:write"))],
) -> RoleResponse:
    """Assign a permission to a role."""

    try:
        return service.assign_permission_to_role(session, role_id, payload.permission_id)
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RolePermissionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
    response_model=RoleResponse,
    summary="Remove role permission",
    description="Remove a permission assignment from a role.",
    operation_id="removePermissionFromRole",
    responses=AUTH_ERROR_RESPONSES
    | {
        404: {"description": "Role or assignment not found."},
    },
)
def remove_permission_from_role(
    role_id: UUID,
    permission_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _actor: Annotated[object, Depends(require_permission("rbac:write"))],
) -> RoleResponse:
    """Remove a permission from a role."""

    try:
        return service.remove_permission_from_role(session, role_id, permission_id)
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RolePermissionNotFoundAssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/users/{user_id}/roles",
    response_model=UserRoleListResponse,
    summary="List user roles",
    description="Return the roles assigned to a user.",
    operation_id="listUserRoles",
    responses=AUTH_ERROR_RESPONSES | {404: {"description": "User not found."}},
)
def list_user_roles(
    user_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _actor: Annotated[object, Depends(require_permission("rbac:read"))],
) -> UserRoleListResponse:
    """List roles assigned to a user."""

    try:
        return service.list_user_roles(session, user_id)
    except RbacUserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/users/{user_id}/roles",
    response_model=UserRoleListResponse,
    summary="Assign user role",
    description="Assign a role to a user.",
    operation_id="assignRoleToUser",
    responses=AUTH_ERROR_RESPONSES
    | {
        404: {"description": "User or role not found."},
        409: {"description": "Role is already assigned to this user."},
    },
)
def assign_role_to_user(
    user_id: UUID,
    payload: UserRoleAssign,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _actor: Annotated[object, Depends(require_permission("rbac:write"))],
) -> UserRoleListResponse:
    """Assign a role to a user."""

    try:
        return service.assign_role_to_user(session, user_id, payload.role_id)
    except RbacUserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UserRoleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    response_model=UserRoleListResponse,
    summary="Remove user role",
    description="Remove a role assignment from a user.",
    operation_id="removeRoleFromUser",
    responses=AUTH_ERROR_RESPONSES
    | {
        404: {"description": "User, role, or assignment not found."},
    },
)
def remove_role_from_user(
    user_id: UUID,
    role_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _actor: Annotated[object, Depends(require_permission("rbac:write"))],
) -> UserRoleListResponse:
    """Remove a role from a user."""

    try:
        return service.remove_role_from_user(session, user_id, role_id)
    except RbacUserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UserRoleNotFoundAssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
