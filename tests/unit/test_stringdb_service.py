"""Comprehensive tests for StringDBService."""

# Private member access is needed for testing internal methods

from unittest.mock import AsyncMock, MagicMock

import pytest

from stringdb_link.exceptions import StringDBServiceError
from stringdb_link.models.requests import (
    AnnotationRequest,
    EnrichmentRequest,
    IdentifierRequest,
    ImageRequest,
    InteractionPartnersRequest,
    LinkRequest,
    NetworkRequest,
    PPIEnrichmentRequest,
)
from stringdb_link.models.responses import (
    EnrichmentTermListResponse,
    FunctionalAnnotationListResponse,
    InteractionPartnerListResponse,
    LinkInfo,
    NetworkImageResponse,
    NetworkInteractionListResponse,
    PPIEnrichmentResult,
    StringIdMappingListResponse,
)
from stringdb_link.models.stringdb import ImageFormat, NetworkFlavor, NetworkType, OutputFormat
from stringdb_link.services.stringdb_service import StringDBService


@pytest.fixture
def mock_client():
    """Create a mock StringDBClient."""
    client = AsyncMock()
    client.get_string_ids = AsyncMock()
    client.get_network_interactions = AsyncMock()
    client.get_interaction_partners = AsyncMock()
    client.get_functional_enrichment = AsyncMock()
    client.get_functional_annotation = AsyncMock()
    client.get_network_image = AsyncMock()
    client.get_homology_scores = AsyncMock()
    client.get_homology_best_hits = AsyncMock()
    client.get_ppi_enrichment = AsyncMock()
    client.get_link = AsyncMock()
    return client


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def service(mock_client, mock_logger):
    """Create a StringDBService instance with mocked dependencies."""
    return StringDBService(client=mock_client, logger=mock_logger)


class TestStringDBService:
    """Test StringDBService class."""

    async def test_resolve_identifiers_success(self, service, mock_client):
        """Test successful identifier resolution."""
        # Arrange
        request = IdentifierRequest(identifiers=["p53", "BRCA1"], species=9606)
        mock_mappings = [
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
                "annotation": "breast cancer 1",
            },
        ]
        mock_client.get_string_ids.return_value = mock_mappings

        # Act
        result = await service.resolve_identifiers(request)

        # Assert
        assert isinstance(result, StringIdMappingListResponse)
        assert result.total_count == 2
        assert len(result.mappings) == 2
        mock_client.get_string_ids.assert_called_once_with(
            identifiers=["p53", "BRCA1"], species=9606, echo_query=False
        )

    async def test_resolve_identifiers_error(self, service, mock_client):
        """Test identifier resolution with client error."""
        # Arrange
        request = IdentifierRequest(identifiers=["invalid"])
        mock_client.get_string_ids.side_effect = Exception("API error")

        # Act & Assert
        with pytest.raises(StringDBServiceError, match="Failed to resolve identifiers"):
            await service.resolve_identifiers(request)

    async def test_get_network_interactions_success(self, service, mock_client):
        """Test successful network interactions retrieval."""
        # Arrange
        request = NetworkRequest(
            identifiers=["9606.ENSP00000269305"],
            species=9606,
            required_score=0.4,
            network_type=NetworkType.FUNCTIONAL,
        )
        mock_interactions = [
            {
                "stringId_A": "9606.ENSP00000269305",
                "stringId_B": "9606.ENSP00000348554",
                "preferredName_A": "TP53",
                "preferredName_B": "MDM2",
                "ncbiTaxonId": 9606,
                "score": 0.900,
                "nscore": 0.0,
                "fscore": 0.0,
                "pscore": 0.0,
                "ascore": 0.203,
                "escore": 0.938,
                "dscore": 0.999,
                "tscore": 0.995,
            }
        ]
        mock_client.get_network_interactions.return_value = mock_interactions

        # Act
        result = await service.get_network_interactions(request)

        # Assert
        assert isinstance(result, NetworkInteractionListResponse)
        assert result.total_count == 1
        assert len(result.interactions) == 1
        mock_client.get_network_interactions.assert_called_once()

    async def test_get_interaction_partners_success(self, service, mock_client):
        """Test successful interaction partners retrieval."""
        # Arrange
        request = InteractionPartnersRequest(
            identifiers=["9606.ENSP00000269305"], species=9606, limit=10
        )
        mock_partners = [
            {
                "stringId_A": "9606.ENSP00000269305",
                "stringId_B": "9606.ENSP00000348554",
                "preferredName_A": "TP53",
                "preferredName_B": "MDM2",
                "ncbiTaxonId": 9606,
                "score": 0.800,
                "nscore": 0.005,
                "fscore": 0.005,
                "pscore": 0.005,
                "ascore": 0.999,
                "escore": 0.999,
                "dscore": 0.999,
                "tscore": 0.999,
            }
        ]
        mock_client.get_interaction_partners.return_value = mock_partners

        # Act
        result = await service.get_interaction_partners(request)

        # Assert
        assert isinstance(result, InteractionPartnerListResponse)
        assert result.total_count == 1
        assert len(result.partners) == 1

    async def test_get_functional_enrichment_success(self, service, mock_client):
        """Test successful functional enrichment retrieval."""
        # Arrange
        request = EnrichmentRequest(identifiers=["9606.ENSP00000269305"], species=9606)
        mock_terms = [
            {
                "category": "Process",
                "term": "GO:0006915",
                "number_of_genes": 1,
                "number_of_genes_in_background": 100,
                "ncbi_taxon_id": 9606,
                "input_genes": ["TP53"],
                "preferred_names": ["TP53"],
                "p_value": 0.001,
                "fdr": 0.01,
                "description": "apoptotic process",
            }
        ]
        mock_client.get_functional_enrichment.return_value = mock_terms

        # Act
        result = await service.get_functional_enrichment(request)

        # Assert
        assert isinstance(result, EnrichmentTermListResponse)
        assert result.total_count == 1
        assert len(result.terms) == 1

    async def test_get_functional_annotation_success(self, service, mock_client):
        """Test successful functional annotation retrieval."""
        # Arrange
        request = AnnotationRequest(identifiers=["9606.ENSP00000269305"], species=9606)
        mock_annotations = [
            {
                "category": "Process",
                "term": "GO:0006915",
                "number_of_genes": 1,
                "ratio_in_set": 0.5,
                "ncbi_taxon_id": 9606,
                "input_genes": ["TP53"],
                "preferred_names": ["TP53"],
                "description": "apoptotic process",
            }
        ]
        mock_client.get_functional_annotation.return_value = mock_annotations

        # Act
        result = await service.get_functional_annotation(request)

        # Assert
        assert isinstance(result, FunctionalAnnotationListResponse)
        assert result.total_count == 1
        assert len(result.annotations) == 1

    async def test_get_network_image_success(self, service, mock_client):
        """Test successful network image generation."""
        # Arrange
        request = ImageRequest(
            identifiers=["9606.ENSP00000269305"],
            species=9606,
            image_format=ImageFormat.PNG,
            network_flavor=NetworkFlavor.EVIDENCE,
        )
        mock_image_data = b"fake_png_data"
        mock_client.get_network_image.return_value = mock_image_data

        # Act
        result = await service.get_network_image(request)

        # Assert
        assert isinstance(result, NetworkImageResponse)
        assert result.image.image_data == mock_image_data
        assert result.image.image_format == "image"
        assert result.image.content_type == "image/png"

    async def test_get_homology_scores_success(self, service, mock_client):
        """Test successful homology scores retrieval."""
        # Arrange
        identifiers = ["9606.ENSP00000269305"]
        species = 9606
        mock_scores = [
            {
                "stringId_A": "9606.ENSP00000269305",
                "stringId_B": "10090.ENSMUSP00000001",
                "bitscore": 85.0,
                "evalue": 0.0,
            }
        ]
        mock_client.get_homology_scores.return_value = mock_scores

        # Act
        result = await service.get_homology_scores(identifiers, species)

        # Assert
        assert result == mock_scores
        mock_client.get_homology_scores.assert_called_once_with(
            identifiers=identifiers, species=species, output_format=OutputFormat.JSON
        )

    async def test_get_homology_best_hits_success(self, service, mock_client):
        """Test successful homology best hits retrieval."""
        # Arrange
        identifiers = ["9606.ENSP00000269305"]
        species = 9606
        species_b = [10090]
        mock_hits = [
            {
                "stringId_A": "9606.ENSP00000269305",
                "stringId_B": "10090.ENSMUSP00000001",
                "bitscore": 85.0,
            }
        ]
        mock_client.get_homology_best_hits.return_value = mock_hits

        # Act
        result = await service.get_homology_best_hits(identifiers, species, species_b)

        # Assert
        assert result == mock_hits
        mock_client.get_homology_best_hits.assert_called_once_with(
            identifiers=identifiers,
            species=species,
            species_b=species_b,
            output_format=OutputFormat.JSON,
        )

    async def test_get_ppi_enrichment_success(self, service, mock_client):
        """Test successful PPI enrichment retrieval."""
        # Arrange
        request = PPIEnrichmentRequest(
            identifiers=["9606.ENSP00000269305", "9606.ENSP00000348554"], species=9606
        )
        mock_result = {
            "number_of_nodes": 5,
            "number_of_edges": 5,
            "average_node_degree": 3.2,
            "local_clustering_coefficient": 0.75,
            "expected_number_of_edges": 2.1,
            "p_value": 0.001,
        }
        mock_client.get_ppi_enrichment.return_value = mock_result

        # Act
        result = await service.get_ppi_enrichment(request)

        # Assert
        assert isinstance(result, PPIEnrichmentResult)
        assert result.p_value == 0.001

    async def test_get_network_link_success(self, service, mock_client):
        """Test successful network link generation."""
        # Arrange
        request = LinkRequest(
            identifiers=["9606.ENSP00000269305"],
            species=9606,
            network_type=NetworkType.FUNCTIONAL,
        )
        mock_result = {"url": "https://string-db.org/network/9606.ENSP00000269305"}
        mock_client.get_link.return_value = mock_result

        # Act
        result = await service.get_network_link(request)

        # Assert
        assert isinstance(result, LinkInfo)
        assert result.url == "https://string-db.org/network/9606.ENSP00000269305"

    async def test_get_cache_stats(self, service):
        """Test cache statistics retrieval."""
        # This test assumes cache_manager is available and functional
        # Since cache_manager.get_stats() returns a dict, we can test the interface
        result = await service.get_cache_stats()
        assert isinstance(result, dict)

    async def test_clear_cache(self, service):
        """Test cache clearing."""
        # Test that clear_cache completes without error
        await service.clear_cache()
        # Since it's a void method, we just verify it doesn't raise

    async def test_service_error_handling(self, service, mock_client):
        """Test service error handling for various operations."""
        # Test different error scenarios
        mock_client.get_string_ids.side_effect = Exception("Network error")
        request = IdentifierRequest(identifiers=["test"])

        with pytest.raises(StringDBServiceError):
            await service.resolve_identifiers(request)

    async def test_image_content_type_mapping(self, service):
        """Test image content type mapping."""
        # Test private method for content type mapping
        assert service._get_image_content_type("image") == "image/png"
        assert service._get_image_content_type("highres_image") == "image/png"
        assert service._get_image_content_type("svg") == "image/svg+xml"
        assert service._get_image_content_type("unknown") == "image/png"  # default


class TestStringDBServiceIntegration:
    """Integration tests for StringDBService."""

    async def test_resolve_identifiers_caching(self, service, mock_client):
        """Test that identifier resolution uses caching."""
        # Arrange
        request = IdentifierRequest(identifiers=["p53"], species=9606)
        mock_mappings = [
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
        mock_client.get_string_ids.return_value = mock_mappings

        # Act - call twice
        result1 = await service.resolve_identifiers(request)
        result2 = await service.resolve_identifiers(request)

        # Assert - both should succeed
        assert isinstance(result1, StringIdMappingListResponse)
        assert isinstance(result2, StringIdMappingListResponse)
        assert result1.total_count == result2.total_count

    async def test_service_logging(self, service, mock_client, mock_logger):
        """Test that service operations are properly logged."""
        # Arrange
        request = IdentifierRequest(identifiers=["p53"], species=9606)
        mock_mappings = [
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
        mock_client.get_string_ids.return_value = mock_mappings

        # Act
        await service.resolve_identifiers(request)

        # Assert - verify logging calls
        mock_logger.info.assert_called()
        # Check that the log contains expected information
        log_calls = mock_logger.info.call_args_list
        assert any("Resolving protein identifiers" in str(call) for call in log_calls)
        assert any("Successfully resolved identifiers" in str(call) for call in log_calls)


class TestStringDBServiceErrorHandling:
    """Test error handling in StringDBService."""

    async def test_resolve_identifiers_with_client_timeout(self, service, mock_client, mock_logger):
        """Test identifier resolution with client timeout."""
        # Arrange
        request = IdentifierRequest(identifiers=["p53"])
        mock_client.get_string_ids.side_effect = TimeoutError("Request timeout")

        # Act & Assert
        with pytest.raises(StringDBServiceError, match="Failed to resolve identifiers"):
            await service.resolve_identifiers(request)

        # Verify error was logged
        mock_logger.exception.assert_called()

    async def test_network_interactions_with_validation_error(self, service, mock_client):
        """Test network interactions with validation error."""
        # Arrange
        request = NetworkRequest(
            identifiers=["9606.ENSP00000269305"], species=9606, required_score=0.4
        )
        mock_client.get_network_interactions.side_effect = ValueError("Validation failed")

        # Act & Assert - Should raise StringDBServiceError
        with pytest.raises(StringDBServiceError, match="Failed to get network interactions"):
            await service.get_network_interactions(request)

    async def test_enrichment_with_empty_results(self, service, mock_client):
        """Test functional enrichment with empty results."""
        # Arrange
        request = EnrichmentRequest(identifiers=["9606.ENSP00000269305"], species=9606)
        mock_client.get_functional_enrichment.return_value = []

        # Act
        result = await service.get_functional_enrichment(request)

        # Assert
        assert isinstance(result, EnrichmentTermListResponse)
        assert result.total_count == 0
        assert len(result.terms) == 0


class TestStringDBServiceEdgeCases:
    """Test edge cases in StringDBService."""

    async def test_large_identifier_list(self, service, mock_client):
        """Test handling of large identifier lists."""
        # Arrange - create a large list of identifiers
        large_identifiers = [f"protein_{i}" for i in range(50)]
        request = IdentifierRequest(identifiers=large_identifiers)
        mock_mappings = [
            {
                "queryItem": f"protein_{i}",
                "queryIndex": i,
                "stringId": f"9606.PROTEIN{i:06d}",
                "ncbiTaxonId": 9606,
                "taxonName": "Homo sapiens",
                "preferredName": f"PROTEIN{i}",
                "annotation": f"protein {i} description",
            }
            for i in range(50)
        ]
        mock_client.get_string_ids.return_value = mock_mappings

        # Act
        result = await service.resolve_identifiers(request)

        # Assert
        assert isinstance(result, StringIdMappingListResponse)
        assert result.total_count == 50

    async def test_special_characters_in_identifiers(self, service, mock_client):
        """Test handling of special characters in identifiers."""
        # Arrange
        special_identifiers = ["protein-1", "protein_2", "protein.3", "protein@4"]
        request = IdentifierRequest(identifiers=special_identifiers)
        mock_mappings = [
            {
                "queryItem": ident,
                "queryIndex": i,
                "stringId": f"9606.{ident.upper()}",
                "ncbiTaxonId": 9606,
                "taxonName": "Homo sapiens",
                "preferredName": ident.upper(),
                "annotation": f"{ident} protein description",
            }
            for i, ident in enumerate(special_identifiers)
        ]
        mock_client.get_string_ids.return_value = mock_mappings

        # Act
        result = await service.resolve_identifiers(request)

        # Assert
        assert isinstance(result, StringIdMappingListResponse)
        assert result.total_count == 4

    async def test_network_image_different_formats(self, service, mock_client):
        """Test network image generation with different formats."""
        formats_to_test = [ImageFormat.PNG, ImageFormat.SVG]

        for img_format in formats_to_test:
            # Arrange
            request = ImageRequest(
                identifiers=["9606.ENSP00000269305"],
                image_format=img_format,
            )
            mock_image_data = b"fake_image_data"
            mock_client.get_network_image.return_value = mock_image_data

            # Act
            result = await service.get_network_image(request)

            # Assert
            assert isinstance(result, NetworkImageResponse)
            assert result.image.image_data == mock_image_data

            # Verify content type mapping
            if img_format == ImageFormat.SVG:
                assert result.image.content_type == "image/svg+xml"
            else:
                assert result.image.content_type == "image/png"


class TestUpstreamParseFailures:
    """Upstream STRING payloads that violate the schema must surface as 502."""

    async def test_network_parse_failure_maps_to_502(self, service, mock_client):
        # Missing the required preferredName_B -> NetworkInteraction ValidationError.
        mock_client.get_network_interactions.return_value = [
            {
                "stringId_A": "9606.ENSP00000269305",
                "stringId_B": "9606.ENSP00000344843",
                "preferredName_A": "TP53",
                "ncbiTaxonId": 9606,
                "score": 0.9,
                "nscore": 0.0,
                "fscore": 0.0,
                "pscore": 0.0,
                "ascore": 0.2,
                "escore": 0.9,
                "dscore": 0.9,
                "tscore": 0.9,
            }
        ]
        request = NetworkRequest(identifiers=["TP53", "EGFR", "CDK2"], species=9606)
        with pytest.raises(StringDBServiceError) as exc_info:
            await service.get_network_interactions(request)
        assert exc_info.value.status_code == 502
        assert exc_info.value.original_error is not None

    async def test_enrichment_parse_failure_maps_to_502(self, service, mock_client):
        # p_value out of [0, 1] -> EnrichmentTerm ValidationError.
        mock_client.get_functional_enrichment.return_value = [
            {
                "category": "Process",
                "term": "GO:0000162",
                "number_of_genes": 5,
                "number_of_genes_in_background": 9,
                "ncbiTaxonId": 511145,
                "inputGenes": ["trpA"],
                "preferredNames": ["trpA"],
                "p_value": 7.5,
                "fdr": 0.01,
                "description": "bad p-value",
            }
        ]
        request = EnrichmentRequest(identifiers=["trpA", "trpB"], species=511145)
        with pytest.raises(StringDBServiceError) as exc_info:
            await service.get_functional_enrichment(request)
        assert exc_info.value.status_code == 502

    async def test_non_parse_error_stays_500(self, service, mock_client):
        mock_client.get_network_interactions.side_effect = RuntimeError("boom")
        request = NetworkRequest(identifiers=["TP53", "EGFR"], species=9606)
        with pytest.raises(StringDBServiceError) as exc_info:
            await service.get_network_interactions(request)
        assert exc_info.value.status_code == 500
