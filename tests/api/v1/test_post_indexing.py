"""Integration tests for post indexing endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from app.posts.models import Post
from app.users.models import User


@pytest.mark.asyncio
async def test_index_user_posts_endpoint_returns_summary(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """The API should expose a callable single-user indexing path."""

    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        email="api-index@example.com",
        first_name="Api",
        last_name="Indexer",
        password_hash="",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    post = Post(
        id=uuid4(),
        user_id=user.id,
        title="Endpoint test",
        body="This published post should be indexed through the API.",
        visibility="private",
        published_at=now,
        created_at=now,
        updated_at=now,
    )

    with db_session_factory() as session:
        session.add_all([user, post])
        session.commit()

    response = await client.post(f"/api/v1/users/{user.id}/posts/index")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(user.id),
        "indexed_posts": 1,
        "skipped_posts": 0,
        "removed_posts": 0,
        "indexed_chunks": 1,
    }
