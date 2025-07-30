"""Tests for identifier resolution endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest

from stringdb_link.models.responses import StringIdMappingListResponse


def test_resolve_identifiers_success(test_client: TestClient, sample_protein_identifiers):
    """Test successful identifier resolution."""
    request_data = {
        "identifiers": sample_protein_identifiers[:2],  # p53, BRCA1
        "species": 9606,
        "echo_query": True,
    }

    # Mock the StringDB client response
    mock_response = [
        {
            "queryItem": "p53",
            "queryIndex": 0,
            "stringId": "9606.ENSP00000269305",
            "ncbiTaxonId": 9606,
            "taxonName": "Homo sapiens",
            "preferredName": "TP53",
            "annotation": "cellular tumor antigen p53",
        },
        {
            "queryItem": "BRCA1",
            "queryIndex": 1,
            "stringId": "9606.ENSP00000350283",
            "ncbiTaxonId": 9606,
            "taxonName": "Homo sapiens",
            "preferredName": "BRCA1",
            "annotation": "BRCA1 DNA repair associated",
        },
    ]

    with patch(
        "stringdb_link.api.client.StringDBClient.get_string_ids", new_callable=AsyncMock
    ) as mock_get_ids:
        mock_get_ids.return_value = mock_response

        response = test_client.post("/api/identifiers/resolve", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    response_model = StringIdMappingListResponse(**data)
    assert response_model.total_count == 2
    assert len(response_model.mappings) == 2

    # Validate first mapping
    first_mapping = response_model.mappings[0]
    assert first_mapping.query_item == "p53"
    assert first_mapping.string_id == "9606.ENSP00000269305"
    assert first_mapping.preferred_name == "TP53"


def test_resolve_identifiers_validation_error(test_client: TestClient):
    """Test identifier resolution with validation errors."""
    # Empty identifiers
    request_data = {
        "identifiers": [],
        "species": 9606,
    }

    response = test_client.post("/api/identifiers/resolve", json=request_data)
    assert response.status_code == 422  # Validation error

    # Invalid species
    request_data = {
        "identifiers": ["p53"],
        "species": -1,
    }

    response = test_client.post("/api/identifiers/resolve", json=request_data)
    assert response.status_code == 422  # Validation error


def test_resolve_single_identifier_success(test_client: TestClient):
    """Test single identifier resolution endpoint."""
    mock_response = [
        {
            "queryItem": "p53",
            "queryIndex": 0,
            "stringId": "9606.ENSP00000269305",
            "ncbiTaxonId": 9606,
            "taxonName": "Homo sapiens",
            "preferredName": "TP53",
            "annotation": "cellular tumor antigen p53",
        }
    ]

    with patch(
        "stringdb_link.api.client.StringDBClient.get_string_ids", new_callable=AsyncMock
    ) as mock_get_ids:
        mock_get_ids.return_value = mock_response

        response = test_client.get("/api/identifiers/resolve/p53?species=9606&echo_query=true")

    assert response.status_code == 200
    data = response.json()

    # The response uses the original API format (camelCase) due to Pydantic aliases
    assert data["queryItem"] == "p53"
    assert data["stringId"] == "9606.ENSP00000269305"
    assert data["preferredName"] == "TP53"


def test_resolve_single_identifier_not_found(test_client: TestClient):
    """Test single identifier resolution when identifier not found."""
    with patch(
        "stringdb_link.api.client.StringDBClient.get_string_ids", new_callable=AsyncMock
    ) as mock_get_ids:
        mock_get_ids.return_value = []  # No results

        response = test_client.get("/api/identifiers/resolve/nonexistent")

    assert response.status_code == 404
    data = response.json()
    assert "could not be resolved" in data["detail"]


@pytest.mark.slow
@pytest.mark.integration
def test_resolve_identifiers_real_api(test_client: TestClient):
    """Integration test with real StringDB API (marked as slow)."""
    request_data = {
        "identifiers": ["p53"],
        "species": 9606,
        "echo_query": True,
    }

    response = test_client.post("/api/identifiers/resolve", json=request_data)

    # This might fail if StringDB is down, but that's expected for integration tests
    if response.status_code == 200:
        data = response.json()
        assert "mappings" in data
        assert data["total_count"] >= 0
    else:
        # API might be down or rate limited
        assert response.status_code in [502, 503, 429]
