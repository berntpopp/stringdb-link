"""GeneFoundry Response-Envelope Standard v1 conformance tests for stringdb-link.

Pins the flat-banner frame at the MCP tool boundary (``structuredContent``):

- Success, collection tool: ``{"success": true, "results": [...], "_meta": {...}}``
  at the TOP LEVEL — no ``{"result": {"partners": [...]}}`` double-wrap. Domain
  siblings (e.g. ``total_count``) ride beside ``results``.
- Success, single-item tool: ``{"success": true, "result": {...}, "_meta": {...}}``.
- Failure: a flat, in-band error frame (``error_code`` / ``retryable`` /
  ``recovery_action``) returned as ``structuredContent`` (not an opaque text blob),
  so an LLM can branch on a structured failure.
- ``_meta.unsafe_for_clinical_use`` is ``True`` on EVERY response (success + error).

The REST/FastAPI surface is untouched — this is an MCP ``structuredContent``
contract only. See docs/RESPONSE-ENVELOPE-STANDARD-v1.md for the normative frame.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from stringdb_link.exceptions import StringDBServiceError
from stringdb_link.mcp.envelope import build_error_envelope, safe_error_message
from stringdb_link.models.responses import (
    InteractionPartner,
    InteractionPartnerListResponse,
    NetworkImage,
    NetworkImageResponse,
    PPIEnrichmentResult,
)

_PARTNER = InteractionPartner(
    stringId_A="9606.ENSP00000269305",
    stringId_B="9606.ENSP00000344843",
    preferredName_A="TP53",
    preferredName_B="MDM2",
    ncbiTaxonId=9606,
    score=0.999,
    nscore=0.005,
    fscore=0.005,
    pscore=0.005,
    ascore=0.999,
    escore=0.999,
    dscore=0.999,
    tscore=0.999,
)

_PPI = PPIEnrichmentResult(
    number_of_nodes=5,
    number_of_edges=5,
    average_node_degree=3.2,
    local_clustering_coefficient=0.75,
    expected_number_of_edges=2.1,
    p_value=0.001,
)


# --------------------------------------------------------------------------- #
# MCP-boundary behavioral tests (the contract the gateway relies on)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_collection_tool_promotes_results_to_top_level(facade: Any) -> None:
    """A collection tool returns top-level ``results`` (no ``result`` wrap)."""
    with patch(
        "stringdb_link.services.stringdb_service.StringDBService.get_interaction_partners",
        new_callable=AsyncMock,
        return_value=InteractionPartnerListResponse(partners=[_PARTNER], total_count=1),
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_interaction_partners",
                {"identifiers": ["TP53"], "species": 9606},
            )

    body = result.structured_content
    assert body is not None
    assert body["success"] is True
    assert "result" not in body, "collection tools must not double-wrap under 'result'"
    assert isinstance(body["results"], list)
    assert body["results"][0]["preferredName_B"] == "MDM2"
    # Domain sibling rides beside `results` (Response-Envelope Standard v1 Rule 1).
    assert body["total_count"] == 1

    meta = body["_meta"]
    assert meta["tool"] == "get_interaction_partners"
    assert meta["unsafe_for_clinical_use"] is True
    assert meta["source"] == "stringdb"
    assert "request_id" in meta


@pytest.mark.asyncio
async def test_single_tool_nests_payload_under_result(facade: Any) -> None:
    """A single-item tool nests its whole payload under ``result``."""
    with patch(
        "stringdb_link.services.stringdb_service.StringDBService.get_ppi_enrichment",
        new_callable=AsyncMock,
        return_value=_PPI,
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "compute_ppi_enrichment",
                {"identifiers": ["trpA", "trpB"], "species": 511145},
            )

    body = result.structured_content
    assert body is not None
    assert body["success"] is True
    assert "results" not in body, "single-item tool must not use 'results'"
    assert body["result"]["number_of_nodes"] == 5
    assert body["result"]["p_value"] == pytest.approx(0.001)
    assert body["_meta"]["tool"] == "compute_ppi_enrichment"
    assert body["_meta"]["unsafe_for_clinical_use"] is True


@pytest.mark.asyncio
async def test_upstream_failure_is_flat_retryable_error_envelope(facade: Any) -> None:
    """A 502 upstream failure surfaces as a flat, in-band, retryable envelope."""
    with patch(
        "stringdb_link.services.stringdb_service.StringDBService.get_interaction_partners",
        new_callable=AsyncMock,
        side_effect=StringDBServiceError("STRING API unreachable", status_code=502),
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_interaction_partners",
                {"identifiers": ["TP53"], "species": 9606},
                raise_on_error=False,
            )

    body = result.structured_content
    assert body is not None, "errors must carry structured_content, not only content[].text"
    # The wire-level MCP isError bit MUST be set so a client branching on isError
    # sees the failure (Response-Envelope Standard v1).
    assert result.is_error is True
    assert body["success"] is False
    assert body["error_code"] == "upstream_unavailable"
    assert body["retryable"] is True
    assert body["recovery_action"]
    # The message is a fixed, server-authored, status-keyed string — the upstream
    # error string is SEVERED, never echoed (a caller-influenced body could carry
    # injection prose that code-point sanitization alone would not remove).
    assert body["message"] == safe_error_message(502)
    assert "STRING API unreachable" not in body["message"]
    assert body["_meta"]["tool"] == "get_interaction_partners"
    assert body["_meta"]["unsafe_for_clinical_use"] is True


@pytest.mark.asyncio
async def test_internal_failure_is_non_retryable_internal_error(facade: Any) -> None:
    """A bare unexpected exception becomes a 500 -> non-retryable internal_error."""
    with patch(
        "stringdb_link.services.stringdb_service.StringDBService.get_interaction_partners",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_interaction_partners",
                {"identifiers": ["TP53"], "species": 9606},
                raise_on_error=False,
            )

    body = result.structured_content
    assert body is not None
    assert result.is_error is True
    assert body["success"] is False
    assert body["error_code"] == "internal"
    assert body["retryable"] is False
    assert body["recovery_action"]
    assert body["_meta"]["unsafe_for_clinical_use"] is True


@pytest.mark.asyncio
async def test_binary_image_tool_degrades_to_structured_internal_error(facade: Any) -> None:
    """The image tool's binary body defeats the JSON MCP provider (no HTTP
    response in the chain); the wrapper degrades it to a flat, non-retryable
    internal_error envelope with the disclaimer — never an opaque ToolError."""
    image = NetworkImageResponse(
        image=NetworkImage(
            image_data=b"\x89PNG\r\n\x1a\n",
            image_format="image",
            content_type="image/png",
        )
    )
    with patch(
        "stringdb_link.services.stringdb_service.StringDBService.get_network_image",
        new_callable=AsyncMock,
        return_value=image,
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_network_image",
                {"identifiers": ["nup100"], "species": 4932},
                raise_on_error=False,
            )

    body = result.structured_content
    assert body is not None
    assert body["success"] is False
    assert body["error_code"] == "internal"
    assert body["retryable"] is False
    assert body["_meta"]["tool"] == "get_network_image"
    assert body["_meta"]["unsafe_for_clinical_use"] is True


@pytest.mark.asyncio
async def test_every_tool_declares_read_only_open_world_annotations(facade: Any) -> None:
    """Every stringdb-link tool is a read-only STRING lookup (open world)."""
    tools = await facade.list_tools()
    assert tools
    for tool in tools:
        assert tool.annotations is not None, f"{tool.name} missing annotations"
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.openWorldHint is True


# --------------------------------------------------------------------------- #
# Unit-level classification tests (envelope module, no FastMCP wrapper)
# --------------------------------------------------------------------------- #
def test_build_error_envelope_400_is_invalid_input() -> None:
    env = build_error_envelope(
        "resolve_protein_identifiers",
        status_code=400,
        message="Validation error: bad input",
        request_id="r1",
        elapsed_ms=1.0,
    )
    assert env["success"] is False
    assert env["error_code"] == "invalid_input"
    assert env["retryable"] is False
    assert env["message"] == "Validation error: bad input"
    assert env["_meta"]["unsafe_for_clinical_use"] is True


def test_build_error_envelope_429_is_retryable_rate_limited() -> None:
    env = build_error_envelope(
        "get_interaction_partners",
        status_code=429,
        message="Too many requests",
        request_id="r2",
        elapsed_ms=1.0,
    )
    assert env["error_code"] == "rate_limited"
    assert env["retryable"] is True


def test_build_error_envelope_500_is_non_retryable_internal() -> None:
    env = build_error_envelope(
        "get_network_link",
        status_code=500,
        message="Internal server error",
        request_id="r3",
        elapsed_ms=1.0,
    )
    assert env["error_code"] == "internal"
    assert env["retryable"] is False


def test_build_error_envelope_502_is_retryable_upstream() -> None:
    env = build_error_envelope(
        "get_protein_homology_scores",
        status_code=502,
        message="Bad gateway",
        request_id="r4",
        elapsed_ms=1.0,
    )
    assert env["error_code"] == "upstream_unavailable"
    assert env["retryable"] is True
