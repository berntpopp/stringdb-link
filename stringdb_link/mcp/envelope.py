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
than raised as an opaque ``ToolError`` text blob. Verified against the installed
FastMCP 3.4.4, ``ToolResult(structured_content=envelope, is_error=True)`` carries
BOTH the wire-level ``isError: true`` bit AND the populated ``structuredContent``
frame on the return path — so the error carrier
(``stringdb_link.mcp.error_passthrough``) sets ``is_error=True`` and clients that
branch on the protocol ``isError`` bit see the failure, exactly as
Response-Envelope Standard v1 requires. (Only the ``raise`` path loses
``structuredContent``; the return path does not.)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal, cast

from stringdb_link.mcp.untrusted_content import (
    UntrustedText,
    enforce_untrusted_text_limits,
    fence_untrusted_text,
    sanitize_message,
)

# Static provenance stamp bumped when the tool surface / envelope shape changes
# in a way a warm client should re-fetch metadata for. No capabilities tool
# exists yet on this server, so this is provenance, not a live value.
CAPABILITIES_VERSION = "1"

SOURCE = "stringdb"

# GeneFoundry Response-Envelope Standard v1.1 — untrusted-content fencing.
#
# One entry per MCP tool that carries an externally sourced free-text field
# (see genefoundry-router/docs/conformance/untrusted-text-inventory.yml,
# backend: stringdb): ``(json key holding the raw prose, json key holding the
# record's stable STRING/GO/KEGG id)``. Interaction/homology scores are
# numeric and never appear here.
UNTRUSTED_TEXT_FIELDS: dict[str, tuple[str, str]] = {
    "resolve_protein_identifiers": ("annotation", "stringId"),
    "compute_functional_enrichment": ("description", "term"),
    "get_functional_annotations": ("description", "term"),
}

# STRING enrichment/annotation result lists are the tool's real result cap, not
# the bare v1.1 default of 128: a large input gene set can legitimately surface
# many GO/KEGG terms in one call. The 2 MiB/object and 8 MiB/total byte limits
# stay at their v1.1 defaults — they are the real DoS backstop.
_UNTRUSTED_TEXT_MAX_OBJECTS = 10_000


def _untrusted_text_object_defs() -> dict[str, Any]:
    """Return the ``$defs`` graph for the ``UntrustedText`` object.

    Hoists ``UntrustedText``'s own nested ``$defs`` (``UntrustedTextProvenance``)
    to the top level so its ``#/$defs/UntrustedTextProvenance`` ``$ref`` still
    resolves once embedded in a tool's ``outputSchema``. A fresh dict is built
    per call so FastMCP's downstream ``prune_defs`` pass cannot mutate a shared
    object across the fenced tools.
    """
    schema = UntrustedText.model_json_schema()
    nested = schema.pop("$defs", {})
    defs: dict[str, Any] = {"UntrustedText": schema}
    defs.update(nested)
    return defs


# Closed error-code enum (Response-Envelope Standard v1 §2). Exactly the six
# canonical fleet codes — the behaviour gate (docs/conformance/behaviour.py)
# rejects anything outside this set. ``internal`` (not ``internal_error``) is the
# canonical spelling for a non-retryable server-side failure.
ErrorCode = Literal[
    "invalid_input",
    "not_found",
    "ambiguous_query",
    "upstream_unavailable",
    "rate_limited",
    "internal",
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
    500: ("internal", False),
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
    "internal": "Retry once; if the error persists the request could not be completed.",
}

# Fixed, server-authored, body-free error messages keyed by the classified code.
# The caller-visible ``message`` is derived ONLY from the HTTP status/classification
# -- NEVER from a response body. An upstream (or FastAPI/ASGI) error body is
# caller-influenceable: it can carry injection PROSE that survives code-point
# sanitization, so it is severed here at the boundary rather than echoed. The HTTP
# status is the one safe, non-attacker-controlled scalar we derive the message from.
_SAFE_ERROR_MESSAGE: dict[ErrorCode, str] = {
    "invalid_input": "The request was rejected as invalid.",
    "not_found": "The requested record was not found.",
    "ambiguous_query": "The query was ambiguous; narrow it to a single result.",
    "upstream_unavailable": "The upstream STRING API is unavailable.",
    "rate_limited": "The STRING API request rate was exceeded.",
    "internal": "An internal error occurred while processing the request.",
}


def safe_error_message(status_code: int) -> str:
    """Return a fixed, server-authored message for an HTTP status.

    Never derived from a response body: only the status is classified. This is the
    boundary guarantee that no attacker-influenceable upstream/error-body prose can
    reach an MCP caller through the error ``message``.
    """
    error_code, _ = classify_status(status_code)
    return _SAFE_ERROR_MESSAGE[error_code]


def new_request_id() -> str:
    """Return a fresh opaque request id for one MCP tool invocation."""
    return uuid.uuid4().hex


def _fence_collection_field(
    items: list[Any],
    *,
    text_field: str,
    record_id_field: str,
) -> None:
    """Reshape one bare-string prose field into a v1.1 ``untrusted_text`` object.

    Mutates ``items`` in place: STRING protein annotations and GO/KEGG
    enrichment/annotation term descriptions are externally sourced free text
    and must never reach an MCP caller as a bare string. The raw string is
    replaced by the typed object at the same key — no sibling field carries a
    duplicate copy of the raw or sanitized prose.
    """
    fenced: list[UntrustedText] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw = item.get(text_field)
        if not isinstance(raw, str):
            continue
        record_id = str(item.get(record_id_field, ""))
        obj = fence_untrusted_text(raw, source=SOURCE, record_id=record_id)
        fenced.append(obj)
        item[text_field] = obj.model_dump(mode="json")
    enforce_untrusted_text_limits(fenced, max_objects=_UNTRUSTED_TEXT_MAX_OBJECTS)


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
        fence_fields = UNTRUSTED_TEXT_FIELDS.get(tool_name)
        if fence_fields is not None and isinstance(items, list):
            _fence_collection_field(
                items, text_field=fence_fields[0], record_id_field=fence_fields[1]
            )
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
    field_errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build the flat, in-band error frame (Response-Envelope Standard v1 §2).

    stringdb-link routes raise ``HTTPException`` with a plain-string ``detail``
    (no structured ``code`` body), so classification is purely status-driven and
    ``message`` is the sanitized route detail. The message is run through
    :func:`sanitize_message` here as a belt-and-suspenders backstop so no forbidden
    control/zero-width/bidi/NUL code point reaches the caller by any error path,
    even if a caller passes an unsanitized string.

    ``field_errors`` (when supplied) names the offending input parameter(s). It is
    derived ONLY from the request-validation ``loc`` path — i.e. this server's own
    schema parameter names, never any caller/upstream prose — so an LLM can
    self-correct (Response-Envelope Standard v1: an error must be actionable). Each
    name is sanitized as a defensive backstop.
    """
    error_code, retryable = classify_status(status_code)
    envelope: dict[str, Any] = {
        "success": False,
        "error_code": error_code,
        "message": sanitize_message(message),
        "retryable": retryable,
        "recovery_action": _GENERIC_RECOVERY_ACTION[error_code],
    }
    if field_errors:
        cleaned = [sanitize_message(str(name))[:64] for name in field_errors if str(name)]
        if cleaned:
            envelope["field_errors"] = cleaned
            envelope["field"] = cleaned[0]
    envelope["_meta"] = _augment_meta(
        {}, tool_name=tool_name, request_id=request_id, elapsed_ms=elapsed_ms
    )
    return envelope


#: The six canonical error codes (keys of the message map are exactly the enum).
_ERROR_CODE_SET: frozenset[str] = frozenset(_SAFE_ERROR_MESSAGE)


def is_error_payload(raw: object) -> bool:
    """True if a tool's returned payload is already an error frame (``success: false``).

    Such a payload must be surfaced with the wire-level ``isError`` bit set, not
    wrapped as a success — otherwise a client branching on ``isError`` sees a failure
    reported as a successful call.
    """
    return isinstance(raw, dict) and raw.get("success") is False


def build_returned_error_envelope(
    tool_name: str,
    raw: dict[str, Any],
    *,
    request_id: str,
    elapsed_ms: float,
) -> dict[str, Any]:
    """Normalize a tool-RETURNED ``{"success": false, ...}`` payload into the error
    frame, closing ``error_code`` to the canonical enum and re-augmenting ``_meta``.

    Distinct from :func:`build_error_envelope` (which classifies from an HTTP status):
    here the payload already carries an ``error_code``/``message``, so they are
    preserved when valid and defaulted when not. All caller-derived strings are
    sanitized; an off-enum ``error_code`` collapses to ``internal``.
    """
    code = raw.get("error_code")
    error_code: ErrorCode = cast("ErrorCode", code) if code in _ERROR_CODE_SET else "internal"
    raw_message = raw.get("message")
    message = (
        sanitize_message(raw_message)
        if isinstance(raw_message, str) and raw_message
        else _SAFE_ERROR_MESSAGE[error_code]
    )
    retryable = raw.get("retryable")
    if not isinstance(retryable, bool):
        retryable = error_code in ("upstream_unavailable", "rate_limited")
    recovery = raw.get("recovery_action")
    if not isinstance(recovery, str) or not recovery:
        recovery = _GENERIC_RECOVERY_ACTION[error_code]

    envelope: dict[str, Any] = {
        "success": False,
        "error_code": error_code,
        "message": message,
        "retryable": retryable,
        "recovery_action": recovery,
    }
    field_errors = raw.get("field_errors")
    if isinstance(field_errors, list):
        cleaned = [sanitize_message(str(n))[:64] for n in field_errors if str(n)]
        if cleaned:
            envelope["field_errors"] = cleaned
            envelope["field"] = cleaned[0]
    elif isinstance(raw.get("field"), str) and raw["field"]:
        envelope["field"] = sanitize_message(raw["field"])[:64]
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
    return "internal", False


def reshape_output_schema(
    schema: dict[str, Any] | None, tool_name: str | None = None
) -> dict[str, Any]:
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

    When ``tool_name`` fences an untrusted-text field (``UNTRUSTED_TEXT_FIELDS``),
    the ``results`` array is declared with a list-item schema whose fenced
    pointer ``$ref``s the ``UntrustedText`` object, so the LIVE tool schema
    (``list_tools``) advertises ``kind: const "untrusted_text"`` at the fenced
    field — not the bare ``string`` the original OpenAPI ``$defs`` typed it as.
    The original per-record ``$defs`` are intentionally dropped for fenced tools:
    they still type the fenced field as a string and would misrepresent the
    reshaped MCP output (Response-Envelope Standard v1.1).
    """
    envelope_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "_meta": {"type": "object"},
        },
        "required": ["success", "_meta"],
        "additionalProperties": True,
    }

    if tool_name in UNTRUSTED_TEXT_FIELDS:
        text_field = UNTRUSTED_TEXT_FIELDS[tool_name][0]
        # `results` is optional so the shared outputSchema slot still accepts the
        # error frame (which has no `results`); its item shape pins the fenced
        # pointer to the typed object while staying permissive on sibling fields.
        envelope_schema["properties"]["results"] = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {text_field: {"$ref": "#/$defs/UntrustedText"}},
                "additionalProperties": True,
            },
        }
        envelope_schema["$defs"] = _untrusted_text_object_defs()
        return envelope_schema

    preserved_defs: dict[str, Any] = {}
    if schema:
        for key in ("$defs", "definitions"):
            value = schema.get(key)
            if isinstance(value, dict):
                preserved_defs[key] = value
    envelope_schema.update(preserved_defs)
    return envelope_schema
