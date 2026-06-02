"""Service layer for posts."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.posts.exceptions import PostAuthorNotFoundError, PostIndexSyncError, PostNotFoundError
from app.posts.index_sync import PostIndexSyncService
from app.posts.models import Post, PostIndexRecord
from app.posts.repository import PostIndexRecordRepository, PostRepository
from app.posts.schemas import (
    PostCreate,
    PostIndexRecordResponse,
    PostResponse,
    PostUpdate,
    PostWithIndexResponse,
)
from app.users.repository import UserRepository


@dataclass(slots=True)
class PostService:
    """Business logic for post CRUD operations and index synchronization."""

    repository: PostRepository = field(default_factory=PostRepository)
    user_repository: UserRepository = field(default_factory=UserRepository)
    index_repository: PostIndexRecordRepository = field(default_factory=PostIndexRecordRepository)
    index_sync_service: PostIndexSyncService = field(default_factory=PostIndexSyncService)
    logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.logger = get_logger(__name__)

    def create_post(self, session: Session, payload: PostCreate) -> PostWithIndexResponse:
        """Create a new post and synchronize index state."""

        self._ensure_author_exists(session, payload.author_id)
        post = Post(
            author_id=payload.author_id,
            body=payload.body,
            visibility=payload.visibility.value,
        )

        try:
            self.repository.create(session, post=post)
            self._sync_post_change(
                session,
                post=post,
                operation="create",
                invalidation_reason="post_not_indexable",
            )
            session.commit()
        except Exception:
            session.rollback()
            raise

        session.refresh(post)
        return self.get_post(session, post.id)

    def get_post(self, session: Session, post_id: UUID) -> PostWithIndexResponse:
        """Return a single post and its current index state."""

        post = self.repository.get_by_id(session, post_id)
        if post is None:
            raise PostNotFoundError("Post not found")

        index_record = self.index_repository.get_by_post_and_user(
            session,
            post_id=post.id,
            user_id=post.author_id,
        )
        return PostWithIndexResponse(
            **PostResponse.model_validate(post).model_dump(),
            index_record=(
                None
                if index_record is None
                else self._serialize_index_record(index_record)
            ),
        )

    def update_post(
        self,
        session: Session,
        post_id: UUID,
        payload: PostUpdate,
    ) -> PostWithIndexResponse:
        """Apply partial updates to a post and refresh its index state."""

        post = self.repository.get_by_id(session, post_id)
        if post is None:
            raise PostNotFoundError("Post not found")

        visibility_changed = False
        body_changed = False

        if payload.body is not None and payload.body != post.body:
            post.body = payload.body
            body_changed = True

        if payload.visibility is not None and payload.visibility.value != post.visibility:
            post.visibility = payload.visibility.value
            visibility_changed = True

        if body_changed or visibility_changed:
            post.version += 1

        try:
            session.add(post)
            session.flush()
            self._sync_post_change(
                session,
                post=post,
                operation="privacy_change" if visibility_changed else "update",
                invalidation_reason=(
                    "visibility_changed" if visibility_changed else "post_not_indexable"
                ),
            )
            session.commit()
        except Exception:
            session.rollback()
            raise

        session.refresh(post)
        return self.get_post(session, post.id)

    def delete_post(self, session: Session, post_id: UUID) -> None:
        """Delete a post and invalidate any active index state."""

        post = self.repository.get_by_id(session, post_id)
        if post is None:
            raise PostNotFoundError("Post not found")

        try:
            self.index_sync_service.invalidate_index_record(
                session,
                post_id=post.id,
                user_id=post.author_id,
                reason="post_deleted",
                operation="delete",
                visibility=post.visibility,
            )
            self.repository.delete(session, post=post)
            session.commit()
        except Exception as exc:
            session.rollback()
            self.index_sync_service.metrics.record_failure("delete")
            self.logger.exception(
                "Failed to synchronize post index record during delete",
                extra={
                    "post_id": str(post.id),
                    "operation": "delete",
                    "reason": "post_deleted",
                },
            )
            raise PostIndexSyncError("Failed to synchronize post index record") from exc

    def _ensure_author_exists(self, session: Session, author_id: UUID) -> None:
        """Raise when a post author does not exist."""

        if self.user_repository.get_by_id(session, author_id) is None:
            raise PostAuthorNotFoundError("Post author not found")

    def _serialize_index_record(self, record: PostIndexRecord) -> PostIndexRecordResponse:
        """Return the serialized index record payload."""

        return PostIndexRecordResponse.model_validate(record)

    def _sync_post_change(
        self,
        session: Session,
        *,
        post: Post,
        operation: str,
        invalidation_reason: str,
    ) -> None:
        """Refresh or invalidate the index record for the current post state."""

        try:
            if self.index_sync_service.is_indexable(post):
                self.index_sync_service.upsert_index_record(
                    session,
                    post=post,
                    operation=operation,
                )
                return

            self.index_sync_service.invalidate_index_record(
                session,
                post_id=post.id,
                user_id=post.author_id,
                reason=invalidation_reason,
                operation=operation,
                visibility=post.visibility,
            )
        except Exception as exc:
            self.index_sync_service.metrics.record_failure(operation)
            self.logger.exception(
                "Failed to synchronize post index record",
                extra={
                    "post_id": str(post.id),
                    "operation": operation,
                    "visibility": post.visibility,
                    "reason": invalidation_reason,
                },
            )
            raise PostIndexSyncError("Failed to synchronize post index record") from exc
