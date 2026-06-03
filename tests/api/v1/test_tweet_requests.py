"""Integration tests for tweet request endpoints."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def create_tweet_request(
    client: AsyncClient,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    """Create a tweet request through the API and return the response payload."""

    response = await client.post("/api/v1/tweet-requests", json=payload or {})
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


@pytest.mark.asyncio
async def test_create_tweet_request_accepts_partial_intake(client: AsyncClient) -> None:
    """Creating a partial tweet request should return structured missing readiness fields."""

    payload = await create_tweet_request(client, {"brief": "Announce the summer release."})

    assert payload["brief"] == "Announce the summer release."
    assert payload["status"] == "needs_clarification"
    assert payload["validation"] == {
        "is_ready": False,
        "missing_fields": [
            {
                "field": "target_audience",
                "message": "Specify the target audience for the tweet.",
            },
            {
                "field": "objective",
                "message": "Clarify the tweet objective before writing can start.",
            },
        ],
        "blockers": [],
    }


@pytest.mark.asyncio
async def test_create_tweet_request_rejects_server_derived_status_input(
    client: AsyncClient,
) -> None:
    """Clients should not be allowed to submit the derived status field."""

    response = await client.post(
        "/api/v1/tweet-requests",
        json={"brief": "Announce the summer release.", "status": "ready_for_writing"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "status"]


@pytest.mark.asyncio
async def test_update_tweet_request_can_promote_draft_to_ready(client: AsyncClient) -> None:
    """PATCH should recompute readiness and mark the draft ready when fields are satisfied."""

    created = await create_tweet_request(client, {"brief": "Announce the summer release."})

    response = await client.patch(
        f"/api/v1/tweet-requests/{created['id']}",
        json={
            "target_audience": "Existing enterprise customers",
            "objective": "Drive signups for the waitlist",
            "approved_by_compliance": True,
            "approved_by_reviewer": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready_for_writing"
    assert response.json()["validation"] == {
        "is_ready": True,
        "missing_fields": [],
        "blockers": [],
    }


@pytest.mark.asyncio
async def test_get_tweet_request_returns_current_validation_state(client: AsyncClient) -> None:
    """GET should return the persisted draft and its derived readiness state."""

    created = await create_tweet_request(
        client,
        {
            "brief": "Announce the summer release.",
            "target_audience": "Existing enterprise customers",
            "objective": "Drive signups for the waitlist",
        },
    )

    response = await client.get(f"/api/v1/tweet-requests/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["status"] == "blocked_review"
    assert response.json()["validation"] == {
        "is_ready": False,
        "missing_fields": [],
        "blockers": [
            {
                "code": "compliance_approval_required",
                "message": "Compliance approval is required before writing can start.",
            },
            {
                "code": "reviewer_approval_required",
                "message": "Reviewer approval is required before writing can start.",
            },
        ],
    }


@pytest.mark.asyncio
async def test_get_tweet_request_returns_not_found_for_unknown_id(client: AsyncClient) -> None:
    """Fetching an unknown tweet request should return 404."""

    response = await client.get(f"/api/v1/tweet-requests/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Tweet request not found"}


@pytest.mark.asyncio
async def test_get_tweet_request_status_returns_evaluated_status(client: AsyncClient) -> None:
    """GET /status should return the derived readiness subset for the draft."""

    created = await create_tweet_request(
        client,
        {
            "brief": "Announce the summer release.",
            "target_audience": "Existing enterprise customers",
            "objective": "Drive signups for the waitlist",
            "approved_by_compliance": True,
            "approved_by_reviewer": True,
        },
    )

    response = await client.get(f"/api/v1/tweet-requests/{created['id']}/status")

    assert response.status_code == 200
    assert response.json() == {
        "id": created["id"],
        "status": "ready_for_writing",
        "validation": {
            "is_ready": True,
            "missing_fields": [],
            "blockers": [],
        },
    }


@pytest.mark.asyncio
async def test_update_tweet_request_clears_approvals_after_brief_change(
    client: AsyncClient,
) -> None:
    """Editing approved brief content should move the draft back behind review gates."""

    created = await create_tweet_request(
        client,
        {
            "brief": "Announce the summer release.",
            "target_audience": "Existing enterprise customers",
            "objective": "Drive signups for the waitlist",
            "approved_by_compliance": True,
            "approved_by_reviewer": True,
        },
    )

    response = await client.patch(
        f"/api/v1/tweet-requests/{created['id']}",
        json={"brief": "Announce the fall release."},
    )

    assert response.status_code == 200
    assert response.json()["approved_by_compliance"] is None
    assert response.json()["approved_by_reviewer"] is None
    assert response.json()["status"] == "blocked_review"
    assert response.json()["validation"]["blockers"] == [
        {
            "code": "compliance_approval_required",
            "message": "Compliance approval is required before writing can start.",
        },
        {
            "code": "reviewer_approval_required",
            "message": "Reviewer approval is required before writing can start.",
        },
    ]


@pytest.mark.asyncio
async def test_update_tweet_request_returns_not_found_for_unknown_id(client: AsyncClient) -> None:
    """Updating an unknown tweet request should return 404."""

    response = await client.patch(
        f"/api/v1/tweet-requests/{uuid4()}",
        json={"objective": "Drive signups for the waitlist"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Tweet request not found"}


@pytest.mark.asyncio
async def test_get_tweet_request_status_returns_not_found_for_unknown_id(
    client: AsyncClient,
) -> None:
    """Evaluating status for an unknown tweet request should return 404."""

    response = await client.get(f"/api/v1/tweet-requests/{uuid4()}/status")

    assert response.status_code == 404
    assert response.json() == {"detail": "Tweet request not found"}
