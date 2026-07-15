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
    """Return a fixed, classification-keyed message. NEVER reads the response body.

    The response body -- whether the local FastAPI/ASGI error body or any
    ``httpx.Response`` surfaced from the exception's cause/context chain by
    ``_find_http_status_response`` -- is caller-influenceable: a route may
    interpolate an upstream/exception string into its ``{"detail": ...}`` and an
    upstream body can carry injection PROSE that survives code-point sanitization.
    So the body is never parsed or echoed here; the caller-visible message is
    derived ONLY from the HTTP status (see ``envelope.safe_error_message``), the
    one safe, non-attacker-controlled scalar. ``build_error_envelope`` additionally
    strips forbidden code points as a defensive backstop.
    """
    return envelope.safe_error_message(response.status_code)


def _validation_field_names(response: httpx.Response) -> list[str]:
    """Extract offending parameter name(s) from a local request-validation body.

    ONLY the FastAPI/Starlette 4xx validation shape ``{"detail": [{"loc": [...]}]}``
    is parsed, and ONLY the ``loc`` leaf under ``body``/``query``/``path`` is read —
    i.e. this server's own schema parameter names, never the caller-supplied value
    (``input``), the human message (``msg``), or any upstream STRING error body
    (which is HTTP 200 or lacks this shape). This is the one attacker-safe scalar in
    the body: it lets the error name the parameter without echoing any prose. Any
    parse failure yields no names (fail-closed).
    """
    try:
        payload = response.json()
    except Exception:
        return []
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if not isinstance(detail, list):
        return []
    names: list[str] = []
    for item in detail:
        loc = item.get("loc") if isinstance(item, dict) else None
        if not isinstance(loc, list) or not loc:
            continue
        # The leaf of the loc path is the offending parameter name (FastAPI prefixes
        # it with body/query/path). It is this server's own schema name — safe to
        # surface, unlike the caller value or upstream prose.
        leaf = loc[-1]
        if isinstance(leaf, str) and leaf not in names:
            names.append(leaf)
    return names


def _build_error_envelope_from_exception(
    tool_name: str, exc: Exception, elapsed_ms: float
) -> dict[str, Any]:
    """Convert any exception raised during a tool's REST call into the error frame."""
    request_id = envelope.new_request_id()
    response = _find_http_status_response(exc)
    if response is None:
        # No HTTP response anywhere in the chain: a connection-level failure or a
        # non-HTTP bug (e.g. the image route's binary body defeating the JSON
        # provider). Route it through a non-retryable internal error with a
        # generic message (mask_error_details posture — no internal text leaks).
        return envelope.build_error_envelope(
            tool_name,
            status_code=500,
            message=_GENERIC_INTERNAL_MESSAGE,
            request_id=request_id,
            elapsed_ms=elapsed_ms,
        )
    field_errors: list[str] = []
    if response.status_code in (400, 422):
        field_errors = _validation_field_names(response)
    return envelope.build_error_envelope(
        tool_name,
        status_code=response.status_code,
        message=_fallback_message(response),
        request_id=request_id,
        elapsed_ms=elapsed_ms,
        field_errors=field_errors,
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

    # Tool-Surface Budget Standard v1 Rule 3: suppress outputSchema. It is optional
    # in MCP, no model reads it, and it is pure per-request surface. Setting it to
    # None also removes the low-level SDK's per-call structuredContent validation,
    # so both the success and error frames pass freely. structuredContent is still
    # emitted (every tool returns a dict envelope; verified fastmcp 3.4.4
    # tools/base.py:357-361). Untrusted-text fencing is UNAFFECTED: it happens on
    # the wire in build_success_envelope; Response-Envelope Standard v1.1a requires
    # the fenced object on the wire and only requires a schema declaration IF a
    # schema is published — which it no longer is.
    object.__setattr__(component, "output_schema", None)

    original_run = component.run
    tool_name = component.name

    async def run_with_structured_errors(arguments: dict[str, Any]) -> ToolResult:
        start = time.perf_counter()
        try:
            result = await original_run(arguments)
        except Exception as exc:  # all failures become the flat error frame
            elapsed_ms = (time.perf_counter() - start) * 1000
            error_envelope = _build_error_envelope_from_exception(tool_name, exc, elapsed_ms)
            # is_error=True gives the wire-level MCP ``isError`` bit alongside the
            # structured envelope (Response-Envelope Standard v1). Verified against
            # fastmcp 3.4.4: the RETURN path keeps structuredContent (only ``raise``
            # would drop it). Without this a client branching on ``isError`` sees a
            # failed call as a success.
            return ToolResult(structured_content=error_envelope, is_error=True)

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
