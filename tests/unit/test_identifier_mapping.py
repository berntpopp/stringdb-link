"""Every tool taking ``identifiers`` says which inputs STRING mapped (genefoundry-router#343).

Audit trace: ``get_interaction_partners(["ENSG00000133703", "HGNC:6407", "3845"])``
returned one protein and no word on which inputs were used, while
``resolve_protein_identifiers`` showed only ``3845``. STRING returns one row per
PROTEIN, so the other two were not unmapped -- they were the same gene.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

pytestmark = pytest.mark.real_identifier_mapping

_KRAS = "9606.ENSP00000256078"
_TP53 = "9606.ENSP00000269305"
_KNOWN = {
    "ENSG00000133703": (_KRAS, "KRAS"),
    "HGNC:6407": (_KRAS, "KRAS"),
    "3845": (_KRAS, "KRAS"),
    "KRAS": (_KRAS, "KRAS"),
    "TP53": (_TP53, "TP53"),
}
_GET_IDS = "stringdb_link.api.client.StringDBClient.get_string_ids"
_PARTNERS = "stringdb_link.api.client.StringDBClient.get_interaction_partners"


def _string_mapper() -> AsyncMock:
    """STRING's get_string_ids: one row per PROTEIN, the last input naming it wins."""

    async def get_string_ids(
        identifiers: list[str], species: int | None = None, **_: Any
    ) -> list[dict[str, Any]]:
        rows: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(identifiers):
            if item in _KNOWN:
                string_id, name = _KNOWN[item]
                rows[string_id] = {
                    "queryItem": item,
                    "queryIndex": index,
                    "stringId": string_id,
                    "ncbiTaxonId": 9606,
                    "taxonName": "Homo sapiens",
                    "preferredName": name,
                    "annotation": "x",
                }
        return list(rows.values())

    return AsyncMock(side_effect=get_string_ids)


def _partner_row() -> dict[str, Any]:
    scores = dict.fromkeys(("nscore", "fscore", "pscore", "ascore", "escore", "dscore"), 0.0)
    return {
        "stringId_A": _KRAS,
        "preferredName_A": "KRAS",
        "stringId_B": _TP53,
        "preferredName_B": "TP53",
        "ncbiTaxonId": 9606,
        "score": 0.9,
        "tscore": 0.9,
        **scores,
    }


@pytest.mark.asyncio
async def test_partners_report_every_input_even_when_three_name_one_gene(facade: Any) -> None:
    ids = ["ENSG00000133703", "HGNC:6407", "3845", "NOPE123"]
    with (
        patch(_GET_IDS, _string_mapper()),
        patch(_PARTNERS, AsyncMock(return_value=[_partner_row()])),
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_interaction_partners",
                {"identifiers": ids, "species": 9606, "required_score": 0.411},
            )
    body = result.structured_content
    assert body["success"] is True
    assert {m["input"]: m["string_id"] for m in body["mapped"]} == dict.fromkeys(ids[:3], _KRAS)
    assert [u["input"] for u in body["unmapped"]] == ["NOPE123"]
    assert "no protein" in body["unmapped"][0]["reason"]
    assert list(body)[-1] == "_meta"


@pytest.mark.asyncio
async def test_resolve_tool_reports_the_same_mapping_as_the_network_tools(facade: Any) -> None:
    """The row list stays STRING's (one per protein); mapped/unmapped cover every input."""
    with patch(_GET_IDS, _string_mapper()):
        async with Client(facade) as client:
            result = await client.call_tool(
                "resolve_protein_identifiers",
                {"identifiers": ["ENSG00000133703", "HGNC:6407", "3845"], "species": 9606},
            )
    body = result.structured_content
    assert body["total_count"] == 1
    assert [m["input"] for m in body["mapped"]] == ["3845", "HGNC:6407", "ENSG00000133703"]
    assert body["unmapped"] == []


@pytest.mark.asyncio
async def test_symbol_keeps_its_answer_and_gains_the_mapping(facade: Any) -> None:
    with (
        patch(_GET_IDS, _string_mapper()),
        patch(_PARTNERS, AsyncMock(return_value=[_partner_row()])),
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_interaction_partners",
                {"identifiers": ["KRAS"], "species": 9606, "required_score": 0.412},
            )
    body = result.structured_content
    assert body["results"][0]["preferredName_B"] == "TP53"
    assert body["mapped"] == [{"input": "KRAS", "string_id": _KRAS, "preferred_name": "KRAS"}]
    assert body["unmapped"] == []


@pytest.mark.asyncio
async def test_no_input_mapped_is_not_found_naming_the_inputs(facade: Any) -> None:
    """STRING fails the whole call when it reads none of the inputs: not an `internal`."""
    with (
        patch(_GET_IDS, _string_mapper()),
        patch(_PARTNERS, AsyncMock(side_effect=RuntimeError("upstream said no"))),
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_interaction_partners",
                {"identifiers": ["NOPE123"], "species": 9606, "required_score": 0.413},
                raise_on_error=False,
            )
    body = result.structured_content
    assert result.is_error is True
    assert body["error_code"] == "not_found"
    assert body["field"] == "identifiers"
    assert [u["input"] for u in body["unmapped"]] == ["NOPE123"]
    assert "next_commands" not in body["_meta"]  # no converter can be guaranteed


@pytest.mark.asyncio
async def test_mapper_failure_never_fails_the_tool(facade: Any) -> None:
    with (
        patch(_GET_IDS, AsyncMock(side_effect=RuntimeError("down"))),
        patch(_PARTNERS, AsyncMock(return_value=[_partner_row()])),
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_interaction_partners",
                {"identifiers": ["KRAS"], "species": 9606, "required_score": 0.414},
            )
    body = result.structured_content
    assert body["success"] is True
    assert body["identifier_mapping"].startswith("unavailable")
    assert "mapped" not in body


@pytest.mark.asyncio
async def test_a_fifth_input_naming_one_protein_is_undetermined_not_unmapped() -> None:
    from types import SimpleNamespace

    from stringdb_link.mcp.identifier_mapping import map_identifiers

    async def resolve(request: Any) -> Any:  # every input names the same protein
        row = SimpleNamespace(
            query_index=len(request.identifiers) - 1, string_id=_KRAS, preferred_name="KRAS"
        )
        return SimpleNamespace(mappings=[row])

    service = SimpleNamespace(resolve_identifiers=resolve)
    out = await map_identifiers(service, ["a", "b", "c", "d", "e"], 9606)  # type: ignore[arg-type]
    assert len(out["mapped"]) == 4
    assert out["unmapped"][0]["reason"].startswith("not determined")


@pytest.mark.asyncio
async def test_partner_description_names_the_set_level_tools(facade: Any) -> None:
    async with Client(facade) as client:
        tools = {t.name: t.description for t in await client.list_tools()}
    _lead, _, rest = tools["get_interaction_partners"].partition(". ")
    assert rest.startswith("To test a gene list for enriched functions or interactions, call")
    assert "compute_functional_enrichment" in rest
    assert "compute_ppi_enrichment" in rest
