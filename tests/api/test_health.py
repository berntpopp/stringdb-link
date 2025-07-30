"""Tests for health check endpoints."""

from fastapi.testclient import TestClient

from stringdb_link.models.responses import HealthResponse


def test_health_check(test_client: TestClient):
    """Test basic health check endpoint."""
    response = test_client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    health_response = HealthResponse(**data)
    assert health_response.status == "healthy"
    assert health_response.version == "0.1.0"
    assert health_response.uptime_seconds >= 0


def test_version_endpoint(test_client: TestClient):
    """Test version information endpoint."""
    response = test_client.get("/api/version")

    assert response.status_code == 200
    data = response.json()

    assert "version" in data
    assert "api_version" in data
    assert data["version"] == "0.1.0"


