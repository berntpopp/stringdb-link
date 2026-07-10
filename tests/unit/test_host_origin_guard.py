"""Host/Origin boundary contracts for the unified MCP application."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from packaging.version import Version

from stringdb_link.config import Settings, settings
from stringdb_link.server_manager import create_unified_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        settings,
        "allowed_hosts",
        ["localhost", "127.0.0.1", "::1", "stringdb-link.genefoundry.org"],
    )
    monkeypatch.setattr(settings, "allowed_origins", ["https://genefoundry.org"])
    return TestClient(create_unified_app(), raise_server_exceptions=False)


def test_fastmcp_344_strict_guard_is_installed(client: TestClient) -> None:
    assert Version(version("fastmcp")) >= Version("3.4.4")
    response = client.get("/mcp", headers={"Host": "stringdb-link.genefoundry.org"})
    assert response.status_code not in {403, 421}


def test_default_allowlists_are_loopback_only_and_origin_empty() -> None:
    configured = Settings(_env_file=None)
    assert configured.allowed_hosts == ["localhost", "127.0.0.1", "::1"]
    assert configured.allowed_origins == []


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]"])
def test_loopback_hosts_are_allowed(client: TestClient, host: str) -> None:
    response = client.get("/mcp", headers={"Host": host})
    assert response.status_code not in {403, 421}


@pytest.mark.parametrize("path", ["/", "/health", "/mcp"])
def test_untrusted_host_is_rejected_on_every_route(client: TestClient, path: str) -> None:
    response = client.get(path, headers={"Host": "evil.example"})
    assert response.status_code == 421


def test_absent_and_configured_origins_are_allowed(client: TestClient) -> None:
    no_origin = client.get("/mcp", headers={"Host": "stringdb-link.genefoundry.org"})
    configured_origin = client.get(
        "/mcp",
        headers={
            "Host": "stringdb-link.genefoundry.org",
            "Origin": "https://genefoundry.org",
        },
    )
    assert no_origin.status_code not in {403, 421}
    assert configured_origin.status_code not in {403, 421}


@pytest.mark.parametrize("path", ["/", "/health", "/mcp"])
def test_untrusted_origin_is_rejected_on_every_route(client: TestClient, path: str) -> None:
    response = client.get(
        path,
        headers={"Host": "stringdb-link.genefoundry.org", "Origin": "https://evil.example"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("wildcard", ["*", "*.example.org", "host?.example.org", "host[0]"])
def test_wildcard_host_is_rejected(wildcard: str) -> None:
    with pytest.raises(ValueError, match="wildcard"):
        Settings(_env_file=None, allowed_hosts=[wildcard])


def test_json_environment_allowlists_are_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "ALLOWED_HOSTS",
        '["localhost","stringdb-link.genefoundry.org"]',
    )
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://genefoundry.org"]')
    configured = Settings(_env_file=None)
    assert configured.allowed_hosts == ["localhost", "stringdb-link.genefoundry.org"]
    assert configured.allowed_origins == ["https://genefoundry.org"]


@pytest.mark.parametrize(
    "compose_file",
    [
        "docker/docker-compose.yml",
        "docker/docker-compose.prod.yml",
        "docker/docker-compose.npm.yml",
    ],
)
def test_compose_propagates_allowlist_and_healthcheck_host(compose_file: str) -> None:
    text = Path(compose_file).read_text()
    assert "ALLOWED_HOSTS" in text
    assert '"localhost","127.0.0.1","::1"' in text
    assert '"Host: localhost"' in text
