"""
Tests for API Gateway routing, health checks, and documentation endpoints.
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_gateway_health(client: httpx.AsyncClient):
    """Verify that the NGINX API Gateway is healthy."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "api-gateway"


@pytest.mark.asyncio
async def test_gateway_api_info(client: httpx.AsyncClient):
    """Verify that API Gateway metadata and endpoints directory are accessible."""
    response = await client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "endpoints" in data
    assert "/api/v1/auth" in data["endpoints"]
    assert "/api/v1/products" in data["endpoints"]
    assert "/api/v1/orders" in data["endpoints"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "docs_path",
    [
        "/docs/users",
        "/docs/products",
        "/docs/cart",
        "/docs/orders",
        "/docs/payments",
        "/docs/notifications",
    ],
)
async def test_service_swagger_docs(client: httpx.AsyncClient, docs_path: str):
    """Verify that the Swagger/OpenAPI docs for each microservice are reverse-proxied."""
    response = await client.get(docs_path)
    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "html" in response.headers.get("content-type", "")
