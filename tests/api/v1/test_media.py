"""Integration tests for media endpoints."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def upload_media(
    client: AsyncClient,
    *,
    filename: str = "photo.png",
    content: bytes = b"\x89PNG\r\n\x1a\nimage-bytes",
    content_type: str = "image/png",
) -> dict[str, object]:
    """Upload a media file through the API and return the response payload."""

    response = await client.post(
        "/api/v1/media/upload",
        files={"file": (filename, content, content_type)},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


@pytest.mark.asyncio
async def test_upload_media_returns_created_metadata(client: AsyncClient) -> None:
    """Uploading media should persist metadata and expose the stored file URL."""

    payload = await upload_media(client, filename="summer photo.png")

    assert payload["filename"] == "summer_photo.png"
    assert payload["content_type"] == "image/png"
    assert payload["size"] == 19
    assert payload["storage_path"].endswith(".png")
    assert str(payload["url"]).startswith("/media-files/")
    assert "id" in payload
    assert "created_at" in payload

    file_response = await client.get(str(payload["url"]))
    assert file_response.status_code == 200
    assert file_response.content == b"\x89PNG\r\n\x1a\nimage-bytes"


@pytest.mark.asyncio
async def test_upload_media_rejects_unsupported_content_type(client: AsyncClient) -> None:
    """Uploading an unsupported media type should fail with 415."""

    response = await client.post(
        "/api/v1/media/upload",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json() == {"detail": "Unsupported media type"}


@pytest.mark.asyncio
async def test_upload_media_rejects_oversized_payload(client: AsyncClient) -> None:
    """Uploading a file above the configured size limit should fail with 413."""

    response = await client.post(
        "/api/v1/media/upload",
        files={"file": ("large.png", b"a" * 1025, "image/png")},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "File exceeds the maximum allowed size of 1024 bytes"}


@pytest.mark.asyncio
async def test_get_media_by_id_returns_metadata(client: AsyncClient) -> None:
    """Fetching media by id should return the stored record."""

    created_media = await upload_media(client)

    response = await client.get(f"/api/v1/media/{created_media['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created_media["id"]
    assert response.json()["storage_path"] == created_media["storage_path"]


@pytest.mark.asyncio
async def test_get_media_by_id_returns_not_found(client: AsyncClient) -> None:
    """Fetching unknown media should return 404."""

    response = await client.get(f"/api/v1/media/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Media not found"}


@pytest.mark.asyncio
async def test_list_media_returns_paginated_payload(client: AsyncClient) -> None:
    """Listing media should include pagination metadata."""

    await upload_media(client, filename="first.png")
    await upload_media(client, filename="second.png")

    response = await client.get("/api/v1/media", params={"page": 1, "limit": 1})

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert response.json()["limit"] == 1
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1


@pytest.mark.asyncio
async def test_delete_media_removes_metadata_and_file(client: AsyncClient) -> None:
    """Deleting media should remove both metadata and the stored file."""

    created_media = await upload_media(client)

    delete_response = await client.delete(f"/api/v1/media/{created_media['id']}")
    get_response = await client.get(f"/api/v1/media/{created_media['id']}")
    file_response = await client.get(str(created_media["url"]))

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Media deleted successfully"}
    assert get_response.status_code == 404
    assert file_response.status_code == 404


@pytest.mark.asyncio
async def test_openapi_documents_media_upload_as_multipart(client: AsyncClient) -> None:
    """The OpenAPI schema should describe the upload endpoint as multipart form data."""

    response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    upload_operation = schema["paths"]["/api/v1/media/upload"]["post"]
    multipart_schema = upload_operation["requestBody"]["content"]["multipart/form-data"]["schema"]

    assert upload_operation["operationId"] == "uploadMedia"
    assert "415" in upload_operation["responses"]
    assert multipart_schema["$ref"].startswith("#/components/schemas/")
