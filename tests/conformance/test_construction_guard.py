"""Construction guard: asserts server_manager uses the correct MCP transport pattern.

These tests fail until server_manager.py is updated to:
  - call http_app(path=settings.mcp_path, stateless_http=True, json_response=True)
  - mount the MCP app at root: app.mount("/", mcp_http_app)
"""

from __future__ import annotations

import inspect

from stringdb_link import server_manager


def test_mcp_app_is_rooted_stateless_json() -> None:
    src = inspect.getsource(server_manager)
    assert 'http_app(path="/")' not in src, "must bake the mcp_path, not path='/'"
    assert "stateless_http=True" in src, "stateless_http=True must be set"
    assert "json_response=True" in src, "json_response=True must be set"
    assert 'mount("/"' in src, "mount the MCP app at root, not at settings.mcp_path"
