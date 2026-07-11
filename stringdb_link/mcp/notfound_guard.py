"""FastMCP-core not-found reflection guard (Response-Envelope v1.1 fast-follow).

FastMCP core (pinned ``>=3.4.4,<4.0.0``) reflects the caller's OWN requested tool
name / resource URI / prompt name back to the caller (and to logs) BEFORE any
backend middleware runs. This module closes that residual with fixed, input-free
messages built from CONSTANTS only, mirroring the ratified fleet references
(``mondo``/``hpo`` registry preflight, ``clinvar`` protocol backstop,
``panelapp`` validation-log scrub filter; canonical ``autopvs1`` single-module).

The reflected text is *caller-supplied* (a caller self-reflection surface), so
this is materially lower-risk than the upstream-injection leak the prior sweep
closed. It is still worth closing: the reflected name/URI — with any
control/zero-width/bidi/NUL code point — lands in shared operator logs and in an
agent's tool-result context. Fixed constants remove the channel entirely.

Layers (spec §3), copied per repo (no shared runtime library exists fleet-wide):

* Layer 1 — ``on_call_tool`` registry preflight: ``get_tool(name)`` returns
  ``None`` for an unknown tool, so we return a fixed, name-free ``not_found``
  envelope BEFORE core dispatch. Closes the unknown-TOOL caller surface; never
  echoes ``_meta.tool``.
* Layer 2 — ``on_read_resource`` boundary: an unknown (URL-valid) resource makes
  core raise ``NotFoundError("Unknown resource: '<uri>'")``; we re-raise a fixed
  URI-free ``ResourceError``. (stringdb registers no author-authored resources,
  so every read failure is treated as untrusted.)
* Layer 3 — protocol-handler backstop: wraps the raw ``CallTool`` / ``ReadResource``
  / ``GetPrompt`` request handlers as the OUTERMOST layer. Replaces any non-envelope
  ``isError`` tool result (the unknown-tool *return* path this server takes) and
  re-raises fixed input-free messages for resource/prompt dispatch failures — the
  ONLY layer that covers the unknown-PROMPT surface.
* Layer 5 — validation-log scrub filter: FastMCP's pre-middleware and the MCP SDK
  session's request-validation logs echo the raw name/URI (with code points) on
  their own loggers/handlers. The filter neutralizes those records at the source
  logger so caller input never reaches a log sink.

Layer 4 (arg/error sanitation) is the existing error-passthrough + envelope
sanitation from the prior sweep (``error_passthrough.py`` / ``envelope.py``).
Layer 6 (OTel span redaction) is a no-op here: FastMCP pulls in
``opentelemetry-api`` transitively, but ``opentelemetry-sdk`` is absent, so the
tracer provider is non-recording — no span exception attributes are ever captured
(fleet policy: do NOT add the SDK dependency).

The unknown-tool result is the ONE place this server returns ``isError=True`` on
the wire (its normal error path is the in-band ``success:false`` frame). Setting
``isError`` short-circuits the FastMCP Client's output-schema validation, which
otherwise logs the hostile requested NAME via its own ``client`` logger (ratified
fleet contract: autopvs1/clinvar/gnomad).
"""

from __future__ import annotations

import json
import logging
from typing import Any, cast

import mcp.types
from fastmcp.exceptions import NotFoundError as FastMCPNotFoundError
from fastmcp.exceptions import ResourceError
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.base import ToolResult
from mcp.types import CallToolResult, TextContent

from stringdb_link.logging_config import get_logger
from stringdb_link.mcp.envelope import CAPABILITIES_VERSION, SOURCE, new_request_id

logger = get_logger("stringdb_notfound_guard")

# Fixed, input-free public messages. They NEVER contain the requested name/URI
# (nor a ``_meta.tool`` echo of it): sanitation strips code points but not
# injection prose, so a fixed constant is the only safe source (prior-sweep
# lesson). ``not_found`` reuses this repo's error-code vocabulary (envelope.py).
_UNKNOWN_TOOL_MESSAGE = "The requested tool is not available."
_UNKNOWN_RESOURCE_MESSAGE = "The requested resource is not available."
_UNKNOWN_PROMPT_MESSAGE = "The requested prompt is not available."
_UNKNOWN_TOOL_RECOVERY = (
    "Confirm the requested tool name against the server's advertised tool list."
)

#: Closed set of author-authored, code-point-free fixed ResourceError messages a
#: resource handler may legitimately surface. stringdb-link registers no such
#: resources, so the set is empty and every read failure is replaced with the
#: fixed generic message — the guard NEVER re-publishes ``str(exc)`` (sanitation
#: strips code points but preserves injection prose).
_KNOWN_RESOURCE_MESSAGES: frozenset[str] = frozenset()


class _UnknownToolResult(ToolResult):
    """A ``ToolResult`` that flips ``CallToolResult.isError=True`` on the wire.

    Dict-like accessors delegate to ``structured_content`` so tests that index
    the envelope keep working.
    """

    def __getitem__(self, key: str) -> Any:
        if self.structured_content is None:
            raise KeyError(key)
        return self.structured_content[key]

    def __contains__(self, key: object) -> bool:
        return self.structured_content is not None and key in self.structured_content

    def get(self, key: str, default: Any = None) -> Any:
        if self.structured_content is None:
            return default
        return self.structured_content.get(key, default)

    def to_mcp_result(self) -> CallToolResult:
        return CallToolResult(
            content=self.content,
            structuredContent=self.structured_content,
            isError=True,
            _meta=self.meta,
        )


def _unknown_tool_meta() -> dict[str, Any]:
    """Fixed provenance ``_meta`` for the unknown-tool envelope.

    Deliberately omits the ``tool`` key: the requested (caller-controlled) name
    is never reflected back on the wire.
    """
    return {
        "request_id": new_request_id(),
        "source": SOURCE,
        "capabilities_version": CAPABILITIES_VERSION,
        "unsafe_for_clinical_use": True,
    }


def unknown_tool_result() -> _UnknownToolResult:
    """Return a fixed, name-free ``not_found`` envelope for an unknown tool.

    Carries both ``structured_content`` and a matching TextContent JSON mirror,
    and flips ``isError=True`` on the wire.
    """
    payload: dict[str, Any] = {
        "success": False,
        "error_code": "not_found",
        "message": _UNKNOWN_TOOL_MESSAGE,
        "retryable": False,
        "recovery_action": _UNKNOWN_TOOL_RECOVERY,
        "_meta": _unknown_tool_meta(),
    }
    return _UnknownToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, separators=(",", ":")))],
        structured_content=payload,
        is_error=True,
    )


class NotFoundGuard(Middleware):
    """Layer 1 (tool preflight) + Layer 2 (resource boundary)."""

    async def on_call_tool(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, ToolResult],
    ) -> ToolResult:
        """Preflight the tool NAME; an unknown name never reaches core dispatch.

        ``get_tool`` returns ``None`` (it does not raise) for an unknown tool on
        this stack, so an unknown name is caught here and answered with a fixed,
        name-free envelope. If resolution raises, defer to the chain (Layer 3
        backstop catches the name-echoing return path).
        """
        fctx = getattr(context, "fastmcp_context", None)
        name = getattr(getattr(context, "message", None), "name", None)
        if fctx is not None and isinstance(name, str):
            try:
                tool = await fctx.fastmcp.get_tool(name)
            except Exception:
                tool = object()  # resolution failure: defer to core, do not mask
            if tool is None:
                logger.warning("mcp_unknown_tool")
                return unknown_tool_result()
        return await call_next(context)

    async def on_read_resource(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Emit a FIXED, URI-free error for a resource not-found / read failure.

        The requested URI is caller-controlled; FastMCP core echoes it
        (``Unknown resource: '<uri>'``) in both the direct exception and the
        protocol error. Re-raise a fixed message so the URI never reaches the
        caller/protocol. ``str(exc)`` is never re-published (it preserves
        injection prose); only author-authored fixed messages in the closed set
        pass through.
        """
        try:
            return await call_next(context)
        except FastMCPNotFoundError:
            logger.warning("mcp_resource_not_found")
            raise ResourceError(_UNKNOWN_RESOURCE_MESSAGE) from None
        except ResourceError as exc:
            if str(exc) in _KNOWN_RESOURCE_MESSAGES:
                raise
            logger.warning("mcp_resource_error", error_type=type(exc).__name__)
            raise ResourceError(_UNKNOWN_RESOURCE_MESSAGE) from None
        except Exception as exc:
            logger.warning("mcp_resource_error", error_type=type(exc).__name__)
            raise ResourceError(_UNKNOWN_RESOURCE_MESSAGE) from None


# ---------------------------------------------------------------------------
# Layer 3 — protocol-handler backstop (clinvar/autopvs1 pattern)
# ---------------------------------------------------------------------------


class ProtocolError(Exception):
    """A dispatch-level failure re-raised with a FIXED, input-free message."""


def _is_structured_envelope(call_result: mcp.types.CallToolResult) -> bool:
    """True if an ``isError`` result carries one of OUR JSON envelopes.

    Distinguishes a structured stringdb-link error (already input-free — it has
    an ``error_code``) from a RAW FastMCP dispatch error whose plain-text message
    echoes the caller-supplied tool name (``Unknown tool: '<name>'``).
    """
    if not call_result.content:
        return False
    text = getattr(call_result.content[0], "text", None)
    if not isinstance(text, str):
        return False
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return False
    return isinstance(obj, dict) and "error_code" in obj


def _fixed_tool_not_found_result() -> mcp.types.ServerResult:
    """A fixed, input-free ServerResult for an unknown/failed tool dispatch."""
    return mcp.types.ServerResult(unknown_tool_result().to_mcp_result())


def install_protocol_error_handler(mcp_server: Any) -> None:
    """Wrap the tool/resource/prompt request handlers as the OUTERMOST layer.

    A FastMCP core not-found (or read) error can no longer reflect the
    caller-supplied name/URI. Install AFTER all tools/resources/prompts are
    registered so the handlers exist.
    """
    handlers = mcp_server._mcp_server.request_handlers

    call_tool = handlers.get(mcp.types.CallToolRequest)
    if call_tool is not None:

        async def wrapped_call_tool(
            request: mcp.types.CallToolRequest,
            *,
            _orig: Any = call_tool,
        ) -> mcp.types.ServerResult:
            try:
                result = cast(mcp.types.ServerResult, await _orig(request))
            except FastMCPNotFoundError:
                return _fixed_tool_not_found_result()
            # FastMCP *returns* an isError CallToolResult with a raw plain-text
            # message ("Unknown tool: '<name>'") for an unknown tool; replace any
            # isError result that is NOT one of our structured envelopes.
            root = getattr(result, "root", None)
            if (
                isinstance(root, mcp.types.CallToolResult)
                and root.isError
                and not _is_structured_envelope(root)
            ):
                return _fixed_tool_not_found_result()
            return result

        handlers[mcp.types.CallToolRequest] = wrapped_call_tool

    for request_type, message in (
        (mcp.types.ReadResourceRequest, _UNKNOWN_RESOURCE_MESSAGE),
        (mcp.types.GetPromptRequest, _UNKNOWN_PROMPT_MESSAGE),
    ):
        orig = handlers.get(request_type)
        if orig is None:
            continue

        async def wrapped(
            request: Any,
            *,
            _orig: Any = orig,
            _message: str = message,
        ) -> Any:
            try:
                return await _orig(request)
            except Exception:
                # Re-raise with a FIXED, input-free message so no requested
                # name/URI (or its code points) reaches the JSON-RPC error frame.
                raise ProtocolError(_message) from None

        handlers[request_type] = wrapped


# ---------------------------------------------------------------------------
# Layer 5 — validation-log scrub filter (panelapp/autopvs1 pattern)
# ---------------------------------------------------------------------------
#
# Each entry is a substring in the ``record.msg`` (format string) of a FastMCP-core
# or MCP-SDK log line that reflects the caller-supplied name/URI. Matching on
# ``msg`` covers both an interpolated f-string and a ``record.args`` payload,
# because the scrub clears the args too.
_SCRUB_MARKERS: tuple[str, ...] = (
    "Handler called: call_tool",
    "Handler called: read_resource",
    "Handler called: get_prompt",
    "Invalid arguments for tool",
    "Error calling tool",
    "Error reading resource",
    "Failed to validate request",
    "Message that failed validation",
    "Tool cache miss for",
)

# The source loggers on which those records are CREATED. A logging filter must be
# attached to the originating logger (or its handlers): logger-level filters are
# skipped during propagation, but HANDLER-level filters DO run during propagation.
# ``fastmcp`` is FastMCP's non-propagating parent (its own Rich handlers): attaching
# there — and to its handlers — scrubs at the handler level any record that
# propagates up from a child logger. ``""`` (root) catches the MCP SDK session's
# request-validation failures.
_SCRUB_LOGGERS: tuple[str, ...] = (
    "",  # root — mcp.shared.session request-validation failures
    "fastmcp",  # non-propagating parent + its Rich handlers (handler-level scrub)
    "fastmcp.server.server",
    "fastmcp.server.mixins.mcp_operations",
    "mcp.server.lowlevel.server",
    "mcp.shared.session",
)

_SCRUBBED_MESSAGE = "MCP request rejected (details omitted)."


class _ValidationLogScrubFilter(logging.Filter):
    """Scrub log records that would echo a caller-supplied tool name / URI.

    Replaces the record payload with fixed metadata (clearing ``args`` /
    ``exc_info`` / ``exc_text`` / ``stack_info``) so the caller-chosen name/URI —
    and any control/zero-width/bidi/NUL code points it carries — can never reach
    a log or telemetry sink. Always returns ``True``: the (now input-free) record
    is still emitted for operational visibility.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.msg if isinstance(record.msg, str) else ""
        if any(marker in msg for marker in _SCRUB_MARKERS):
            record.msg = _SCRUBBED_MESSAGE
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


def install_validation_log_filter() -> None:
    """Idempotently attach the scrub filter to each source logger (and handlers)."""
    for name in _SCRUB_LOGGERS:
        target = logging.getLogger(name)
        if not any(isinstance(f, _ValidationLogScrubFilter) for f in target.filters):
            target.addFilter(_ValidationLogScrubFilter())
        for handler in target.handlers:
            if not any(isinstance(f, _ValidationLogScrubFilter) for f in handler.filters):
                handler.addFilter(_ValidationLogScrubFilter())
