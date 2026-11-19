"""Entry-point tools accept gene symbols directly (genefoundry-router#319).

Benchmark trace: "Is there an interaction between MAP3K1 and HRAS?" -- the model
first converted both symbols to UniProt accessions, then hit ``limit 1000 > 500``.
STRING resolves symbols natively, so one call must answer, echo ``resolved_from``
for each symbol STRING mapped, and an over-max ``limit`` must clamp, not error.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

_MAP3K1 = "9606.ENSP00000382423"
_HRAS = "9606.ENSP00000309845"


def _row(a: tuple[str, str], b: tuple[str, str]) -> dict[str, Any]:
    scores = dict.fromkeys(("nscore", "fscore", "pscore", "ascore", "escore", "dscore"), 0.0)
    return {
        "stringId_A": a[0],
        "preferredName_A": a[1],
        "stringId_B": b[0],
        "preferredName_B": b[1],
        "ncbiTaxonId": 9606,
        "score": 0.9,
        "tscore": 0.9,
        **scores,
    }


_PAIR = _row((_MAP3K1, "MAP3K1"), (_HRAS, "HRAS"))
_RESOLVED = [
    {"input": "MAP3K1", "form": "symbol", "resolved_to": _MAP3K1},
    {"input": "HRAS", "form": "symbol", "resolved_to": _HRAS},
]


@pytest.mark.asyncio
async def test_pair_query_accepts_symbols_and_echoes_resolved_from(facade: Any) -> None:
    upstream = AsyncMock(return_value=[{**_PAIR, "stringId_A": _MAP3K1}])
    with patch("stringdb_link.api.client.StringDBClient.get_network_interactions", upstream):
        async with Client(facade) as client:
            result = await client.call_tool(
                "search_protein_interactions",
                {"identifiers": ["MAP3K1", "HRAS"], "species": 9606, "required_score": 0.401},
            )
    body = result.structured_content
    assert body["success"] is True
    assert body["results"][0]["preferredName_B"] == "HRAS"
    assert body["resolved_from"] == _RESOLVED
    # Symbols are passed through to STRING unconverted (it resolves them natively).
    assert upstream.await_args.kwargs["identifiers"] == ["MAP3K1", "HRAS"]


@pytest.mark.asyncio
async def test_partners_over_max_limit_clamps_instead_of_erroring(facade: Any) -> None:
    upstream = AsyncMock(return_value=[_PAIR])
    with patch("stringdb_link.api.client.StringDBClient.get_interaction_partners", upstream):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_interaction_partners",
                {
                    "identifiers": ["MAP3K1"],
                    "species": 9606,
                    "limit": 1000,
                    "required_score": 0.402,
                },
            )
    body = result.structured_content
    assert result.is_error is False, body
    assert body["limit_clamped_to"] == 500
    assert body["resolved_from"] == _RESOLVED[:1]


@pytest.mark.asyncio
async def test_unconverted_inputs_omit_resolved_from(facade: Any) -> None:
    upstream = AsyncMock(return_value=[_PAIR])
    with patch("stringdb_link.api.client.StringDBClient.get_interaction_partners", upstream):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_interaction_partners",
                {"identifiers": [_MAP3K1], "species": 9606, "required_score": 0.403},
            )
    body = result.structured_content
    assert "resolved_from" not in body
    assert "limit_clamped_to" not in body


def test_ambiguous_symbol_is_not_guessed() -> None:
    from stringdb_link.models.resolution import resolve_symbols

    assert resolve_symbols(["HRAS"], [(_HRAS, "HRAS"), ("9606.ENSP0000099", "HRAS")]) is None
