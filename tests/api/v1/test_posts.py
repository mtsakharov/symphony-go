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
async def test_list_posts_returns_empty_page_when_page_exceeds_result_set(
    client: AsyncClient,
) -> None:
    """Listing posts should return an empty page instead of a 404."""

    author = await create_user(client, email="empty-page-author@example.com")
    await create_post(client, author_id=cast(str, author["id"]))

    response = await client.get("/api/v1/posts", params={"page": 2, "limit": 1})

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 2, "limit": 1, "total": 1}


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
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    components = schema["components"]["schemas"]

    assert operation["tags"] == ["Posts"]
    assert operation["summary"] == "List posts"
    assert operation["operationId"] == "listPosts"
    assert "empty `items` array" in operation["description"]

    assert parameters["page"]["description"].startswith("1-based page number")
    assert parameters["page"]["schema"]["default"] == 1
    assert parameters["page"]["schema"]["minimum"] == 1

    assert parameters["limit"]["description"].startswith("Number of posts returned per page")
    assert parameters["limit"]["schema"]["default"] == 20
    assert parameters["limit"]["schema"]["minimum"] == 1
    assert parameters["limit"]["schema"]["maximum"] == 100

    assert parameters["status"]["description"] == (
        "Filter posts by publication status (`draft` or `published`)."
    )
    assert parameters["author_id"]["description"] == "Filter posts by author id."

    search_schema = parameters["search"]["schema"]["anyOf"][0]
    assert parameters["search"]["description"] == "Case-insensitive search across title and body."
    assert search_schema["minLength"] == 1
    assert search_schema["maxLength"] == 255

    assert "Ties are resolved with the post `id`" in parameters["sort_by"]["description"]
    assert parameters["sort_by"]["schema"]["default"] == "created_at"
    assert parameters["sort_order"]["schema"]["default"] == "desc"

    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response_schema == {"$ref": "#/components/schemas/PostListResponse"}

    post_list_schema = components["PostListResponse"]
    assert post_list_schema["required"] == ["items", "page", "limit", "total"]
    assert post_list_schema["properties"]["items"]["description"].startswith("Posts returned")
    assert post_list_schema["properties"]["page"]["minimum"] == 1.0
    assert post_list_schema["properties"]["limit"]["minimum"] == 1.0
    assert post_list_schema["properties"]["total"]["minimum"] == 0.0
    assert post_list_schema["example"]["page"] == 1
    assert post_list_schema["example"]["limit"] == 20
    assert post_list_schema["example"]["total"] == 57

    post_response_schema = components["PostResponse"]
    assert post_response_schema["properties"]["id"]["description"] == (
        "Unique identifier for the post."
    )
    assert post_response_schema["properties"]["published_at"]["description"] == (
        "Timestamp when the post entered the `published` state."
    )
    assert post_response_schema["example"]["status"] == "published"

    assert components["PostStatus"]["enum"] == ["draft", "published"]
    assert components["PostSortField"]["enum"] == [
        "created_at",
        "updated_at",
        "published_at",
        "title",
    ]
    assert components["SortOrder"]["enum"] == ["asc", "desc"]
