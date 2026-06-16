"""Fixtures for unit tests.

Provides a FastMCP ``facade`` built from the FastAPI app via
``FastMCP.from_fastapi`` so tests can assert on the registered MCP tool surface
(the names the gateway will see).
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def facade() -> Any:
    """A FastMCP facade exposing the registered MCP tools for this server."""
    from stringdb_link.app import create_mcp_app

    return create_mcp_app()
