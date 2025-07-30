"""Comprehensive tests for API route error handling."""

# ruff: noqa: ARG002  # Unused method arguments are pytest fixtures

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
import pytest

from stringdb_link.api.routes.dependencies import get_logger_dependency, get_stringdb_service
from stringdb_link.app import app
from stringdb_link.exceptions import StringDBServiceError, ValidationError
from stringdb_link.services.stringdb_service import StringDBService


@pytest.fixture
def mock_service():
    """Mock StringDB service."""
    return AsyncMock(spec=StringDBService)


@pytest.fixture
def mock_logger():
    """Mock logger."""
    return MagicMock()


@pytest.fixture
def client(mock_service, mock_logger):
    """Create test client with mocked dependencies."""
    # Override dependencies
    app.dependency_overrides[get_stringdb_service] = lambda: mock_service
    app.dependency_overrides[get_logger_dependency] = lambda: mock_logger

    test_client = TestClient(app)
    yield test_client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


class TestIdentifierRouteErrorHandling:
    """Test error handling in identifier routes."""

    @pytest.mark.parametrize(
        ("exception", "expected_status"),
        [
            (StringDBServiceError("Service down", operation="resolve_identifiers"), 500),
            (ValidationError("Invalid identifier", field="identifiers"), 400),
            (ValueError("Unexpected value error"), 500),
            (Exception("Generic error"), 500),
        ],
    )
    def test_resolve_identifiers_error_handling(
        self, client, mock_service, mock_logger, exception, expected_status
    ):
        """Test error handling for resolve_identifiers endpoint."""
        # Arrange: Mock the service to raise the specified exception
        mock_service.resolve_identifiers.side_effect = exception

        # Act: Make the request
        response = client.post(
            "/api/identifiers/resolve", json={"identifiers": ["p53"], "species": 9606}
        )

        # Assert: Check the status code and response detail
        assert response.status_code == expected_status
        response_data = response.json()
        assert "detail" in response_data

        # Verify logger was called
        mock_logger.exception.assert_called_once()

        # Verify service was called
        mock_service.resolve_identifiers.assert_called_once()

    @pytest.mark.parametrize(
        ("exception", "expected_status"),
        [
            (StringDBServiceError("Service error", operation="resolve_identifiers"), 500),
            (ValidationError("Validation failed", field="identifier"), 400),
            (Exception("Generic error"), 500),
        ],
    )
    def test_resolve_single_identifier_error_handling(
        self, client, mock_service, mock_logger, exception, expected_status
    ):
        """Test error handling for resolve_single_identifier endpoint."""
        # Arrange: Mock the service to raise the specified exception
        mock_service.resolve_identifiers.side_effect = exception

        # Act: Make the request
        response = client.get("/api/identifiers/resolve/p53")

        # Assert: Check the status code and response detail
        assert response.status_code == expected_status
        response_data = response.json()
        assert "detail" in response_data

        # Verify logger was called for non-HTTP exceptions
        if not isinstance(exception, Exception) or expected_status >= 500:
            mock_logger.exception.assert_called_once()

    def test_resolve_single_identifier_not_found(self, client, mock_service, mock_logger):
        """Test resolve_single_identifier when no mapping is found."""
        # Arrange: Mock service to return empty mappings
        from stringdb_link.models.responses import StringIdMappingListResponse

        mock_service.resolve_identifiers.return_value = StringIdMappingListResponse(
            mappings=[], total_count=0
        )

        # Act: Make the request
        response = client.get("/api/identifiers/resolve/nonexistent")

        # Assert: Check 404 response
        assert response.status_code == 404
        response_data = response.json()
        assert "could not be resolved" in response_data["detail"]


class TestHealthRouteErrorHandling:
    """Test error handling in health routes."""

    def test_health_check_service_error(self, client, mock_service):
        """Test health check with service error."""
        # Mock a service error
        mock_service.get_cache_stats.side_effect = Exception("Service unavailable")

        response = client.get("/api/health")

        # Should still return 200 but with error details
        assert response.status_code == 200
        response_data = response.json()
        assert "status" in response_data


class TestEnrichmentRouteErrorHandling:
    """Test error handling in enrichment routes."""

    @pytest.mark.parametrize(
        ("exception", "expected_status"),
        [
            (
                StringDBServiceError("Enrichment service down", operation="functional_enrichment"),
                500,
            ),
            (ValidationError("Invalid identifiers", field="identifiers"), 400),
            (Exception("Generic enrichment error"), 500),
        ],
    )
    def test_functional_enrichment_error_handling(
        self, client, mock_service, mock_logger, exception, expected_status
    ):
        """Test error handling for functional_enrichment endpoint."""
        # Arrange: Mock the service to raise the specified exception
        mock_service.get_functional_enrichment.side_effect = exception

        # Act: Make the request
        response = client.post(
            "/api/enrichment/functional",
            json={"identifiers": ["9606.ENSP00000269305"], "species": 9606},
        )

        # Assert: Check the status code and response detail
        assert response.status_code == expected_status
        response_data = response.json()
        assert "detail" in response_data

    @pytest.mark.parametrize(
        ("exception", "expected_status"),
        [
            (StringDBServiceError("PPI service down", operation="ppi_enrichment"), 500),
            (ValidationError("Invalid PPI request", field="identifiers"), 400),
            (Exception("Generic PPI error"), 500),
        ],
    )
    def test_ppi_enrichment_error_handling(
        self, client, mock_service, mock_logger, exception, expected_status
    ):
        """Test error handling for ppi_enrichment endpoint."""
        # Arrange: Mock the service to raise the specified exception
        mock_service.get_ppi_enrichment.side_effect = exception

        # Act: Make the request
        response = client.post(
            "/api/enrichment/ppi",
            json={"identifiers": ["9606.ENSP00000269305", "9606.ENSP00000270142"], "species": 9606},
        )

        # Assert: Check the status code and response detail
        assert response.status_code == expected_status
        response_data = response.json()
        assert "detail" in response_data


class TestNetworkRouteErrorHandling:
    """Test error handling in network routes."""

    @pytest.mark.parametrize(
        ("exception", "expected_status"),
        [
            (StringDBServiceError("Network service error", operation="network_interactions"), 500),
            (ValidationError("Invalid network request", field="identifiers"), 400),
            (Exception("Generic network error"), 500),
        ],
    )
    def test_network_interactions_error_handling(
        self, client, mock_service, mock_logger, exception, expected_status
    ):
        """Test error handling for network_interactions endpoint."""
        # Arrange: Mock the service to raise the specified exception
        mock_service.get_network_interactions.side_effect = exception

        # Act: Make the request
        response = client.post(
            "/api/networks/interactions",
            json={"identifiers": ["9606.ENSP00000269305"], "species": 9606},
        )

        # Assert: Check the status code and response detail
        assert response.status_code == expected_status
        response_data = response.json()
        assert "detail" in response_data

    @pytest.mark.parametrize(
        ("exception", "expected_status"),
        [
            (StringDBServiceError("Partners service error", operation="interaction_partners"), 500),
            (ValidationError("Invalid partners request", field="identifiers"), 400),
            (Exception("Generic partners error"), 500),
        ],
    )
    def test_interaction_partners_error_handling(
        self, client, mock_service, mock_logger, exception, expected_status
    ):
        """Test error handling for interaction_partners endpoint."""
        # Arrange: Mock the service to raise the specified exception
        mock_service.get_interaction_partners.side_effect = exception

        # Act: Make the request
        response = client.post(
            "/api/networks/partners",
            json={"identifiers": ["9606.ENSP00000269305"], "species": 9606, "limit": 10},
        )

        # Assert: Check the status code and response detail
        assert response.status_code == expected_status
        response_data = response.json()
        assert "detail" in response_data


class TestHomologyRouteErrorHandling:
    """Test error handling in homology routes."""

    @pytest.mark.parametrize(
        ("exception", "expected_status"),
        [
            (StringDBServiceError("Homology service error", operation="homology_scores"), 500),
            (ValidationError("Invalid homology request", field="identifiers"), 400),
            (Exception("Generic homology error"), 500),
        ],
    )
    def test_homology_scores_error_handling(
        self, client, mock_service, mock_logger, exception, expected_status
    ):
        """Test error handling for homology_scores endpoint."""
        # Arrange: Mock the service to raise the specified exception
        mock_service.get_homology_scores.side_effect = exception

        # Act: Make the request
        response = client.post(
            "/api/homology/scores", json={"identifiers": ["9606.ENSP00000269305"], "species": 9606}
        )

        # Assert: Check the status code and response detail
        assert response.status_code == expected_status
        response_data = response.json()
        assert "detail" in response_data

    @pytest.mark.parametrize(
        ("exception", "expected_status"),
        [
            (StringDBServiceError("Best hits service error", operation="homology_best_hits"), 500),
            (ValidationError("Invalid best hits request", field="identifiers"), 400),
            (Exception("Generic best hits error"), 500),
        ],
    )
    def test_homology_best_hits_error_handling(
        self, client, mock_service, mock_logger, exception, expected_status
    ):
        """Test error handling for homology_best_hits endpoint."""
        # Arrange: Mock the service to raise the specified exception
        mock_service.get_homology_best_hits.side_effect = exception

        # Act: Make the request
        response = client.post(
            "/api/homology/best-hits",
            json={"identifiers": ["9606.ENSP00000269305"], "species": 9606, "species_b": [10090]},
        )

        # Assert: Check the status code and response detail
        assert response.status_code == expected_status
        response_data = response.json()
        assert "detail" in response_data


class TestImageRouteErrorHandling:
    """Test error handling in image routes."""

    @pytest.mark.parametrize(
        ("exception", "expected_status"),
        [
            (StringDBServiceError("Image service error", operation="network_image"), 500),
            (ValidationError("Invalid image request", field="identifiers"), 400),
            (Exception("Generic image error"), 500),
        ],
    )
    def test_network_image_error_handling(
        self, client, mock_service, mock_logger, exception, expected_status
    ):
        """Test error handling for network_image endpoint."""
        # Arrange: Mock the service to raise the specified exception
        mock_service.get_network_image.side_effect = exception

        # Act: Make the request
        response = client.post(
            "/api/images/network", json={"identifiers": ["9606.ENSP00000269305"], "species": 9606}
        )

        # Assert: Check the status code and response detail
        assert response.status_code == expected_status
        response_data = response.json()
        assert "detail" in response_data


class TestAnnotationRouteErrorHandling:
    """Test error handling in annotation routes."""

    @pytest.mark.parametrize(
        ("exception", "expected_status"),
        [
            (
                StringDBServiceError("Annotation service error", operation="functional_annotation"),
                500,
            ),
            (ValidationError("Invalid annotation request", field="identifiers"), 400),
            (Exception("Generic annotation error"), 500),
        ],
    )
    def test_functional_annotation_error_handling(
        self, client, mock_service, mock_logger, exception, expected_status
    ):
        """Test error handling for functional_annotation endpoint."""
        # Arrange: Mock the service to raise the specified exception
        mock_service.get_functional_annotation.side_effect = exception

        # Act: Make the request
        response = client.post(
            "/api/annotations/functional",
            json={"identifiers": ["9606.ENSP00000269305"], "species": 9606},
        )

        # Assert: Check the status code and response detail
        assert response.status_code == expected_status
        response_data = response.json()
        assert "detail" in response_data


class TestRouteExceptionSpecifics:
    """Test specific exception handling behaviors."""

    def test_stringdb_service_error_with_status_code(self, client, mock_service, mock_logger):
        """Test StringDBServiceError with specific status code."""
        # Arrange
        error = StringDBServiceError("Service unavailable", operation="resolve_identifiers")
        mock_service.resolve_identifiers.side_effect = error

        # Act
        response = client.post("/api/identifiers/resolve", json={"identifiers": ["p53"]})

        # Assert
        assert response.status_code == 500
        response_data = response.json()
        assert "Service error: Service unavailable" in response_data["detail"]

    def test_validation_error_with_field_info(self, client, mock_service, mock_logger):
        """Test ValidationError with field information."""
        # Arrange
        error = ValidationError("Identifier list cannot be empty", field="identifiers", value=[])
        mock_service.resolve_identifiers.side_effect = error

        # Act
        response = client.post("/api/identifiers/resolve", json={"identifiers": ["p53"]})

        # Assert
        assert response.status_code == 400
        response_data = response.json()
        assert "Validation error: Identifier list cannot be empty" in response_data["detail"]

        # Verify logger called with field info
        mock_logger.exception.assert_called_once()
        call_args = mock_logger.exception.call_args
        assert "field" in call_args[1]
        assert call_args[1]["field"] == "identifiers"

    def test_logger_exception_calls(self, client, mock_service, mock_logger):
        """Test that logger.exception is called with appropriate context."""
        # Arrange
        mock_service.resolve_identifiers.side_effect = Exception("Test error")

        # Act
        response = client.post("/api/identifiers/resolve", json={"identifiers": ["p53"]})

        # Assert
        assert response.status_code == 500
        mock_logger.exception.assert_called_once()

        # Check the logger call
        call_args = mock_logger.exception.call_args
        assert len(call_args[0]) > 0  # Has a message
        assert "error" in call_args[1]  # Has error kwarg


class TestErrorResponseFormats:
    """Test that error responses have correct format."""

    def test_error_response_contains_detail(self, client, mock_service):
        """Test that all error responses contain a 'detail' field."""
        # Test various endpoints with errors
        test_cases = [
            ("POST", "/api/identifiers/resolve", {"identifiers": ["p53"]}),
            (
                "POST",
                "/api/enrichment/functional",
                {"identifiers": ["9606.ENSP00000269305"], "species": 9606},
            ),
            (
                "POST",
                "/api/networks/interactions",
                {"identifiers": ["9606.ENSP00000269305"], "species": 9606},
            ),
        ]

        for method, endpoint, json_data in test_cases:
            # Arrange: Make service raise an error
            if "identifiers" in endpoint:
                mock_service.resolve_identifiers.side_effect = Exception("Test error")
            elif "enrichment" in endpoint:
                mock_service.get_functional_enrichment.side_effect = Exception("Test error")
            elif "networks" in endpoint:
                mock_service.get_network_interactions.side_effect = Exception("Test error")

            # Act
            if method == "POST":
                response = client.post(endpoint, json=json_data)
            else:
                response = client.get(endpoint)

            # Assert
            assert response.status_code >= 400
            response_data = response.json()
            assert "detail" in response_data
            assert isinstance(response_data["detail"], str)
            assert len(response_data["detail"]) > 0
