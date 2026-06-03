"""Integration tests for tweet request readiness endpoints."""

from __future__ import annotations

from typing import Any, cast

import pytest
from httpx import AsyncClient


def build_payload() -> dict[str, Any]:
    """Return a valid organic tweet request payload."""

    return {
        "product_or_campaign": "Acme Analytics launch",
        "audience": "B2B SaaS founders",
        "intended_action": "Book a demo",
        "format": "organic",
        "tweet_count": 2,
        "variants_per_tweet": 2,
        "context": {
            "brief": "Launch-day tweet copy.",
            "source_materials": ["launch-brief-v3"],
        },
        "review": {
            "approval_required": False,
            "approver": None,
            "compliance_owner": None,
        },
        "compliance": {
            "regulated_claims": False,
            "brand_safety_notes": None,
        },
    }


async def create_tweet_request(
    client: AsyncClient,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    """Create a tweet request draft through the API and return the response payload."""

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
        "/api/v1/tweet-requests/00000000-0000-0000-0000-000000000000",
        json={"objective": "Drive signups for the waitlist"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Tweet request not found"}


async def test_readiness_endpoint_returns_draft_for_missing_fields(client: AsyncClient) -> None:
    """Empty payloads should surface draft issues."""

    response = await client.post("/api/v1/tweet-requests/readiness", json={})

    assert response.status_code == 200
    payload = cast(dict[str, Any], response.json())
    issue_codes = {issue["code"] for issue in payload["issues"]}
    assert payload["status"] == "draft"
    assert payload["is_ready"] is False
    assert payload["expected_deliverables"] is None
    assert "missing_audience" in issue_codes
    assert "missing_context" in issue_codes


async def test_readiness_endpoint_returns_ready_for_writing(client: AsyncClient) -> None:
    """Valid requests should return ready_for_writing and deliverable count."""

    response = await client.post("/api/v1/tweet-requests/readiness", json=build_payload())

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready_for_writing",
        "is_ready": True,
        "expected_deliverables": 4,
        "issues": [],
    }


async def test_openapi_schema_contains_tweet_request_readiness_endpoint(
    client: AsyncClient,
) -> None:
    """The readiness endpoint should be present in the generated OpenAPI schema."""

    response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/tweet-requests" in schema["paths"]
    assert schema["paths"]["/api/v1/tweet-requests"]["post"]["operationId"] == "createTweetRequest"
    assert (
        schema["paths"]["/api/v1/tweet-requests/{tweet_request_id}"]["patch"]["operationId"]
        == "updateTweetRequest"
    )
    assert "/api/v1/tweet-requests/readiness" in schema["paths"]
    operation = schema["paths"]["/api/v1/tweet-requests/readiness"]["post"]
    assert operation["operationId"] == "evaluateTweetRequestReadiness"
    assert "Tweet Requests" in operation["tags"]
    assert any(tag["name"] == "Tweet Requests" for tag in schema["tags"])
