"""Pytest configuration and fixtures for StringDB-Link tests."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest
import pytest_asyncio

from stringdb_link.api.client import StringDBClient
from stringdb_link.app import app
from stringdb_link.config import Settings, get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        host="127.0.0.1",
        port=8000,
        transport="http",
        debug=True,
        development_mode=True,
        cache_enabled=True,
        cache_default_ttl=60,  # Short TTL for tests
        stringdb_base_url="https://string-db.org/api",
        stringdb_rate_limit_delay=0.1,  # Fast for tests
        log_level="DEBUG",
    )


@pytest.fixture
def override_settings(test_settings: Settings) -> Generator[Settings, None, None]:
    """Override settings for tests."""
    original_settings = get_settings()

    # Mock the dependency
    app.dependency_overrides[get_settings] = lambda: test_settings

    yield test_settings

    # Restore original settings
    app.dependency_overrides[get_settings] = lambda: original_settings


@pytest.fixture
def test_client(override_settings: Settings) -> Generator[TestClient, None, None]:
    """Create test client."""
    client = TestClient(app)
    yield client
    client.close()


@pytest_asyncio.fixture
async def async_client(
    override_settings: Settings,
) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def stringdb_client() -> AsyncGenerator[StringDBClient, None]:
    """Create StringDB client for testing."""
    client = StringDBClient(
        base_url="https://string-db.org/api",
        rate_limit_delay=0.1,  # Fast for tests
    )
    yield client
    await client.close()


@pytest.fixture
def mock_stringdb_client() -> MagicMock:
    """Create mock StringDB client."""
    mock_client = MagicMock(spec=StringDBClient)

    # Mock common methods with realistic responses
    mock_client.get_string_ids.return_value = [
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

    mock_client.get_network_interactions.return_value = [
        {
            "stringId_A": "9606.ENSP00000269305",
            "stringId_B": "9606.ENSP00000344843",
            "preferredName_A": "TP53",
            "preferredName_B": "MDM2",
            "ncbiTaxonId": 9606,
            "score": 0.999,
            "nscore": 0.0,
            "fscore": 0.0,
            "pscore": 0.0,
            "ascore": 0.203,
            "escore": 0.938,
            "dscore": 0.999,
            "tscore": 0.995,
        }
    ]

    mock_client.get_functional_enrichment.return_value = [
        {
            "category": "Process",
            "term": "GO:0006915",
            "number_of_genes": 1,
            "number_of_genes_in_background": 1234,
            "ncbiTaxonId": 9606,
            "inputGenes": ["TP53"],
            "preferredNames": ["TP53"],
            "p_value": 0.001,
            "fdr": 0.01,
            "description": "apoptotic process",
        }
    ]

    return mock_client


@pytest.fixture
def sample_protein_identifiers() -> list[str]:
    """Sample protein identifiers for testing."""
    return ["p53", "BRCA1", "cdk2", "TP53", "MDM2"]


@pytest.fixture
def sample_string_ids() -> list[str]:
    """Sample STRING identifiers for testing."""
    return [
        "9606.ENSP00000269305",  # TP53
        "9606.ENSP00000350283",  # BRCA1
        "9606.ENSP00000266970",  # CDK2
        "9606.ENSP00000344843",  # MDM2
    ]


@pytest.fixture
def sample_enrichment_response() -> list[dict]:
    """Sample enrichment analysis response."""
    return [
        {
            "category": "Process",
            "term": "GO:0006915",
            "number_of_genes": 2,
            "number_of_genes_in_background": 1234,
            "ncbiTaxonId": 9606,
            "inputGenes": ["TP53", "MDM2"],
            "preferredNames": ["TP53", "MDM2"],
            "p_value": 0.001234,
            "fdr": 0.01234,
            "description": "apoptotic process",
        },
        {
            "category": "Function",
            "term": "GO:0003677",
            "number_of_genes": 1,
            "number_of_genes_in_background": 2345,
            "ncbiTaxonId": 9606,
            "inputGenes": ["TP53"],
            "preferredNames": ["TP53"],
            "p_value": 0.005678,
            "fdr": 0.05678,
            "description": "DNA binding",
        },
    ]


@pytest.fixture
def sample_network_response() -> list[dict]:
    """Sample network interaction response."""
    return [
        {
            "stringId_A": "9606.ENSP00000269305",
            "stringId_B": "9606.ENSP00000344843",
            "preferredName_A": "TP53",
            "preferredName_B": "MDM2",
            "ncbiTaxonId": 9606,
            "score": 0.999,
            "nscore": 0.0,
            "fscore": 0.0,
            "pscore": 0.0,
            "ascore": 0.203,
            "escore": 0.938,
            "dscore": 0.999,
            "tscore": 0.995,
        },
        {
            "stringId_A": "9606.ENSP00000269305",
            "stringId_B": "9606.ENSP00000371953",
            "preferredName_A": "TP53",
            "preferredName_B": "ATM",
            "ncbiTaxonId": 9606,
            "score": 0.900,
            "nscore": 0.0,
            "fscore": 0.0,
            "pscore": 0.0,
            "ascore": 0.150,
            "escore": 0.800,
            "dscore": 0.900,
            "tscore": 0.850,
        },
    ]
