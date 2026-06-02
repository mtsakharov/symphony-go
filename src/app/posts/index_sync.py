"""Index synchronization helpers for post lifecycle events."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.posts.models import Post, PostIndexRecord, PostVisibility, utc_now
from app.posts.repository import PostIndexRecordRepository


class PostIndexMetrics(Protocol):
    """Thin metrics hook for post index synchronization."""

    def record_success(self, operation: str) -> None:
        """Record a successful synchronization."""

    def record_failure(self, operation: str) -> None:
        """Record a failed synchronization."""


class NoOpPostIndexMetrics:
    """Default metrics implementation used until a real backend exists."""

    def record_success(self, operation: str) -> None:
        """Ignore successful synchronization events."""

    def record_failure(self, operation: str) -> None:
        """Ignore failed synchronization events."""


@dataclass(slots=True)
class PostIndexSyncService:
    """Synchronize post lifecycle changes into persistent index state."""

    repository: PostIndexRecordRepository = field(default_factory=PostIndexRecordRepository)
    metrics: PostIndexMetrics = field(default_factory=NoOpPostIndexMetrics)

    def is_indexable(self, post: Post) -> bool:
        """Return whether a post should have an active index record."""

        return post.visibility == PostVisibility.PUBLIC.value

    def upsert_index_record(
        self,
        session: Session,
        *,
        post: Post,
        operation: str,
    ) -> PostIndexRecord:
        """Create or refresh the active index record for a post."""

        record = self.repository.get_by_post_and_user(
            session,
            post_id=post.id,
            user_id=post.author_id,
        )
        content_hash = self._build_content_hash(post.body)

        if record is None:
            record = PostIndexRecord(
                post_id=post.id,
                user_id=post.author_id,
            )

        record.source_version = post.version
        record.indexed_body = post.body
        record.content_hash = content_hash
        record.visibility = post.visibility
        record.is_active = True
        record.invalidated_at = None
        record.invalidation_reason = None
        record.last_operation = operation
        record.last_synced_at = utc_now()

        saved_record = self.repository.save(session, record=record)
        self.metrics.record_success(operation)
        return saved_record

    def invalidate_index_record(
        self,
        session: Session,
        *,
        post_id: UUID,
        user_id: UUID,
        reason: str,
        operation: str,
        visibility: str | None = None,
    ) -> PostIndexRecord:
        """Create or refresh an inactive index record for a post."""

        record = self.repository.get_by_post_and_user(
            session,
            post_id=post_id,
            user_id=user_id,
        )

        if record is None:
            record = PostIndexRecord(
                post_id=post_id,
                user_id=user_id,
            )

        record.indexed_body = ""
        record.content_hash = ""
        record.visibility = visibility
        record.is_active = False
        record.invalidated_at = utc_now()
        record.invalidation_reason = reason
        record.last_operation = operation
        record.last_synced_at = utc_now()

        saved_record = self.repository.save(session, record=record)
        self.metrics.record_success(operation)
        return saved_record

    def _build_content_hash(self, body: str) -> str:
        """Return a stable hash for the indexed body."""

        return sha256(body.encode("utf-8")).hexdigest()
