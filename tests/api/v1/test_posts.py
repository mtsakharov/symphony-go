"""Integration tests for post endpoints."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def create_post(
    client: AsyncClient,
    *,
    title: str = "First post",
    content: str = "Hello world",
    is_published: bool = False,
) -> dict[str, object]:
    """Create a post through the API and return the response payload."""

    response = await client.post(
        "/api/v1/posts",
        json={"title": title, "content": content, "is_published": is_published},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


@pytest.mark.asyncio
async def test_create_post_returns_created_post(client: AsyncClient) -> None:
    """Creating a post should return the serialized entity."""

    payload = await create_post(client)

    assert payload["title"] == "First post"
    assert payload["content"] == "Hello world"
    assert payload["is_published"] is False
    assert "id" in payload
    assert "created_at" in payload
    assert "updated_at" in payload


@pytest.mark.asyncio
async def test_list_posts_returns_paginated_payload(client: AsyncClient) -> None:
    """Listing posts should include pagination metadata."""

    await create_post(client, title="First post", content="Alpha")
    await create_post(client, title="Second post", content="Beta")

    response = await client.get("/api/v1/posts", params={"page": 1, "limit": 1})

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert response.json()["limit"] == 1
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1


@pytest.mark.asyncio
async def test_get_post_by_id_returns_post(client: AsyncClient) -> None:
    """Fetching a post by id should return the record."""

    created_post = await create_post(client)

    response = await client.get(f"/api/v1/posts/{created_post['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created_post["id"]


@pytest.mark.asyncio
async def test_get_post_by_id_returns_not_found(client: AsyncClient) -> None:
    """Fetching a missing post should return 404."""

    response = await client.get(f"/api/v1/posts/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Post not found"}


@pytest.mark.asyncio
async def test_update_post_returns_updated_post(client: AsyncClient) -> None:
    """Updating a post should persist the requested changes."""

    created_post = await create_post(client)

    response = await client.patch(
        f"/api/v1/posts/{created_post['id']}",
        json={"title": "Updated post", "is_published": True},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated post"
    assert response.json()["content"] == "Hello world"
    assert response.json()["is_published"] is True


@pytest.mark.asyncio
async def test_delete_post_removes_post(client: AsyncClient) -> None:
    """Deleting a post should remove it from later reads."""

    created_post = await create_post(client)

    delete_response = await client.delete(f"/api/v1/posts/{created_post['id']}")
    get_response = await client.get(f"/api/v1/posts/{created_post['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Post deleted successfully"}
    assert get_response.status_code == 404
