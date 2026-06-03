"""Posts CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.posts.exceptions import PostAuthorNotFoundError, PostNotFoundError
from app.posts.models import PostStatus
from app.posts.schemas import (
    DeletePostResponse,
    ErrorResponse,
    PostCreate,
    PostListResponse,
    PostResponse,
    PostSortField,
    PostUpdate,
    SortOrder,
)
from app.posts.service import PostService

router = APIRouter()


def get_post_service() -> PostService:
    """Return a posts service instance."""

    return PostService()


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create post",
    description="Create a new post for an existing author.",
    operation_id="createPost",
    responses={
        status.HTTP_201_CREATED: {"description": "Post created successfully."},
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "The referenced author does not exist.",
        },
    },
)
def create_post(
    payload: Annotated[PostCreate, Body(description="Post creation payload.")],
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Create a post."""

    try:
        return service.create_post(session, payload)
    except PostAuthorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "",
    response_model=PostListResponse,
    summary="List posts",
    description=(
        "Return a paginated list of posts with optional filtering, search, and sorting. "
        "Requests beyond the available result set still return `200` with an empty `items` "
        "array and the matching `total` count."
    ),
    operation_id="listPosts",
)
def list_posts(
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
    page: Annotated[
        int,
        Query(
            ge=1,
            description=(
                "1-based page number. Pages beyond the available results return an empty "
                "`items` array."
            ),
        ),
    ] = 1,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Number of posts returned per page. Defaults to 20 and caps at 100.",
        ),
    ] = 20,
    status_filter: Annotated[
        PostStatus | None,
        Query(
            alias="status",
            description="Filter posts by publication status (`draft` or `published`).",
        ),
    ] = None,
    author_id: Annotated[UUID | None, Query(description="Filter posts by author id.")] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=255,
            description="Case-insensitive search across title and body.",
        ),
    ] = None,
    sort_by: Annotated[
        PostSortField,
        Query(
            description=(
                "Primary field used to sort the result set. Ties are resolved with the post "
                "`id` in the same direction as `sort_order`."
            ),
        ),
    ] = PostSortField.CREATED_AT,
    sort_order: Annotated[
        SortOrder,
        Query(description="Sort direction for the selected field."),
    ] = SortOrder.DESC,
) -> PostListResponse:
    """List posts."""

    return service.list_posts(
        session,
        page=page,
        limit=limit,
        status=status_filter,
        author_id=author_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="Get post",
    description="Return a post by id.",
    operation_id="getPostById",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "The requested post does not exist.",
        }
    },
)
def get_post(
    post_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Get a post by id."""

    try:
        return service.get_post(session, post_id)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
    summary="Update post",
    description="Apply partial updates to a post.",
    operation_id="updatePost",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "The referenced author does not exist.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "The requested post does not exist.",
        },
    },
)
def update_post(
    post_id: UUID,
    payload: Annotated[PostUpdate, Body(description="Partial post update payload.")],
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Update a post."""

    try:
        return service.update_post(session, post_id, payload)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PostAuthorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete(
    "/{post_id}",
    response_model=DeletePostResponse,
    summary="Delete post",
    description="Delete a post by id.",
    operation_id="deletePost",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "The requested post does not exist.",
        }
    },
)
def delete_post(
    post_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> DeletePostResponse:
    """Delete a post."""

    try:
        service.delete_post(session, post_id)
    except PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DeletePostResponse(message="Post deleted successfully")
