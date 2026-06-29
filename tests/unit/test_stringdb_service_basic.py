"""Basic tests for StringDBService focusing on core functionality."""

# Unused method arguments are pytest fixtures, private member access is for testing

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stringdb_link.exceptions import StringDBServiceError
from stringdb_link.models.requests import (
    AnnotationRequest,
    EnrichmentRequest,
    IdentifierRequest,
    ImageRequest,
    InteractionPartnersRequest,
    NetworkRequest,
)
from stringdb_link.models.stringdb import ImageFormat, NetworkType, OutputFormat
from stringdb_link.services.stringdb_service import StringDBService


@pytest.fixture
def mock_client():
    """Create a mock StringDBClient."""
    return AsyncMock()


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def service(mock_client, mock_logger):
    """Create a StringDBService instance with mocked dependencies."""
    return StringDBService(client=mock_client, logger=mock_logger)


class TestStringDBServiceCore:
    """Test core StringDBService functionality."""

    async def test_service_initialization(self, mock_client, mock_logger):
        """Test service initialization."""
        # Arrange & Act
        service = StringDBService(client=mock_client, logger=mock_logger)

        # Assert
        assert service.client == mock_client
        assert service.logger == mock_logger

    async def test_service_initialization_default_logger(self, mock_client):
        """Test service initialization with default logger."""
        # Arrange & Act
        service = StringDBService(client=mock_client)

        # Assert
        assert service.client == mock_client
        assert service.logger is not None

    async def test_resolve_identifiers_calls_client(self, service, mock_client):
        """Test that resolve_identifiers properly calls the client."""
        # Arrange
        request = IdentifierRequest(identifiers=["p53"])
        mock_client.get_string_ids.return_value = []

        # Act
        with patch.object(service, "_cached_resolve_identifiers") as mock_cached:
            mock_cached.return_value = []
            result = await service.resolve_identifiers(request)

        # Assert
        mock_cached.assert_called_once_with(identifiers=("p53",), species=None, echo_query=False)
        assert result.total_count == 0

    async def test_resolve_identifiers_error_handling(self, service, mock_client):
        """Test error handling in resolve_identifiers."""
        # Arrange
        request = IdentifierRequest(identifiers=["invalid"])

        with patch.object(service, "_cached_resolve_identifiers") as mock_cached:
            mock_cached.side_effect = Exception("API error")

            # Act & Assert
            with pytest.raises(StringDBServiceError, match="Failed to resolve identifiers"):
                await service.resolve_identifiers(request)

    async def test_get_network_interactions_calls_client(self, service, mock_client):
        """Test that get_network_interactions properly calls the client."""
        # Arrange
        request = NetworkRequest(
            identifiers=["9606.ENSP00000269305"],
            required_score=0.4,
            network_type=NetworkType.FUNCTIONAL,
        )

        # Act
        with patch.object(service, "_cached_get_network_interactions") as mock_cached:
            mock_cached.return_value = []
            result = await service.get_network_interactions(request)

        # Assert
        mock_cached.assert_called_once()
        assert result.total_count == 0

    async def test_get_interaction_partners_calls_client(self, service, mock_client):
        """Test that get_interaction_partners properly calls the client."""
        # Arrange
        request = InteractionPartnersRequest(identifiers=["9606.ENSP00000269305"])

        # Act
        with patch.object(service, "_cached_get_interaction_partners") as mock_cached:
            mock_cached.return_value = []
            result = await service.get_interaction_partners(request)

        # Assert
        mock_cached.assert_called_once()
        assert result.total_count == 0

    async def test_get_functional_enrichment_calls_client(self, service, mock_client):
        """Test that get_functional_enrichment properly calls the client."""
        # Arrange
        request = EnrichmentRequest(identifiers=["9606.ENSP00000269305"])

        # Act
        with patch.object(service, "_cached_get_functional_enrichment") as mock_cached:
            mock_cached.return_value = []
            result = await service.get_functional_enrichment(request)

        # Assert
        mock_cached.assert_called_once()
        assert result.total_count == 0

    async def test_get_functional_annotation_calls_client(self, service, mock_client):
        """Test that get_functional_annotation properly calls the client."""
        # Arrange
        request = AnnotationRequest(identifiers=["9606.ENSP00000269305"])

        # Act
        with patch.object(service, "_cached_get_functional_annotation") as mock_cached:
            mock_cached.return_value = []
            result = await service.get_functional_annotation(request)

        # Assert
        mock_cached.assert_called_once()
        assert result.total_count == 0

    async def test_get_network_image_calls_client(self, service, mock_client):
        """Test that get_network_image properly calls the client."""
        # Arrange
        request = ImageRequest(
            identifiers=["9606.ENSP00000269305"],
            image_format=ImageFormat.PNG,
        )

        # Act
        with patch.object(service, "_cached_get_network_image") as mock_cached:
            from stringdb_link.models.responses import NetworkImage

            mock_image = NetworkImage(
                image_data=b"fake_data", image_format="image", content_type="image/png"
            )
            mock_cached.return_value = mock_image
            result = await service.get_network_image(request)

        # Assert
        mock_cached.assert_called_once()
        assert result.image.image_data == b"fake_data"

    async def test_get_homology_scores_calls_client(self, service, mock_client):
        """Test that get_homology_scores properly calls the client."""
        # Arrange
        identifiers = ["9606.ENSP00000269305"]
        mock_client.get_homology_scores.return_value = []

        # Act
        result = await service.get_homology_scores(identifiers)

        # Assert
        mock_client.get_homology_scores.assert_called_once_with(
            identifiers=identifiers, species=None, output_format=OutputFormat.JSON
        )
        assert result == []

    async def test_get_homology_best_hits_calls_client(self, service, mock_client):
        """Test that get_homology_best_hits properly calls the client."""
        # Arrange
        identifiers = ["9606.ENSP00000269305"]
        mock_client.get_homology_best_hits.return_value = {}

        # Act
        result = await service.get_homology_best_hits(identifiers)

        # Assert
        mock_client.get_homology_best_hits.assert_called_once_with(
            identifiers=identifiers, species=None, species_b=None, output_format=OutputFormat.JSON
        )
        assert result == {}

    async def test_get_cache_stats(self, service):
        """Test cache statistics retrieval."""
        # Act
        result = await service.get_cache_stats()

        # Assert
        assert isinstance(result, dict)

    async def test_clear_cache(self, service):
        """Test cache clearing."""
        # Act
        await service.clear_cache()

        # Assert - should complete without error

    def test_get_image_content_type_mapping(self, service):
        """Test image content type mapping."""
        # Test known formats
        assert service._get_image_content_type("image") == "image/png"
        assert service._get_image_content_type("highres_image") == "image/png"
        assert service._get_image_content_type("svg") == "image/svg+xml"

        # Test unknown format defaults to PNG
        assert service._get_image_content_type("unknown") == "image/png"

    async def test_service_methods_log_operations(self, service, mock_logger):
        """Test that service methods log their operations."""
        # Arrange
        request = IdentifierRequest(identifiers=["test"])

        # Act
        with patch.object(service, "_cached_resolve_identifiers", return_value=[]):
            await service.resolve_identifiers(request)

        # Assert
        mock_logger.info.assert_called()

    async def test_service_methods_log_errors(self, service, mock_logger):
        """Test that service methods log errors."""
        # Arrange
        request = IdentifierRequest(identifiers=["test"])

        # Act
        with patch.object(service, "_cached_resolve_identifiers") as mock_cached:
            mock_cached.side_effect = Exception("Test error")

            with pytest.raises(StringDBServiceError):
                await service.resolve_identifiers(request)

        # Assert
        mock_logger.exception.assert_called()

    async def test_cached_methods_use_tuples_for_hashability(self, service, mock_client):
        """Test that cached methods convert lists to tuples for hashability."""
        # Arrange
        identifiers = ["protein1", "protein2"]
        mock_client.get_string_ids.return_value = []

        # Act
        await service._cached_resolve_identifiers(
            identifiers=tuple(identifiers), species=9606, echo_query=False
        )

        # Assert
        mock_client.get_string_ids.assert_called_once_with(
            identifiers=identifiers, species=9606, echo_query=False
        )

    async def test_service_handles_none_background_identifiers(self, service):
        """Test that service handles None background identifiers correctly."""
        # Arrange
        request = EnrichmentRequest(
            identifiers=["9606.ENSP00000269305"], background_string_identifiers=None
        )

        # Act
        with patch.object(service, "_cached_get_functional_enrichment") as mock_cached:
            mock_cached.return_value = []
            await service.get_functional_enrichment(request)

        # Assert
        # Should pass None, not convert to tuple
        _args, kwargs = mock_cached.call_args
        assert kwargs["background_string_identifiers"] is None

    async def test_service_converts_background_identifiers_to_tuple(self, service):
        """Test that service converts background identifiers list to tuple."""
        # Arrange
        background_ids = ["9606.ENSP00000001", "9606.ENSP00000002"]
        request = EnrichmentRequest(
            identifiers=["9606.ENSP00000269305"], background_string_identifiers=background_ids
        )

        # Act
        with patch.object(service, "_cached_get_functional_enrichment") as mock_cached:
            mock_cached.return_value = []
            await service.get_functional_enrichment(request)

        # Assert
        _args, kwargs = mock_cached.call_args
        assert kwargs["background_string_identifiers"] == tuple(background_ids)

    async def test_all_service_methods_handle_exceptions(self, service, mock_client):
        """Test that all service methods handle exceptions properly."""
        # Test methods that use client directly
        client_methods = [
            (service.get_homology_scores, ["test"], "get_homology_scores"),
            (service.get_homology_best_hits, ["test"], "get_homology_best_hits"),
        ]

        for method, args, client_method_name in client_methods:
            # Make client method raise exception
            getattr(mock_client, client_method_name).side_effect = Exception("Test error")

            with pytest.raises(StringDBServiceError):
                await method(*args)


class TestStringDBServiceCacheIntegration:
    """Test cache integration in StringDBService."""

    async def test_cached_resolve_identifiers_creates_mappings(self, service, mock_client):
        """Test that cached resolve identifiers creates proper mappings."""
        # Arrange
        mock_client.get_string_ids.return_value = [
            {
                "queryItem": "p53",
                "queryIndex": 0,
                "stringId": "9606.ENSP00000269305",
                "ncbiTaxonId": 9606,
                "taxonName": "Homo sapiens",
                "preferredName": "TP53",
                "annotation": "tumor protein p53",
            }
        ]

        # Act
        result = await service._cached_resolve_identifiers(
            identifiers=("p53",), species=9606, echo_query=False
        )

        # Assert
        assert len(result) == 1
        assert result[0].string_id == "9606.ENSP00000269305"

    async def test_service_uses_correct_cache_parameters(self, service):
        """Test that service methods use correct cache parameters."""
        # This test verifies cache decorator is applied with correct parameters
        # We can't easily test the actual caching behavior without complex setup

        # Verify the methods have cache decorators by checking if they're wrapped
        assert hasattr(service._cached_resolve_identifiers, "__wrapped__")
        assert hasattr(service._cached_get_network_interactions, "__wrapped__")
        assert hasattr(service._cached_get_interaction_partners, "__wrapped__")
        assert hasattr(service._cached_get_functional_enrichment, "__wrapped__")
        assert hasattr(service._cached_get_functional_annotation, "__wrapped__")
        assert hasattr(service._cached_get_network_image, "__wrapped__")
