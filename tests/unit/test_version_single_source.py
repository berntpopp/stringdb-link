"""Guard: pyproject -> installed metadata -> __version__ -> MCP serverInfo are one value.

Single-source versioning for stringdb-link. The canonical version lives ONLY in
``pyproject.toml [project].version``; ``__version__`` derives from installed
metadata; and the FastMCP server (built by ``create_mcp_app``) must advertise
that same value as ``serverInfo.version`` on ``initialize`` — not the FastMCP
framework version.
"""

from __future__ import annotations

import tomllib
from importlib.metadata import version
from pathlib import Path

from stringdb_link import __version__
from stringdb_link.app import create_mcp_app

DIST = "stringdb-link"


def _pyproject_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]


def test_pyproject_is_the_single_source() -> None:
    assert version(DIST) == _pyproject_version()


def test_dunder_version_is_metadata_derived() -> None:
    assert __version__ == version(DIST)


def test_mcp_server_info_version_matches_package() -> None:
    assert create_mcp_app().version == version(DIST)
