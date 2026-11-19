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
    assert data["version"] == __version__


class _FakeClient:
    """Stand-in STRING client that counts upstream /version probes."""

    def __init__(self, exc: Exception | None = None) -> None:
        self.calls = 0
        self.exc = exc

    async def get_version(self) -> dict[str, str]:
        self.calls += 1
        if self.exc:
            raise self.exc
        return {"string_version": "12.5"}


def _health_with(fake: _FakeClient, monkeypatch) -> TestClient:
    from stringdb_link.api.routes import health
    from stringdb_link.api.routes.dependencies import get_stringdb_client
    from stringdb_link.app import app

    monkeypatch.setattr(health, "_upstream_probe", None, raising=False)
    monkeypatch.setitem(app.dependency_overrides, get_stringdb_client, lambda: fake)
    return TestClient(app)


def test_api_health_caches_upstream_probe(monkeypatch):
    """Repeated health polls within the TTL probe STRING once (#127)."""
    fake = _FakeClient()
    client = _health_with(fake, monkeypatch)

    for _ in range(5):
        assert client.get("/api/health").json()["status"] == "healthy"
    assert fake.calls == 1
    client.get("/health")  # liveness never probes upstream
    assert fake.calls == 1


def test_api_health_upstream_503_is_degraded_not_error(monkeypatch):
    """A STRING 5xx (StringDBAPIError, not httpx) degrades instead of raising (#127)."""
    from stringdb_link.exceptions import StringDBAPIError

    fake = _FakeClient(StringDBAPIError("server error", status_code=503))
    client = _health_with(fake, monkeypatch)

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["stringdb_api"] == "unavailable"
