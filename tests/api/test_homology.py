"""Tests for homology endpoints (success path).

The homology routes build ``HomologyScore`` objects from raw STRING JSON. STRING
returns camelCase keys (``ncbiTaxonId_A`` / ``stringId_A`` / ``ncbiTaxonId_B`` /
``stringId_B`` / ``bitscore``) while the model uses snake_case fields with no
aliases. These success-path tests guard the camelCase -> snake_case transform the
routes apply before constructing the model; without it, non-empty results raise a
validation error and the endpoint returns 500.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from stringdb_link.models.responses import HomologyScoreListResponse

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# Realistic STRING /api/json/homology response. Note bitscore arrives as a
# string from this endpoint; the model coerces it to float.
HOMOLOGY_SCORES_RESPONSE = [
    {
        "ncbiTaxonId_A": 9606,
        "stringId_A": "9606.ENSP00000269305",
        "ncbiTaxonId_B": 9606,
        "stringId_B": "9606.ENSP00000269305",
        "bitscore": "815.8",
    }
]

# Realistic STRING /api/json/homology_best response (cross-species best hit).
HOMOLOGY_BEST_RESPONSE = [
    {
        "ncbiTaxonId_A": 9606,
        "stringId_A": "9606.ENSP00000269305",
        "ncbiTaxonId_B": 10090,
        "stringId_B": "10090.ENSMUSP00000104298",
        "bitscore": 598.2,
    }
]


def test_get_homology_scores_success(test_client: TestClient):
    """Non-empty homology scores map camelCase STRING JSON onto the model."""
    request_data = {"identifiers": ["9606.ENSP00000269305"], "species": 9606}

    with patch(
        "stringdb_link.api.client.StringDBClient.get_homology_scores",
        new_callable=AsyncMock,
    ) as mock_homology:
        mock_homology.return_value = HOMOLOGY_SCORES_RESPONSE
        response = test_client.post("/api/homology/scores", json=request_data)

    assert response.status_code == 200
    data = response.json()

    model = HomologyScoreListResponse(**data)
    assert model.total_count == 1
    assert len(model.scores) == 1

    score = model.scores[0]
    assert score.ncbi_taxon_id_a == 9606
    assert score.string_id_a == "9606.ENSP00000269305"
    assert score.ncbi_taxon_id_b == 9606
    assert score.string_id_b == "9606.ENSP00000269305"
    assert score.bitscore == pytest.approx(815.8)


def test_get_homology_scores_empty(test_client: TestClient):
    """Empty results remain valid and return an empty score list."""
    request_data = {"identifiers": ["nonexistent"], "species": 9606}

    with patch(
        "stringdb_link.api.client.StringDBClient.get_homology_scores",
        new_callable=AsyncMock,
    ) as mock_homology:
        mock_homology.return_value = []
        response = test_client.post("/api/homology/scores", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    assert data["scores"] == []


def test_get_homology_best_hits_success(test_client: TestClient):
    """Best hits map cross-species camelCase STRING JSON onto the model."""
    request_data = {
        "identifiers": ["9606.ENSP00000269305"],
        "species": 9606,
        "species_b": [10090],
    }

    with patch(
        "stringdb_link.api.client.StringDBClient.get_homology_best_hits",
        new_callable=AsyncMock,
    ) as mock_best:
        mock_best.return_value = HOMOLOGY_BEST_RESPONSE
        response = test_client.post("/api/homology/best-hits", json=request_data)

    assert response.status_code == 200
    data = response.json()

    model = HomologyScoreListResponse(**data)
    assert model.total_count == 1

    score = model.scores[0]
    assert score.ncbi_taxon_id_a == 9606
    assert score.ncbi_taxon_id_b == 10090
    assert score.string_id_b == "10090.ENSMUSP00000104298"
    assert score.bitscore == pytest.approx(598.2)


@pytest.mark.slow
@pytest.mark.integration
def test_get_homology_scores_real_api(test_client: TestClient):
    """Opt-in integration test against the real STRING API (skip-on-unavailable).

    Mirrors ``tests/api/test_identifiers.py``: it never hard-fails on an
    unreachable/rate-limited API, only asserting the response envelope when the
    call succeeds.
    """
    request_data = {"identifiers": ["9606.ENSP00000269305"], "species": 9606}

    response = test_client.post("/api/homology/scores", json=request_data)

    if response.status_code == 200:
        data = response.json()
        assert "scores" in data
        assert data["total_count"] >= 0
        if data["scores"]:
            first = data["scores"][0]
            assert "string_id_a" in first
            assert "bitscore" in first
    else:
        # API may be down or rate limited; the route wraps failures as 5xx/429.
        assert response.status_code in (429, 500, 502, 503)
