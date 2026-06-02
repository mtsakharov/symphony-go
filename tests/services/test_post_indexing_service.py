"""Unit and persistence tests for post indexing."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.post_indexing.chunking import chunk_normalized_text, normalize_post_content
from app.post_indexing.repository import PostIndexRepository
from app.post_indexing.service import UserPostIndexingService
from app.posts.models import Post
from app.users.models import User


def build_user(*, email: str = "indexer@example.com") -> User:
    """Return a hydrated user model for indexing tests."""

    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        email=email,
        first_name="Index",
        last_name="User",
        password_hash="",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def build_post(
    *,
    user_id: UUID,
    title: str = "Post title",
    body: str = "Post body",
    visibility: str = "followers",
    published_at: datetime | None = None,
    is_archived: bool = False,
    is_deleted: bool = False,
) -> Post:
    """Return a hydrated post model for indexing tests."""

    now = datetime.now(UTC)
    return Post(
        id=uuid4(),
        user_id=user_id,
        title=title,
        body=body,
        visibility=visibility,
        published_at=published_at or now,
        is_archived=is_archived,
        is_deleted=is_deleted,
        created_at=now,
        updated_at=now,
    )


def test_normalize_post_content_strips_markup_and_collapses_whitespace() -> None:
    """Normalization should produce stable plain text."""

    normalized = normalize_post_content(
        title="  <h1>Hello</h1>  ",
        body="<p>One</p><p> Two&nbsp; words </p>",
    )

    assert normalized == "Hello\n\nOne\nTwo words"


def test_chunk_normalized_text_is_deterministic_for_oversized_content() -> None:
    """Chunking should preserve order and stable chunk identifiers."""

    post_id = uuid4()
    text = (
        "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron.\n\n"
        "This paragraph is also deliberately long so the chunker has to split it more than once."
    )

    first = chunk_normalized_text(post_id=post_id, text=text, max_chars=60)
    second = chunk_normalized_text(post_id=post_id, text=text, max_chars=60)

    assert len(first) > 1
    assert [(chunk.chunk_id, chunk.chunk_index, chunk.text) for chunk in first] == [
        (chunk.chunk_id, chunk.chunk_index, chunk.text) for chunk in second
    ]
    assert all(len(chunk.text) <= 60 for chunk in first)


def test_index_user_posts_persists_eligible_posts(db_session: Session) -> None:
    """Eligible published posts should be indexed with traceable metadata."""

    user = build_user()
    post = build_post(
        user_id=user.id,
        title="  <h1>Launch update</h1> ",
        body="<p>First paragraph.</p><p>Second paragraph.</p>",
    )
    db_session.add_all([user, post])
    db_session.commit()

    summary = UserPostIndexingService(max_chunk_size=120).index_user_posts(db_session, user.id)
    records = PostIndexRepository().list_post_chunks(db_session, user_id=user.id)

    assert summary.indexed_posts == 1
    assert summary.skipped_posts == 0
    assert summary.indexed_chunks == 1
    assert len(records) == 1
    assert records[0].user_id == user.id
    assert records[0].post_id == post.id
    assert records[0].chunk_id == f"{post.id}:0"
    assert records[0].visibility == "followers"
    assert records[0].content == "Launch update\n\nFirst paragraph.\nSecond paragraph."


def test_index_user_posts_excludes_ineligible_posts_and_removes_existing_chunks(
    db_session: Session,
) -> None:
    """Archived, deleted, draft, or empty posts should not remain indexed."""

    user = build_user(email="stale@example.com")
    post = build_post(user_id=user.id, body="This used to be eligible.")
    db_session.add_all([user, post])
    db_session.commit()

    service = UserPostIndexingService(max_chunk_size=120)
    first_summary = service.index_user_posts(db_session, user.id)
    assert first_summary.indexed_posts == 1

    post.is_archived = True
    db_session.add(post)
    db_session.commit()

    second_summary = service.index_user_posts(db_session, user.id)
    records = PostIndexRepository().list_post_chunks(db_session, user_id=user.id)

    assert second_summary.indexed_posts == 0
    assert second_summary.skipped_posts == 1
    assert second_summary.removed_posts == 1
    assert records == []


def test_index_user_posts_chunks_oversized_content(db_session: Session) -> None:
    """Oversized posts should be split deterministically into multiple chunks."""

    user = build_user(email="chunked@example.com")
    post = build_post(
        user_id=user.id,
        title="Weekly digest",
        body=(
            "Paragraph one has enough text to exceed the configured chunk size when combined "
            "with the title and other sections.\n\n"
            "Paragraph two also has enough text to force a second chunk and prove that the "
            "ordering remains stable across repeated indexing runs."
        ),
    )
    db_session.add_all([user, post])
    db_session.commit()

    service = UserPostIndexingService(max_chunk_size=90)
    first_summary = service.index_user_posts(db_session, user.id)
    first_records = [
        (record.chunk_id, record.chunk_index, record.content)
        for record in PostIndexRepository().list_post_chunks(db_session, user_id=user.id)
    ]
    second_summary = service.index_user_posts(db_session, user.id)
    second_records = [
        (record.chunk_id, record.chunk_index, record.content)
        for record in PostIndexRepository().list_post_chunks(db_session, user_id=user.id)
    ]

    assert first_summary.indexed_chunks > 1
    assert second_summary.indexed_chunks == first_summary.indexed_chunks
    assert first_records == second_records
    assert all(len(content) <= 90 for _, _, content in first_records)
