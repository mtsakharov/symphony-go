"""Integration tests for post endpoints."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def create_user(
    client: AsyncClient,
    *,
    email: str,
    first_name: str = "John",
    last_name: str = "Doe",
) -> dict[str, object]:
    """Create a user through the API and return the response payload."""

    response = await client.post(
        "/api/v1/users",
        json={"email": email, "first_name": first_name, "last_name": last_name},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def create_post(
    client: AsyncClient,
    *,
    author_id: str,
    title: str = "Hello world",
    body: str = "Post body",
    status: str = "draft",
) -> dict[str, object]:
    """Create a post through the API and return the response payload."""

    response = await client.post(
        "/api/v1/posts",
        json={"title": title, "body": body, "status": status, "author_id": author_id},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


@pytest.mark.asyncio
async def test_create_post_returns_created_post(client: AsyncClient) -> None:
    """Creating a post should return the serialized entity."""

    author = await create_user(client, email="author@example.com")

    payload = await create_post(
        client,
        author_id=cast(str, author["id"]),
        title="Introducing Posts",
        body="Draft content",
    )

    assert payload["title"] == "Introducing Posts"
    assert payload["body"] == "Draft content"
    assert payload["status"] == "draft"
    assert payload["author_id"] == author["id"]
    assert payload["published_at"] is None
    assert "id" in payload
    assert "created_at" in payload
    assert "updated_at" in payload


@pytest.mark.asyncio
async def test_create_post_rejects_unknown_author(client: AsyncClient) -> None:
    """Creating a post with a missing author should fail with 400."""

    response = await client.post(
        "/api/v1/posts",
        json={
            "title": "Introducing Posts",
            "body": "Draft content",
            "status": "draft",
            "author_id": str(uuid4()),
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Author not found"}


@pytest.mark.asyncio
async def test_list_posts_supports_filtering_sorting_and_pagination(client: AsyncClient) -> None:
    """Listing posts should apply filters, sorting, and pagination metadata."""

    first_author = await create_user(client, email="author1@example.com")
    second_author = await create_user(client, email="author2@example.com")

    await create_post(
        client,
        author_id=cast(str, first_author["id"]),
        title="Zulu",
        body="First body",
        status="draft",
    )
    await create_post(
        client,
        author_id=cast(str, first_author["id"]),
        title="Alpha",
        body="Launch notes",
        status="published",
    )
    await create_post(
        client,
        author_id=cast(str, second_author["id"]),
        title="Bravo",
        body="Launch recap",
        status="published",
    )

    response = await client.get(
        "/api/v1/posts",
        params={
            "page": 1,
            "limit": 1,
            "status": "published",
            "author_id": cast(str, first_author["id"]),
            "search": "launch",
            "sort_by": "title",
            "sort_order": "asc",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["limit"] == 1
    assert payload["total"] == 1
    assert [item["title"] for item in payload["items"]] == ["Alpha"]


@pytest.mark.asyncio
async def test_get_post_by_id_returns_not_found(client: AsyncClient) -> None:
    """Fetching a missing post should return 404."""

    response = await client.get(f"/api/v1/posts/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Post not found"}


@pytest.mark.asyncio
async def test_update_post_can_publish_draft(client: AsyncClient) -> None:
    """Updating a post should support publish transitions."""

    author = await create_user(client, email="author@example.com")
    post = await create_post(client, author_id=cast(str, author["id"]))

    response = await client.patch(
        f"/api/v1/posts/{post['id']}",
        json={"title": "Published title", "status": "published"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Published title"
    assert payload["status"] == "published"
    assert payload["published_at"] is not None


@pytest.mark.asyncio
async def test_delete_post_removes_post(client: AsyncClient) -> None:
    """Deleting a post should remove it from later reads."""

    author = await create_user(client, email="author@example.com")
    post = await create_post(client, author_id=cast(str, author["id"]))

    delete_response = await client.delete(f"/api/v1/posts/{post['id']}")
    get_response = await client.get(f"/api/v1/posts/{post['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Post deleted successfully"}
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_create_post_validates_payload(client: AsyncClient) -> None:
    """Creating a post with invalid data should fail with 422."""

    author = await create_user(client, email="author@example.com")

    response = await client.post(
        "/api/v1/posts",
        json={
            "title": " ",
            "body": "Post body",
            "author_id": cast(str, author["id"]),
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_posts_validates_pagination_params(client: AsyncClient) -> None:
    """Listing posts should validate pagination inputs."""

    response = await client.get("/api/v1/posts", params={"page": 0, "limit": 101})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_openapi_schema_includes_posts_endpoints(client: AsyncClient) -> None:
    """OpenAPI should advertise the posts module."""

    response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/posts" in schema["paths"]
    assert "/api/v1/posts/{post_id}" in schema["paths"]
    assert any(tag["name"] == "Posts" for tag in schema["tags"])
