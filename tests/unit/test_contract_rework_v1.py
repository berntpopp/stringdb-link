"""Regression tests for the Codex-reviewed contract-hardening rework.

Covers the six fixes from the PR #34 review:

1. get_interaction_partners paginates PER PROTEIN (no global head-slice) with a
   true, limit-invariant total.
2. A tool that RETURNS ``{"success": false}`` yields ``isError: true``.
3. get_network_link keeps the four real STRING formats and shapes tsv/xml into a
   structured result (never 422, never empty).
5. An empty upstream image body is an error, never ``success`` with 0 bytes.
6. ANY STRING in-band ``{"error": ...}`` becomes ``invalid_input`` naming a field.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from stringdb_link.exceptions import ValidationError
from stringdb_link.mcp.error_passthrough import finalize_tool_result
from stringdb_link.models.requests import InteractionPartnersRequest, LinkRequest
from stringdb_link.services.stringdb_service import StringDBService, _raise_if_string_error


def _raw_partner(query_string_id: str, partner_name: str) -> dict[str, Any]:
    """A raw STRING interaction-partner row keyed by aliased field names."""
    return {
        "stringId_A": query_string_id,
        "stringId_B": f"9606.{partner_name}",
        "preferredName_A": query_string_id.split(".")[-1],
        "preferredName_B": partner_name,
        "ncbiTaxonId": 9606,
        "score": 0.9,
        "nscore": 0.0,
        "fscore": 0.0,
        "pscore": 0.0,
        "ascore": 0.9,
        "escore": 0.9,
        "dscore": 0.9,
        "tscore": 0.9,
    }


def _service_with_client(**client_methods: Any) -> tuple[StringDBService, MagicMock]:
    client = MagicMock()
    for name, value in client_methods.items():
        setattr(client, name, value)
    return StringDBService(client=client, logger=MagicMock()), client


# --- Issue 2: returned {"success": false} -> isError: true --------------------
def test_returned_error_dict_sets_is_error() -> None:
    result = finalize_tool_result(
        "resolve_protein_identifiers",
        {"success": False, "error_code": "invalid_input", "message": "bad", "field": "species"},
        request_id="r1",
        elapsed_ms=1.0,
    )
    assert result.is_error is True
    body = result.structured_content
    assert body is not None
    assert body["success"] is False
    assert body["error_code"] == "invalid_input"
    assert body["field"] == "species"


def test_returned_error_dict_off_enum_code_collapses_to_internal() -> None:
    result = finalize_tool_result(
        "resolve_protein_identifiers",
        {"success": False, "error_code": "validation_failed"},
        request_id="r1",
        elapsed_ms=1.0,
    )
    assert result.is_error is True
    assert result.structured_content["error_code"] == "internal"


def test_returned_success_dict_is_not_error() -> None:
    result = finalize_tool_result(
        "get_interaction_partners",
        {"partners": [], "total_count": 0},
        request_id="r1",
        elapsed_ms=1.0,
    )
    assert result.is_error is False
    assert result.structured_content["success"] is True


# --- Issue 6: ANY in-band {"error": ...} -> invalid_input naming a field ------
def test_background_error_names_background_field() -> None:
    with pytest.raises(ValidationError) as exc:
        _raise_if_string_error([{"error": "background_error", "message": "x"}])
    assert exc.value.field == "background_string_identifiers"


def test_unknown_in_band_error_still_names_a_field() -> None:
    with pytest.raises(ValidationError) as exc:
        _raise_if_string_error([{"error": "some_new_string_error_type", "message": "x"}])
    # The GENERAL class is handled: a field is always named (never field-less).
    assert exc.value.field == "identifiers"


def test_non_error_payload_does_not_raise() -> None:
    _raise_if_string_error([{"term": "GO:0001", "description": "ok"}])


# --- Issue 1: per-protein pagination + limit-invariant total ------------------
@pytest.mark.asyncio
async def test_interaction_partners_paginate_per_protein() -> None:
    # TP53 has 3 partners, MDM2 has 2 — a global [:limit=2] would drop MDM2 entirely.
    raw = [
        _raw_partner("9606.TP53", "A"),
        _raw_partner("9606.TP53", "B"),
        _raw_partner("9606.TP53", "C"),
        _raw_partner("9606.MDM2", "D"),
        _raw_partner("9606.MDM2", "E"),
    ]
    svc, client = _service_with_client(
        get_interaction_partners=AsyncMock(return_value=raw),
    )
    request = InteractionPartnersRequest(identifiers=["TP53", "MDM2"], species=9606, limit=2)
    resp = await svc.get_interaction_partners(request)

    # The full set was fetched (limit omitted upstream), not a hardcoded page.
    assert client.get_interaction_partners.await_args.kwargs["limit"] is None
    # True, limit-invariant total.
    assert resp.total_count == 5
    assert resp.truncated is True
    # BOTH query proteins are represented (2 each), MDM2 not omitted.
    queries = {p.string_id_a for p in resp.partners}
    assert queries == {"9606.TP53", "9606.MDM2"}
    assert len(resp.partners) == 4


# --- Issue 3: get_network_link keeps tsv/xml, shapes them structurally --------
@pytest.mark.asyncio
async def test_network_link_tsv_returns_structured_url() -> None:
    tsv = "url\nhttps://version-12-0.string-db.org/cgi/link?to=DEADBEEF\n"
    svc, _ = _service_with_client(get_link=AsyncMock(return_value=tsv))
    request = LinkRequest(identifiers=["TP53", "MDM2"], species=9606)
    info = await svc.get_network_link(request, output_format="tsv")

    assert info.output_format == "tsv"
    assert info.url == "https://version-12-0.string-db.org/cgi/link?to=DEADBEEF"
    assert info.formatted == tsv  # the raw STRING serialization is preserved, not dropped


@pytest.mark.asyncio
async def test_network_link_xml_extracts_clean_url() -> None:
    xml = (
        '<?xml version="1.0"?>\n<get_linkResult>\n<record>\n'
        "<url>https://version-12-0.string-db.org/cgi/link?to=CAFE</url>\n"
        "</record>\n</get_linkResult>\n"
    )
    svc, _ = _service_with_client(get_link=AsyncMock(return_value=xml))
    info = await svc.get_network_link(LinkRequest(identifiers=["TP53"], species=9606), "xml")
    # The trailing </url> markup must NOT be swallowed into the URL.
    assert info.url == "https://version-12-0.string-db.org/cgi/link?to=CAFE"
    assert info.formatted == xml


@pytest.mark.asyncio
async def test_network_link_json_has_no_formatted() -> None:
    svc, _ = _service_with_client(
        get_link=AsyncMock(return_value="https://version-12-0.string-db.org/cgi/link?to=AA")
    )
    request = LinkRequest(identifiers=["TP53"], species=9606)
    info = await svc.get_network_link(request, output_format="json")
    assert info.output_format == "json"
    assert info.url.endswith("to=AA")
    assert info.formatted is None
