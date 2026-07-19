"""Contract Truth v1 gate against the live StringDB MCP registry."""

from __future__ import annotations

import asyncio
import socket
from hashlib import sha256
from pathlib import Path
from typing import Never

import pytest

EXPECTED_HELPER_SHA256 = "e6c12b087c8231f5324c6388abd01afaeffa305a84d0b7c0e3629e17993d3674"


async def test_documentation_matches_live_mcp_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Lint repository documentation against the production MCP registry."""
    helper_path = Path(__file__).with_name("contract_truth.py")
    pin_path = Path(__file__).with_name("contract_truth.sha256")

    vendored_pin = pin_path.read_text(encoding="utf-8").strip()
    assert vendored_pin == EXPECTED_HELPER_SHA256
    assert sha256(helper_path.read_bytes()).hexdigest() == vendored_pin

    from .contract_truth import (
        active_markdown_files,
        historical_markdown_files,
        lint_repository,
    )

    monkeypatch.chdir(tmp_path)

    outbound_attempts: list[tuple[str, object]] = []

    def reject_outbound(operation: str, address: object) -> Never:
        outbound_attempts.append((operation, address))
        raise AssertionError(f"contract discovery attempted outbound I/O via {operation}")

    def reject_connect(_socket: socket.socket, address: object) -> Never:
        reject_outbound("socket.connect", address)

    def reject_connect_ex(_socket: socket.socket, address: object) -> Never:
        reject_outbound("socket.connect_ex", address)

    async def reject_create_connection(
        _loop: asyncio.BaseEventLoop,
        _protocol_factory: object,
        host: object = None,
        port: object = None,
        *args: object,
        **kwargs: object,
    ) -> Never:
        reject_outbound("asyncio.create_connection", (host, port))

    monkeypatch.setattr(socket.socket, "connect", reject_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_connect_ex)
    monkeypatch.setattr(asyncio.BaseEventLoop, "create_connection", reject_create_connection)

    from stringdb_link import app as app_module
    from stringdb_link.api.routes.dependencies import (
        get_stringdb_client,
        get_stringdb_service,
    )

    api_app = app_module.create_app()
    fake_client = object()
    fake_service = object()
    api_app.dependency_overrides[get_stringdb_client] = lambda: fake_client
    api_app.dependency_overrides[get_stringdb_service] = lambda: fake_service
    monkeypatch.setattr(app_module, "create_app", lambda: api_app)

    tools = await app_module.create_mcp_app().list_tools()
    assert outbound_attempts == []
    assert tools, "the live MCP registry must not be empty"

    catalog: dict[str, dict[str, object]] = {}
    for tool in tools:
        assert isinstance(tool.parameters, dict)
        catalog[tool.name] = {"inputSchema": tool.parameters}

    repo_root = Path(__file__).resolve().parents[2]
    assert Path.cwd() == tmp_path
    assert repo_root != Path.cwd()
    assert active_markdown_files(repo_root), "active Markdown discovery must not be empty"
    assert historical_markdown_files(repo_root), "historical Markdown discovery must not be empty"

    findings = lint_repository(repo_root, catalog)
    rendered = "\n".join(
        f"{finding.path}:{finding.line}: {finding.rule}: {finding.message}" for finding in findings
    )
    assert not findings, rendered
