"""Integration tests for retrieval endpoints."""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from app.posts.models import Post
from app.users.models import User


def create_user(session: Session, *, email: str, is_active: bool = True) -> User:
    """Persist a user for API retrieval tests."""

    user = User(
        email=email,
        first_name="Api",
        last_name="User",
        is_active=is_active,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_post(
    session: Session,
    *,
    user_id: UUID,
    content: str,
    is_deleted: bool = False,
    is_private: bool = False,
    is_blocked: bool = False,
) -> Post:
    """Persist a post for API retrieval tests."""

    post = Post(
        user_id=user_id,
        content=content,
        is_deleted=is_deleted,
        is_private=is_private,
        is_blocked=is_blocked,
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@pytest.mark.asyncio
async def test_retrieve_requires_authenticated_user_identity(client: AsyncClient) -> None:
    """The retrieval endpoint must reject anonymous access."""

    response = await client.post("/api/v1/retrieval/query", json={"query": "alpha"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing authenticated user identity"}


@pytest.mark.asyncio
async def test_retrieve_returns_only_visible_posts_for_current_user(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """The endpoint must enforce user scope and request-time visibility."""

    with db_session_factory() as session:
        current_user = create_user(session, email="current@example.com")
        other_user = create_user(session, email="other@example.com")
        visible_post = create_post(
            session,
            user_id=current_user.id,
            content="search target visible post",
        )
        create_post(
            session,
            user_id=current_user.id,
            content="search target deleted post",
            is_deleted=True,
        )
        create_post(
            session,
            user_id=current_user.id,
            content="search target private post",
            is_private=True,
        )
        create_post(
            session,
            user_id=current_user.id,
            content="search target blocked post",
            is_blocked=True,
        )
        create_post(
            session,
            user_id=other_user.id,
            content="search target other user post",
        )

    response = await client.post(
        "/api/v1/retrieval/query",
        headers={"X-User-Id": str(current_user.id)},
        json={"query": "search target", "top_k": 5, "token_budget": 20},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == str(current_user.id)
    assert payload["eligible_candidate_count"] == 1
    assert payload["dropped_ineligible_count"] == 3
    assert [record["post_id"] for record in payload["evidence"]] == [str(visible_post.id)]


@pytest.mark.asyncio
async def test_retrieve_derives_identity_from_header_not_payload(
    client: AsyncClient,
    db_session_factory: sessionmaker[Session],
) -> None:
    """The endpoint should use auth context rather than caller-supplied user ids."""

    with db_session_factory() as session:
        current_user = create_user(session, email="header@example.com")
        create_post(
            session,
            user_id=current_user.id,
            content="header scoped content",
        )

    response = await client.post(
        "/api/v1/retrieval/query",
        headers={"X-User-Id": str(current_user.id)},
        json={
            "query": "header scoped",
            "top_k": 1,
            "token_budget": 10,
            "user_id": "00000000-0000-0000-0000-000000000000",
        },
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == str(current_user.id)
