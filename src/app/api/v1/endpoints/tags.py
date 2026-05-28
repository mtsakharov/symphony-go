"""Tags CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.tags.exceptions import TagConflictError, TagNotFoundError
from app.tags.schemas import DeleteTagResponse, TagCreate, TagListResponse, TagResponse, TagUpdate
from app.tags.service import TagService

router = APIRouter()


def get_tag_service() -> TagService:
    """Return a tags service instance."""

    return TagService()


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tag",
    description="Create a new tag with a unique name.",
    operation_id="createTag",
)
def create_tag(
    payload: TagCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> TagResponse:
    """Create a tag."""

    try:
        return service.create_tag(session, payload)
    except TagConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "",
    response_model=TagListResponse,
    summary="List tags",
    description="Return a paginated list of tags.",
    operation_id="listTags",
)
def list_tags(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[TagService, Depends(get_tag_service)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> TagListResponse:
    """List tags."""

    return service.list_tags(session, page=page, limit=limit)


@router.get(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Get tag",
    description="Return a tag by id.",
    operation_id="getTagById",
)
def get_tag(
    tag_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> TagResponse:
    """Get a tag by id."""

    try:
        return service.get_tag(session, tag_id)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Update tag",
    description="Apply partial updates to a tag.",
    operation_id="updateTag",
)
def update_tag(
    tag_id: UUID,
    payload: TagUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> TagResponse:
    """Update a tag."""

    try:
        return service.update_tag(session, tag_id, payload)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TagConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete(
    "/{tag_id}",
    response_model=DeleteTagResponse,
    summary="Delete tag",
    description="Delete a tag by id.",
    operation_id="deleteTag",
)
def delete_tag(
    tag_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[TagService, Depends(get_tag_service)],
) -> DeleteTagResponse:
    """Delete a tag."""

    try:
        service.delete_tag(session, tag_id)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DeleteTagResponse(message="Tag deleted successfully")
