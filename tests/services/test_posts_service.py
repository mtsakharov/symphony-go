"""Integration and service tests for posts."""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.posts.exceptions import PostIndexSyncError
from app.posts.index_sync import PostIndexSyncService
from app.posts.models import Post, PostIndexRecord, PostVisibility
from app.posts.repository import PostIndexRecordRepository
from app.posts.schemas import PostCreate, PostUpdate
from app.posts.service import PostService
from app.users.models import User


def create_user(session: Session, *, user_id: UUID | None = None) -> User:
    """Create and persist a user for post tests."""

    user = User(
        id=user_id or uuid4(),
        email=f"{uuid4()}@example.com",
        first_name="Test",
        last_name="User",
        password_hash="",
        is_active=True,
    )
    session.add(user)
    session.commit()
    return user


def list_index_records(session: Session, *, post_id: UUID) -> list[PostIndexRecord]:
    """Return all index records for a post."""

    return PostIndexRecordRepository().list_by_post(session, post_id=post_id)


def test_create_post_creates_active_index_record(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Creating an indexable post should upsert one active index record."""

    service = PostService()

    with db_session_factory() as session:
        user = create_user(session)

        response = service.create_post(
            session,
            PostCreate(
                author_id=user.id,
                body="Hello world",
                visibility=PostVisibility.PUBLIC,
            ),
        )

        records = list_index_records(session, post_id=response.id)

    assert len(records) == 1
    assert records[0].is_active is True
    assert records[0].indexed_body == "Hello world"
    assert records[0].last_operation == "create"


def test_update_post_refreshes_existing_active_index_record_without_duplicates(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Updating a post should refresh the existing active index record in place."""

    service = PostService()

    with db_session_factory() as session:
        user = create_user(session)
        created = service.create_post(
            session,
            PostCreate(
                author_id=user.id,
                body="First body",
                visibility=PostVisibility.PUBLIC,
            ),
        )
        original_record = created.index_record

        updated = service.update_post(
            session,
            created.id,
            PostUpdate(body="Updated body"),
        )
        records = list_index_records(session, post_id=created.id)

    assert len(records) == 1
    assert updated.index_record is not None
    assert original_record is not None
    assert updated.index_record.id == original_record.id
    assert updated.index_record.indexed_body == "Updated body"
    assert updated.index_record.is_active is True
    assert updated.index_record.last_operation == "update"


def test_delete_post_invalidates_index_record(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Deleting a post should invalidate its index record."""

    service = PostService()

    with db_session_factory() as session:
        user = create_user(session)
        created = service.create_post(
            session,
            PostCreate(
                author_id=user.id,
                body="Delete me",
                visibility=PostVisibility.PUBLIC,
            ),
        )

        service.delete_post(session, created.id)
        records = list_index_records(session, post_id=created.id)

    assert len(records) == 1
    assert records[0].is_active is False
    assert records[0].invalidation_reason == "post_deleted"
    assert records[0].last_operation == "delete"
    assert records[0].indexed_body == ""


def test_visibility_change_invalidates_existing_record(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Changing visibility to a non-indexable state should invalidate the record."""

    service = PostService()

    with db_session_factory() as session:
        user = create_user(session)
        created = service.create_post(
            session,
            PostCreate(
                author_id=user.id,
                body="Visible body",
                visibility=PostVisibility.PUBLIC,
            ),
        )

        updated = service.update_post(
            session,
            created.id,
            PostUpdate(visibility=PostVisibility.PRIVATE),
        )
        records = list_index_records(session, post_id=created.id)

    assert len(records) == 1
    assert updated.index_record is not None
    assert updated.index_record.is_active is False
    assert updated.index_record.invalidation_reason == "visibility_changed"
    assert records[0].indexed_body == ""


def test_visibility_change_back_to_public_reactivates_single_record(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Returning a post to public visibility should reactivate the same record."""

    service = PostService()

    with db_session_factory() as session:
        user = create_user(session)
        created = service.create_post(
            session,
            PostCreate(
                author_id=user.id,
                body="Private body",
                visibility=PostVisibility.PRIVATE,
            ),
        )
        created_record = created.index_record

        updated = service.update_post(
            session,
            created.id,
            PostUpdate(visibility=PostVisibility.PUBLIC),
        )
        records = list_index_records(session, post_id=created.id)

    assert len(records) == 1
    assert created_record is not None
    assert updated.index_record is not None
    assert updated.index_record.id == created_record.id
    assert updated.index_record.is_active is True
    assert updated.index_record.indexed_body == "Private body"
    assert updated.index_record.last_operation == "privacy_change"


def test_reprocessing_same_index_event_keeps_one_active_record(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Repeatedly syncing the same post should keep a single active record."""

    service = PostService()
    sync_service = PostIndexSyncService()

    with db_session_factory() as session:
        user = create_user(session)
        created = service.create_post(
            session,
            PostCreate(
                author_id=user.id,
                body="Idempotent body",
                visibility=PostVisibility.PUBLIC,
            ),
        )
        post = service.repository.get_by_id(session, created.id)
        assert post is not None

        sync_service.upsert_index_record(session, post=post, operation="update")
        sync_service.upsert_index_record(session, post=post, operation="update")
        session.commit()
        records = list_index_records(session, post_id=created.id)

    assert len(records) == 1
    assert records[0].is_active is True
    assert records[0].last_operation == "update"


def test_sync_failures_are_logged_and_raised(
    db_session_factory: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Synchronization failures should be logged and surfaced to callers."""

    class FailingPostIndexSyncService(PostIndexSyncService):
        def upsert_index_record(
            self,
            session: Session,
            *,
            post: Post,
            operation: str,
        ) -> PostIndexRecord:
            raise RuntimeError("index unavailable")

    service = PostService(index_sync_service=FailingPostIndexSyncService())

    with db_session_factory() as session:
        user = create_user(session)

        with (
            caplog.at_level(logging.ERROR, logger="app.posts.service"),
            pytest.raises(PostIndexSyncError, match="Failed to synchronize post index record"),
        ):
            service.create_post(
                session,
                PostCreate(
                    author_id=user.id,
                    body="Will fail",
                    visibility=PostVisibility.PUBLIC,
                ),
            )

        posts = list(session.execute(select(Post)).scalars().all())
        index_records = list(session.execute(select(PostIndexRecord)).scalars().all())

    assert posts == []
    assert index_records == []
    assert any(
        record.message == "Failed to synchronize post index record"
        for record in caplog.records
    )
    assert any(getattr(record, "operation", None) == "create" for record in caplog.records)
