"""Integration tests for post endpoints."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.posts.schemas import PostListResponse


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
async def test_list_posts_response_contract_is_locked(client: AsyncClient) -> None:
    """Listing posts should preserve the published paginated response contract."""

    author = await create_user(client, email="contract-author@example.com")
    await create_post(
        client,
        author_id=cast(str, author["id"]),
        title="Contract post",
        body="Stable contract body",
        status="published",
    )

    response = await client.get("/api/v1/posts", params={"page": 1, "limit": 20})

    assert response.status_code == 200
    payload = response.json()
    assert list(payload) == ["items", "page", "limit", "total"]
    assert len(payload["items"]) == 1
    assert list(payload["items"][0]) == [
        "id",
        "title",
        "body",
        "status",
        "author_id",
        "published_at",
        "created_at",
        "updated_at",
    ]
    assert payload["items"][0]["title"] == "Contract post"
    assert payload["items"][0]["body"] == "Stable contract body"
    assert payload["items"][0]["status"] == "published"
    assert payload["items"][0]["author_id"] == author["id"]
    assert payload["items"][0]["published_at"] is not None
    assert payload["page"] == 1
    assert payload["limit"] == 20
    assert payload["total"] == 1
    assert PostListResponse.model_validate(payload).model_dump(mode="json") == payload


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
    """OpenAPI should advertise and lock the paginated posts contract."""

    response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/posts" in schema["paths"]
    assert "/api/v1/posts/{post_id}" in schema["paths"]
    assert any(tag["name"] == "Posts" for tag in schema["tags"])

    operation = schema["paths"]["/api/v1/posts"]["get"]
    assert operation == {
        "tags": ["Posts"],
        "summary": "List posts",
        "description": "Return a paginated list of posts with optional filtering and sorting.",
        "operationId": "listPosts",
        "parameters": [
            {
                "name": "page",
                "in": "query",
                "required": False,
                "description": "Page number starting from 1.",
                "schema": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 1,
                    "title": "Page",
                    "description": "Page number starting from 1.",
                },
            },
            {
                "name": "limit",
                "in": "query",
                "required": False,
                "description": "Number of posts per page.",
                "schema": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                    "title": "Limit",
                    "description": "Number of posts per page.",
                },
            },
            {
                "name": "status",
                "in": "query",
                "required": False,
                "description": "Filter posts by publication status.",
                "schema": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/PostStatus"},
                        {"type": "null"},
                    ],
                    "description": "Filter posts by publication status.",
                    "title": "Status",
                },
            },
            {
                "name": "author_id",
                "in": "query",
                "required": False,
                "description": "Filter posts by author id.",
                "schema": {
                    "anyOf": [
                        {"type": "string", "format": "uuid"},
                        {"type": "null"},
                    ],
                    "description": "Filter posts by author id.",
                    "title": "Author Id",
                },
            },
            {
                "name": "search",
                "in": "query",
                "required": False,
                "description": "Case-insensitive search across title and body.",
                "schema": {
                    "anyOf": [
                        {"type": "string", "minLength": 1, "maxLength": 255},
                        {"type": "null"},
                    ],
                    "description": "Case-insensitive search across title and body.",
                    "title": "Search",
                },
            },
            {
                "name": "sort_by",
                "in": "query",
                "required": False,
                "description": "Field used to sort the result set.",
                "schema": {
                    "$ref": "#/components/schemas/PostSortField",
                    "default": "created_at",
                    "description": "Field used to sort the result set.",
                },
            },
            {
                "name": "sort_order",
                "in": "query",
                "required": False,
                "description": "Sort direction for the selected field.",
                "schema": {
                    "$ref": "#/components/schemas/SortOrder",
                    "default": "desc",
                    "description": "Sort direction for the selected field.",
                },
            },
        ],
        "responses": {
            "200": {
                "description": "Successful Response",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/PostListResponse"}
                    }
                },
            },
            "422": {
                "description": "Validation Error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
                    }
                },
            },
        },
    }
    assert schema["components"]["schemas"]["PostListResponse"] == {
        "title": "PostListResponse",
        "type": "object",
        "description": "Paginated posts list response.",
        "required": ["items", "page", "limit", "total"],
        "properties": {
            "items": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/PostResponse"},
                "title": "Items",
            },
            "page": {
                "type": "integer",
                "minimum": 1.0,
                "title": "Page",
            },
            "limit": {
                "type": "integer",
                "minimum": 1.0,
                "title": "Limit",
            },
            "total": {
                "type": "integer",
                "minimum": 0.0,
                "title": "Total",
            },
        },
    }
    assert schema["components"]["schemas"]["PostResponse"] == {
        "title": "PostResponse",
        "type": "object",
        "description": "Serialized post returned by the API.",
        "required": [
            "id",
            "title",
            "body",
            "status",
            "author_id",
            "published_at",
            "created_at",
            "updated_at",
        ],
        "properties": {
            "id": {"type": "string", "format": "uuid", "title": "Id"},
            "title": {"type": "string", "title": "Title"},
            "body": {"type": "string", "title": "Body"},
            "status": {"$ref": "#/components/schemas/PostStatus"},
            "author_id": {"type": "string", "format": "uuid", "title": "Author Id"},
            "published_at": {
                "anyOf": [
                    {"type": "string", "format": "date-time"},
                    {"type": "null"},
                ],
                "title": "Published At",
            },
            "created_at": {
                "type": "string",
                "format": "date-time",
                "title": "Created At",
            },
            "updated_at": {
                "type": "string",
                "format": "date-time",
                "title": "Updated At",
            },
        },
    }
    assert schema["components"]["schemas"]["PostStatus"] == {
        "title": "PostStatus",
        "type": "string",
        "description": "Supported post publication states.",
        "enum": ["draft", "published"],
    }
    assert schema["components"]["schemas"]["PostSortField"] == {
        "title": "PostSortField",
        "type": "string",
        "description": "Supported list sorting fields.",
        "enum": ["created_at", "updated_at", "published_at", "title"],
    }
    assert schema["components"]["schemas"]["SortOrder"] == {
        "title": "SortOrder",
        "type": "string",
        "description": "Supported sorting directions.",
        "enum": ["asc", "desc"],
    }
