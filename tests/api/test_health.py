"""Tests for health check endpoints."""

from fastapi.testclient import TestClient
import pytest

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


def test_cache_stats_disabled(test_client: TestClient):
    """Test cache stats when caching is disabled."""
    response = test_client.get("/api/cache/stats")

    assert response.status_code == 200
    data = response.json()

    assert "cache_enabled" in data


def test_liveness_probe(test_client: TestClient):
    """Test Kubernetes liveness probe."""
    response = test_client.get("/api/health/live")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "alive"


@pytest.mark.slow
def test_detailed_health_check(test_client: TestClient):
    """Test detailed health check (may be slow due to StringDB API call)."""
    response = test_client.get("/api/health/detailed")

    # Should return either 200 (healthy) or 503 (degraded)
    assert response.status_code in [200, 503]

    data = response.json()
    if response.status_code == 200:
        health_response = HealthResponse(**data)
        assert health_response.status in ["healthy", "degraded"]
        assert health_response.stringdb_api in ["available", "unavailable"]
