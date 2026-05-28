"""Users CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.users.exceptions import UserEmailConflictError, UserNotFoundError
from app.users.schemas import (
    DeleteUserResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserStatusUpdate,
    UserUpdate,
)
from app.users.service import UserService

router = APIRouter()


def get_user_service() -> UserService:
    """Return a users service instance."""

    return UserService()


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user with a unique email address.",
    operation_id="createUser",
)
def create_user(
    payload: UserCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Create a user."""

    try:
        return service.create_user(session, payload)
    except UserEmailConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users",
    description="Return a paginated list of users.",
    operation_id="listUsers",
)
def list_users(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[UserService, Depends(get_user_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> UserListResponse:
    """List users."""

    return service.list_users(session, page=page, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user",
    description="Return a user by id.",
    operation_id="getUserById",
)
def get_user(
    user_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Get a user by id."""

    try:
        return service.get_user(session, user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="Update user status",
    description="Update the active status of a user.",
    operation_id="updateUserStatus",
)
def update_user_status(
    user_id: UUID,
    payload: UserStatusUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Update a user's active status."""

    try:
        return service.update_user_status(session, user_id, payload)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Apply partial updates to a user.",
    operation_id="updateUser",
)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Update a user."""

    try:
        return service.update_user(session, user_id, payload)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UserEmailConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete(
    "/{user_id}",
    response_model=DeleteUserResponse,
    summary="Delete user",
    description="Delete a user by id.",
    operation_id="deleteUser",
)
def delete_user(
    user_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> DeleteUserResponse:
    """Delete a user."""

    try:
        service.delete_user(session, user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DeleteUserResponse(message="User deleted successfully")
