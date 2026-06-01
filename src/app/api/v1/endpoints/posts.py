"""Post creation endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.posts.exceptions import MediaAssetNotFoundError, PostValidationError
from app.posts.schemas import PostCreate, PostResponse
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
    description="Create a text, image, or video post from uploaded media assets.",
    operation_id="createPost",
)
def create_post(
    payload: PostCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    """Create a post."""

    try:
        return service.create_post(session, payload)
    except MediaAssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PostValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
