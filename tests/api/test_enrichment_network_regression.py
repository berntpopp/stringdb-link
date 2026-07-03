"""Route-level regression for stringdb-link #5 (enrichment/network HTTP 500)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from stringdb_link.models.responses import (
    EnrichmentTermListResponse,
    NetworkInteractionListResponse,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clear_string_caches():
    """Network/enrichment service methods are cached on a process-global manager;
    clear it so cache keys from other tests cannot mask the route behavior."""
    import asyncio

    from stringdb_link.utils.caching import cache_manager

    asyncio.run(cache_manager.clear_all_caches())
    yield


# STRING comma-separated variant (the production form that triggered the 500).
ENRICHMENT_RESPONSE = [
    {
        "category": "Process",
        "term": "GO:0000162",
        "number_of_genes": 5,
        "number_of_genes_in_background": 9,
        "ncbiTaxonId": 511145,
        "inputGenes": "trpA,trpB,trpC,trpGD,trpE",
        "preferredNames": "trpA,trpB,trpC,trpD,trpE",
        "p_value": 1.97e-13,
        "fdr": 6.18e-10,
        "description": "Tryptophan biosynthetic process",
    }
]

# Network record with ncbiTaxonId as a string and a score marginally above 1.0.
NETWORK_RESPONSE = [
    {
        "stringId_A": "9606.ENSP00000269305",
        "stringId_B": "9606.ENSP00000275493",
        "preferredName_A": "TP53",
        "preferredName_B": "EGFR",
        "ncbiTaxonId": "9606",
        "score": 1.02,
        "nscore": 0.0,
        "fscore": 0.0,
        "pscore": 0.0,
        "ascore": 0.0,
        "escore": 0.329,
        "dscore": 0.0,
        "tscore": 0.919,
    }
]


def test_functional_enrichment_returns_200_on_schema_example(test_client: TestClient):
    request_data = {"identifiers": ["trpA", "trpB", "trpC", "trpE", "trpGD"], "species": 511145}
    with patch(
        "stringdb_link.api.client.StringDBClient.get_functional_enrichment",
        new_callable=AsyncMock,
    ) as mock_enrichment:
        mock_enrichment.return_value = ENRICHMENT_RESPONSE
        response = test_client.post("/api/enrichment/functional", json=request_data)

    assert response.status_code == 200
    model = EnrichmentTermListResponse(**response.json())
    assert model.total_count == 1
    assert model.terms[0].input_genes == ["trpA", "trpB", "trpC", "trpGD", "trpE"]


def test_search_protein_interactions_returns_200_on_schema_example(test_client: TestClient):
    request_data = {"identifiers": ["TP53", "EGFR", "CDK2"], "species": 9606}
    with patch(
        "stringdb_link.api.client.StringDBClient.get_network_interactions",
        new_callable=AsyncMock,
    ) as mock_network:
        mock_network.return_value = NETWORK_RESPONSE
        response = test_client.post("/api/networks/interactions", json=request_data)

    assert response.status_code == 200
    model = NetworkInteractionListResponse(**response.json())
    assert model.total_count == 1
    assert model.interactions[0].score == pytest.approx(1.02)


def test_malformed_enrichment_record_returns_502_not_500(test_client: TestClient):
    bad = [dict(ENRICHMENT_RESPONSE[0])]
    del bad[0]["description"]  # required field missing -> upstream parse failure
    request_data = {"identifiers": ["trpA", "trpB"], "species": 511145}
    with patch(
        "stringdb_link.api.client.StringDBClient.get_functional_enrichment",
        new_callable=AsyncMock,
    ) as mock_enrichment:
        mock_enrichment.return_value = bad
        response = test_client.post("/api/enrichment/functional", json=request_data)

    assert response.status_code == 502
