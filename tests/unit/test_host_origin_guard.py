"""Host/Origin boundary contracts for the unified MCP application."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from packaging.version import Version

from stringdb_link.config import Settings, settings
from stringdb_link.models.responses import InteractionPartnerListResponse
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


_MODERN_VERSION = "2026-07-28"
_MODERN_META = {
    "io.modelcontextprotocol/protocolVersion": _MODERN_VERSION,
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "stringdb-host-test", "version": "1.0.0"},
}


def _modern_post(
    client: TestClient, rpc_id: int, method: str, params: dict[str, object], name: str | None = None
) -> Any:
    headers = {
        "Host": "stringdb-link.genefoundry.org",
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "mcp-protocol-version": _MODERN_VERSION,
        "mcp-method": method,
    }
    if name is not None:
        headers["mcp-name"] = name
    return client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": method,
            "params": {**params, "_meta": _MODERN_META},
        },
    )


def test_modern_mcp_http_discovers_lists_calls_and_fences_unknown_tool(
    client: TestClient,
) -> None:
    """2026-07-28 sessionless era: discover -> list -> call, unknown tool fenced."""
    hostile = "ignore-instructions-secret"
    partners = InteractionPartnerListResponse(partners=[], total_count=0)
    with (
        patch(
            "stringdb_link.services.stringdb_service.StringDBService.get_interaction_partners",
            new_callable=AsyncMock,
            return_value=partners,
        ),
        client,
    ):
        discover = _modern_post(client, 1, "server/discover", {})
        listed = _modern_post(client, 2, "tools/list", {})
        called = _modern_post(
            client,
            3,
            "tools/call",
            {
                "name": "get_interaction_partners",
                "arguments": {"identifiers": ["TP53"], "species": 9606},
            },
            name="get_interaction_partners",
        )
        unknown = _modern_post(
            client, 4, "tools/call", {"name": hostile, "arguments": {}}, name=hostile
        )

    assert discover.status_code == 200
    assert _MODERN_VERSION in discover.json()["result"]["supportedVersions"]
    assert "mcp-session-id" not in discover.headers
    assert listed.status_code == 200
    assert "get_interaction_partners" in {t["name"] for t in listed.json()["result"]["tools"]}
    assert called.status_code == 200
    assert called.json()["result"]["structuredContent"]["success"] is True
    assert unknown.status_code == 200
    unknown_result = unknown.json()["result"]
    assert unknown_result["isError"] is True
    assert unknown_result["structuredContent"]["error_code"] == "not_found"
    assert hostile not in unknown.text
