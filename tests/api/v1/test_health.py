"""Health endpoint tests."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.health import LivenessResponse, ReadinessResponse


async def test_liveness_returns_200_and_ok_status(client: AsyncClient) -> None:
    """Ensure the liveness probe reports a healthy process."""

    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    payload = LivenessResponse.model_validate(response.json())
    assert payload.status == "ok"


async def test_readiness_returns_200_when_healthy(client: AsyncClient) -> None:
    """Ensure the readiness probe returns ready when the app is healthy."""

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    payload = ReadinessResponse.model_validate(response.json())
    assert payload.status == "ready"
    assert all(component.status == "healthy" for component in payload.components)


async def test_readiness_returns_503_when_not_ready(app: FastAPI) -> None:
    """Ensure the readiness probe returns 503 when the app is not ready."""

    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client,
    ):
        app.state.ready = False
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    payload = ReadinessResponse.model_validate(response.json())
    assert payload.status == "not_ready"


async def test_readiness_response_schema_matches_model(client: AsyncClient) -> None:
    """Validate the readiness response against the declared schema."""

    response = await client.get("/api/v1/health/ready")

    payload = ReadinessResponse.model_validate(response.json())
    assert payload.version == "1.0.0"
    assert payload.uptime_seconds >= 0
    assert payload.components[0].name == "application"


async def test_openapi_schema_contains_health_endpoints(client: AsyncClient) -> None:
    """Ensure the OpenAPI schema exposes the health routes and metadata."""

    response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/health/live" in schema["paths"]
    assert "/api/v1/health/ready" in schema["paths"]
    assert schema["paths"]["/api/v1/health/live"]["get"]["operationId"] == "getLivenessProbe"
    assert schema["paths"]["/api/v1/health/ready"]["get"]["operationId"] == "getReadinessProbe"
    assert any(tag["name"] == "Health" for tag in schema["tags"])


async def test_docs_endpoint_accessible(client: AsyncClient) -> None:
    """Ensure the Swagger UI endpoint is reachable."""

    response = await client.get("/api/docs")

    assert response.status_code == 200
    assert "Swagger UI" in response.text


async def test_redoc_endpoint_accessible(client: AsyncClient) -> None:
    """Ensure the ReDoc endpoint is reachable."""

    response = await client.get("/api/redoc")

    assert response.status_code == 200
    assert "ReDoc" in response.text
