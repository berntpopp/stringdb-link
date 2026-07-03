"""Structured error passthrough for FastMCP OpenAPI-generated tools.

Wraps every OpenAPI-generated stringdb-link tool so its ``run()`` always returns
a Response-Envelope Standard v1 frame (see ``stringdb_link.mcp.envelope``) as
``structuredContent`` — the flat success banner on the happy path, the flat
in-band error frame on failure — and attaches uniform read-only annotations.

Wired via ``FastMCP.from_fastapi(..., mcp_component_fn=wrap_structured_error_tools)``
in ``stringdb_link.app.create_mcp_app``. The FastAPI/REST routes are never
touched: this only reshapes what MCP callers see.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from fastmcp.server.providers.openapi import OpenAPITool
from fastmcp.tools.base import ToolResult

from stringdb_link.mcp import envelope
from stringdb_link.mcp.annotations import READ_ONLY_OPEN_WORLD

_GENERIC_INTERNAL_MESSAGE = "An internal error occurred while processing the request."


def _find_http_status_response(exc: BaseException) -> httpx.Response | None:
    """Find an httpx response in an exception's cause/context chain."""
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, httpx.HTTPStatusError):
            return current.response
        response = getattr(current, "response", None)
        if isinstance(response, httpx.Response):
            return response
        current = current.__cause__ or current.__context__
    return None


def _fallback_message(response: httpx.Response) -> str:
    """Best-effort human-readable message from a FastAPI error response body.

    stringdb-link routes raise ``HTTPException(status_code, detail="...")`` which
    FastAPI renders as ``{"detail": "<string>"}`` (or ``{"detail": [ ... ]}`` for
    422 validation). The detail text is route-controlled and already sanitized.
    """
    try:
        body = response.json()
    except ValueError:
        text = response.text.strip()
        return text[:300] if text else f"HTTP {response.status_code}"

    if isinstance(body, dict):
        detail = body.get("detail")
        if isinstance(detail, str) and detail:
            return detail[:300]
        if isinstance(detail, list) and detail:
            parts: list[str] = []
            for item in detail:
                if isinstance(item, dict) and item.get("msg"):
                    loc = ".".join(str(p) for p in item.get("loc", []))
                    parts.append(f"{loc}: {item['msg']}" if loc else str(item["msg"]))
            if parts:
                return "; ".join(parts)[:300]
        for key in ("message", "error"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value[:300]
    return f"HTTP {response.status_code}"


def _build_error_envelope_from_exception(
    tool_name: str, exc: Exception, elapsed_ms: float
) -> dict[str, Any]:
    """Convert any exception raised during a tool's REST call into the error frame."""
    request_id = envelope.new_request_id()
    response = _find_http_status_response(exc)
    if response is None:
        # No HTTP response anywhere in the chain: a connection-level failure or a
        # non-HTTP bug (e.g. the image route's binary body defeating the JSON
        # provider). Route it through a non-retryable internal_error with a
        # generic message (mask_error_details posture — no internal text leaks).
        return envelope.build_error_envelope(
            tool_name,
            status_code=500,
            message=_GENERIC_INTERNAL_MESSAGE,
            request_id=request_id,
            elapsed_ms=elapsed_ms,
        )
    return envelope.build_error_envelope(
        tool_name,
        status_code=response.status_code,
        message=_fallback_message(response),
        request_id=request_id,
        elapsed_ms=elapsed_ms,
    )


def wrap_structured_error_tools(route: Any, component: Any) -> None:
    """Wrap a generated OpenAPI tool so every result is a Response-Envelope
    Standard v1 frame, and attach uniform read-only annotations.

    Called by the FastMCP OpenAPI provider as ``mcp_component_fn(route, tool)``
    for each component (tools, resources, templates); no-op for non-tools.
    """
    if not isinstance(component, OpenAPITool):
        return

    # Every stringdb-link tool is a read-only STRING lookup against an
    # externally-evolving, open-world database — none mutate state.
    object.__setattr__(component, "annotations", READ_ONLY_OPEN_WORLD)

    # Declare an envelope-shaped outputSchema so the low-level MCP SDK's
    # per-call structuredContent validation accepts both the success and error
    # frames (see envelope.reshape_output_schema).
    object.__setattr__(
        component, "output_schema", envelope.reshape_output_schema(component.output_schema)
    )

    original_run = component.run
    tool_name = component.name

    async def run_with_structured_errors(arguments: dict[str, Any]) -> ToolResult:
        start = time.perf_counter()
        try:
            result = await original_run(arguments)
        except Exception as exc:  # all failures become the flat error frame
            elapsed_ms = (time.perf_counter() - start) * 1000
            error_envelope = _build_error_envelope_from_exception(tool_name, exc, elapsed_ms)
            return ToolResult(structured_content=error_envelope)

        elapsed_ms = (time.perf_counter() - start) * 1000
        raw = result.structured_content if isinstance(result.structured_content, dict) else {}
        success_envelope = envelope.build_success_envelope(
            tool_name,
            raw,
            request_id=envelope.new_request_id(),
            elapsed_ms=elapsed_ms,
        )
        return ToolResult(structured_content=success_envelope)

    object.__setattr__(component, "run", run_with_structured_errors)
