"""Tests for health check endpoints."""

from fastapi.testclient import TestClient

from stringdb_link import __version__
from stringdb_link.models.responses import HealthResponse


def test_health_check(test_client: TestClient):
    """Test basic health check endpoint."""
    response = test_client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    health_response = HealthResponse(**data)
    assert health_response.status == "healthy"
    assert health_response.version == __version__
    assert health_response.transport == "streamable-http-stateless"
    assert health_response.uptime_seconds >= 0


def test_root_health_check(test_client: TestClient):
    """Test root /health endpoint required by MCP Transport Standard v1 probe."""
    response = test_client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["version"] == __version__
    assert data["transport"] == "streamable-http-stateless"


def test_version_endpoint(test_client: TestClient):
    """Test version information endpoint."""
    response = test_client.get("/api/version")

    assert response.status_code == 200
    data = response.json()

    assert "version" in data
    assert "api_version" in data
    assert data["version"] == "1.0.0"
