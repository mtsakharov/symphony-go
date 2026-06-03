"""Integration tests for tweet request readiness endpoints."""

from __future__ import annotations

from typing import Any, cast

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
    assert "/api/v1/tweet-requests/readiness" in schema["paths"]
    operation = schema["paths"]["/api/v1/tweet-requests/readiness"]["post"]
    assert operation["operationId"] == "evaluateTweetRequestReadiness"
    assert "Tweet Requests" in operation["tags"]
    assert any(tag["name"] == "Tweet Requests" for tag in schema["tags"])
