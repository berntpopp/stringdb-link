"""GeneFoundry Response-Envelope Standard v1 — the flat banner frame.

Reshapes stringdb-link's OpenAPI-generated MCP tool responses into the
fleet-wide envelope (see ``docs/RESPONSE-ENVELOPE-STANDARD-v1.md`` on the
``genefoundry-router-standards`` repo):

- Success, collection tool: ``{"success": true, "results": [...], "_meta": {...}}``
- Success, single-item tool: ``{"success": true, "result": {...}, "_meta": {...}}``
- Failure (flat, in-band): ``{"success": false, "error_code": ..., "message": ...,
  "retryable": ..., "recovery_action": ..., "_meta": {...}}``

This module is REST-agnostic: it operates only on the plain JSON dict a FastAPI
route already returned (as extracted by ``stringdb_link.mcp.error_passthrough``).
The REST API surface is untouched — this is an MCP ``structuredContent``
contract, not a REST response-body contract.

Mirrors the fleet's conformant exemplar (genereviews-link / clingen-link):
errors are RETURNED as structured content (``success: false`` in-band) rather
than raised as an opaque ``ToolError`` text blob. The installed FastMCP 3.3.1 /
mcp SDK give no supported way to combine a wire-level ``isError: true`` with a
populated ``structuredContent`` on the return path (raising loses
``structuredContent`` entirely), so — like the rest of the fleet — we rely on
the in-band ``success`` flag rather than the wire ``isError`` bit.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

# Static provenance stamp bumped when the tool surface / envelope shape changes
# in a way a warm client should re-fetch metadata for. No capabilities tool
# exists yet on this server, so this is provenance, not a live value.
CAPABILITIES_VERSION = "1"

SOURCE = "stringdb"

# Closed error-code enum (Response-Envelope Standard v1 §2), harmonized with the
# codes used fleet-wide (e.g. clingen-link's ``internal_error``).
ErrorCode = Literal[
    "invalid_input",
    "not_found",
    "ambiguous_query",
    "upstream_unavailable",
    "rate_limited",
    "internal_error",
]


@dataclass(frozen=True)
class _ToolSpec:
    """How to reshape one tool's raw REST JSON body into the envelope frame."""

    kind: Literal["single", "collection"]
    # For "collection" tools, the raw wrapper-model key holding the list
    # (e.g. StringIdMappingListResponse.mappings). Promoted to top-level
    # ``results``; any sibling keys (e.g. ``total_count``) ride beside it.
    source_key: str | None = None


# One entry per MCP tool generated from stringdb_link/api/routes/*.py (tool name
# == route operation_id). "single" tools nest their whole raw payload under
# ``result``; "collection" tools promote ``source_key`` to top-level ``results``.
PRIMARY_KEY_MAP: dict[str, _ToolSpec] = {
    "resolve_protein_identifiers": _ToolSpec(kind="collection", source_key="mappings"),
    "search_protein_interactions": _ToolSpec(kind="collection", source_key="interactions"),
    "get_interaction_partners": _ToolSpec(kind="collection", source_key="partners"),
    "compute_functional_enrichment": _ToolSpec(kind="collection", source_key="terms"),
    "get_functional_annotations": _ToolSpec(kind="collection", source_key="annotations"),
    "get_protein_homology_scores": _ToolSpec(kind="collection", source_key="scores"),
    "get_protein_homology_best_hits": _ToolSpec(kind="collection", source_key="scores"),
    "compute_ppi_enrichment": _ToolSpec(kind="single"),
    "get_network_link": _ToolSpec(kind="single"),
    "get_network_image": _ToolSpec(kind="single"),
}

_DEFAULT_SPEC = _ToolSpec(kind="single")

# Classify a REST HTTP status into the closed enum + retryable flag. stringdb
# routes emit 400 (validation), 429 (rate limit), 500 (genuine internal error:
# "Internal server error during ..."), and 502/503/504 (upstream STRING API
# outage / parse failure). 500 therefore maps to a NON-retryable internal_error,
# distinct from the retryable upstream 5xx bucket.
_STATUS_CODE_MAP: dict[int, tuple[ErrorCode, bool]] = {
    400: ("invalid_input", False),
    404: ("not_found", False),
    409: ("ambiguous_query", False),
    413: ("invalid_input", False),
    422: ("invalid_input", False),
    429: ("rate_limited", True),
    500: ("internal_error", False),
    502: ("upstream_unavailable", True),
    503: ("upstream_unavailable", True),
    504: ("upstream_unavailable", True),
}

_GENERIC_RECOVERY_ACTION: dict[ErrorCode, str] = {
    "invalid_input": "Reformulate the request; an argument shape or value was rejected.",
    "not_found": "Confirm the protein identifier(s) and species; call "
    "resolve_protein_identifiers to discover valid STRING IDs.",
    "ambiguous_query": "Narrow the query so it resolves to a single result.",
    "upstream_unavailable": "Retry with backoff; the upstream STRING API was unavailable.",
    "rate_limited": "Retry after backing off; the STRING API request rate was exceeded.",
    "internal_error": "Retry once; if the error persists the request could not be completed.",
}


def new_request_id() -> str:
    """Return a fresh opaque request id for one MCP tool invocation."""
    return uuid.uuid4().hex


def _augment_meta(
    meta: dict[str, Any],
    *,
    tool_name: str,
    request_id: str,
    elapsed_ms: float,
) -> dict[str, Any]:
    """Merge envelope-required provenance into an existing ``_meta`` block."""
    augmented = dict(meta)
    augmented["tool"] = tool_name
    augmented["request_id"] = request_id
    augmented["elapsed_ms"] = round(elapsed_ms, 3)
    augmented["source"] = SOURCE
    augmented["capabilities_version"] = CAPABILITIES_VERSION
    augmented["unsafe_for_clinical_use"] = True
    return augmented


def build_success_envelope(
    tool_name: str,
    raw: dict[str, Any],
    *,
    request_id: str,
    elapsed_ms: float,
) -> dict[str, Any]:
    """Reshape a raw REST JSON body into the success frame.

    ``raw`` is the tool's already-unwrapped REST response body (a plain dict).
    Collection tools promote their list under ``results`` and keep any sibling
    keys (e.g. ``total_count``) beside it (Rule 1: "MAY add domain keys beside
    results/result"); single tools nest the whole body under ``result``.
    """
    spec = PRIMARY_KEY_MAP.get(tool_name, _DEFAULT_SPEC)
    working = dict(raw)
    meta = working.pop("_meta", None)
    if not isinstance(meta, dict):
        meta = {}

    envelope: dict[str, Any] = {"success": True}
    if spec.kind == "collection":
        source_key = spec.source_key or "results"
        items = working.pop(source_key, [])
        envelope["results"] = items
        # Remaining domain keys (e.g. total_count) ride beside `results`.
        envelope.update(working)
    else:
        envelope["result"] = working

    envelope["_meta"] = _augment_meta(
        meta, tool_name=tool_name, request_id=request_id, elapsed_ms=elapsed_ms
    )
    return envelope


def build_error_envelope(
    tool_name: str,
    *,
    status_code: int,
    message: str,
    request_id: str,
    elapsed_ms: float,
) -> dict[str, Any]:
    """Build the flat, in-band error frame (Response-Envelope Standard v1 §2).

    stringdb-link routes raise ``HTTPException`` with a plain-string ``detail``
    (no structured ``code`` body), so classification is purely status-driven and
    ``message`` is the sanitized route detail.
    """
    error_code, retryable = classify_status(status_code)
    envelope: dict[str, Any] = {
        "success": False,
        "error_code": error_code,
        "message": message,
        "retryable": retryable,
        "recovery_action": _GENERIC_RECOVERY_ACTION[error_code],
    }
    envelope["_meta"] = _augment_meta(
        {}, tool_name=tool_name, request_id=request_id, elapsed_ms=elapsed_ms
    )
    return envelope


def classify_status(status_code: int) -> tuple[ErrorCode, bool]:
    """Map an HTTP status to ``(error_code, retryable)`` in the closed enum."""
    if status_code in _STATUS_CODE_MAP:
        return _STATUS_CODE_MAP[status_code]
    if status_code >= 500:
        return "upstream_unavailable", True
    return "internal_error", False


def reshape_output_schema(schema: dict[str, Any] | None) -> dict[str, Any]:
    """Return a permissive envelope-shaped ``outputSchema`` for one tool.

    The low-level MCP SDK validates ``structuredContent`` against the tool's
    declared ``outputSchema`` on every call, so it must accept BOTH the success
    frame (``results``/``result`` + domain siblings) and the error frame
    (``error_code``/``message``/``retryable``/``recovery_action``) that share the
    one ``outputSchema`` slot. Declare an object requiring only ``success`` +
    ``_meta`` and permissive on the rest. Any ``$defs``/``definitions`` from the
    original FastAPI-derived schema are copied across best-effort (FastMCP's own
    downstream ``prune_defs`` pass drops unreferenced defs, which is fine — deep
    per-record shape is exercised behaviorally, not via declared-schema
    introspection).
    """
    preserved_defs: dict[str, Any] = {}
    if schema:
        for key in ("$defs", "definitions"):
            value = schema.get(key)
            if isinstance(value, dict):
                preserved_defs[key] = value

    envelope_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "_meta": {"type": "object"},
        },
        "required": ["success", "_meta"],
        "additionalProperties": True,
    }
    envelope_schema.update(preserved_defs)
    return envelope_schema
