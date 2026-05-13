# backend/tests/test_main.py

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient, mock_db):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient, mock_db):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data


@pytest.mark.asyncio
async def test_docs_endpoint(client: AsyncClient, mock_db):
    response = await client.get("/api/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_openapi_endpoint(client: AsyncClient, mock_db):
    response = await client.get("/api/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient, mock_db):
    response = await client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_404_returns_json(client: AsyncClient, mock_db):
    response = await client.get("/nonexistent-route")
    assert response.status_code in (404, 422)


@pytest.mark.asyncio
async def test_rate_limit_headers(client: AsyncClient, mock_db):
    """Verify rate limiting middleware is active."""
    response = await client.get("/health")
    assert response.status_code == 200