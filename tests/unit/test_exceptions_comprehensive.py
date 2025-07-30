"""Comprehensive tests for exceptions module."""

from stringdb_link.exceptions import (
    CacheError,
    ConfigurationError,
    MCPError,
    NetworkError,
    ProteinNotFoundError,
    ServiceUnavailableError,
    StringDBAPIError,
    StringDBLinkError,
    StringDBRateLimitError,
    StringDBServiceError,
    StringDBTimeoutError,
    ValidationError,
)


class TestStringDBLinkError:
    """Test base StringDBLinkError class."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = StringDBLinkError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.status_code is None
        assert error.details == {}

    def test_error_with_status_code(self):
        """Test error with status code."""
        error = StringDBLinkError("Test error", status_code=400)
        assert error.status_code == 400

    def test_error_with_details(self):
        """Test error with details."""
        details = {"field": "identifiers", "value": "invalid"}
        error = StringDBLinkError("Test error", details=details)
        assert error.details == details

    def test_error_to_dict(self):
        """Test converting error to dictionary."""
        error = StringDBLinkError("Test error", status_code=400, details={"field": "test"})
        result = error.to_dict()

        expected = {
            "error": "StringDBLinkError",
            "message": "Test error",
            "status_code": 400,
            "details": {"field": "test"},
        }
        assert result == expected

    def test_error_to_dict_minimal(self):
        """Test converting minimal error to dictionary."""
        error = StringDBLinkError("Test error")
        result = error.to_dict()

        expected = {
            "error": "StringDBLinkError",
            "message": "Test error",
        }
        assert result == expected


class TestStringDBAPIError:
    """Test StringDBAPIError class."""

    def test_api_error_inheritance(self):
        """Test API error inherits from base error."""
        error = StringDBAPIError("API error")
        assert isinstance(error, StringDBLinkError)
        assert str(error) == "API error"

    def test_api_error_with_status(self):
        """Test API error with HTTP status."""
        error = StringDBAPIError("Server error", status_code=500)
        assert error.status_code == 500

    def test_api_error_to_dict(self):
        """Test API error dictionary conversion."""
        error = StringDBAPIError("API error", status_code=400)
        result = error.to_dict()
        assert result["error"] == "StringDBAPIError"
        assert result["message"] == "API error"
        assert result["status_code"] == 400


class TestStringDBTimeoutError:
    """Test StringDBTimeoutError class."""

    def test_timeout_error_inheritance(self):
        """Test timeout error inherits from API error."""
        error = StringDBTimeoutError("Timeout error")
        assert isinstance(error, StringDBAPIError)
        assert isinstance(error, StringDBLinkError)

    def test_timeout_error_message(self):
        """Test timeout error message."""
        error = StringDBTimeoutError("Request timed out")
        assert str(error) == "Request timed out"

    def test_timeout_error_dict(self):
        """Test timeout error dictionary."""
        error = StringDBTimeoutError("Timeout")
        result = error.to_dict()
        assert result["error"] == "StringDBTimeoutError"


class TestStringDBRateLimitError:
    """Test StringDBRateLimitError class."""

    def test_rate_limit_error_basic(self):
        """Test basic rate limit error."""
        error = StringDBRateLimitError("Rate limited")
        assert str(error) == "Rate limited"
        assert isinstance(error, StringDBAPIError)

    def test_rate_limit_error_with_retry_after(self):
        """Test rate limit error with retry after."""
        error = StringDBRateLimitError("Rate limited", retry_after=60)
        assert error.status_code == 429
        assert error.retry_after == 60


class TestValidationError:
    """Test ValidationError class."""

    def test_validation_error_basic(self):
        """Test basic validation error."""
        error = ValidationError("Invalid input")
        assert str(error) == "Invalid input"
        assert isinstance(error, StringDBLinkError)

    def test_validation_error_with_field(self):
        """Test validation error with field details."""
        error = ValidationError("Invalid species", field="species", value=-1)
        assert error.field == "species"
        assert error.value == -1

    def test_validation_error_dict(self):
        """Test validation error dictionary."""
        error = ValidationError("Validation failed")
        result = error.to_dict()
        assert result["error"] == "ValidationError"


class TestProteinNotFoundError:
    """Test ProteinNotFoundError class."""

    def test_protein_not_found_basic(self):
        """Test basic protein not found error."""
        error = ProteinNotFoundError("test_protein")
        assert str(error) == "Protein identifier 'test_protein' not found"
        assert isinstance(error, StringDBLinkError)

    def test_protein_not_found_with_protein(self):
        """Test protein not found error with protein identifier."""
        error = ProteinNotFoundError("unknown_protein", species=9606)
        assert error.identifier == "unknown_protein"
        assert error.species == 9606


class TestNetworkError:
    """Test NetworkError class."""

    def test_network_error_basic(self):
        """Test basic network error."""
        error = NetworkError("Network failure")
        assert str(error) == "Network failure"
        assert isinstance(error, StringDBLinkError)

    def test_network_error_with_details(self):
        """Test network error with connection details."""
        error = NetworkError("Connection failed", endpoint="https://string-db.org/api")
        assert error.endpoint == "https://string-db.org/api"


class TestCacheError:
    """Test CacheError class."""

    def test_cache_error_basic(self):
        """Test basic cache error."""
        error = CacheError("Cache failure")
        assert str(error) == "Cache failure"
        assert isinstance(error, StringDBLinkError)

    def test_cache_error_with_operation(self):
        """Test cache error with operation details."""
        error = CacheError("Cache set failed", operation="set", cache_key="test_key")
        assert error.operation == "set"
        assert error.cache_key == "test_key"


class TestConfigurationError:
    """Test ConfigurationError class."""

    def test_config_error_basic(self):
        """Test basic configuration error."""
        error = ConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"
        assert isinstance(error, StringDBLinkError)

    def test_config_error_with_setting(self):
        """Test configuration error with setting details."""
        error = ConfigurationError("Invalid port", setting="port", value="invalid")
        assert error.setting == "port"
        assert error.value == "invalid"


class TestMCPError:
    """Test MCPError class."""

    def test_mcp_error_basic(self):
        """Test basic MCP error."""
        error = MCPError("MCP protocol error")
        assert str(error) == "MCP protocol error"
        assert isinstance(error, StringDBLinkError)

    def test_mcp_error_with_tool(self):
        """Test MCP error with tool details."""
        error = MCPError("Tool execution failed", tool_name="get_identifiers")
        assert error.tool_name == "get_identifiers"


class TestServiceUnavailableError:
    """Test ServiceUnavailableError class."""

    def test_service_unavailable_basic(self):
        """Test basic service unavailable error."""
        error = ServiceUnavailableError("Service unavailable")
        assert str(error) == "Service unavailable"
        assert isinstance(error, StringDBLinkError)

    def test_service_unavailable_with_service(self):
        """Test service unavailable error with service details."""
        error = ServiceUnavailableError("StringDB API unavailable", service="stringdb_api")
        assert error.service == "stringdb_api"


class TestStringDBServiceError:
    """Test StringDBServiceError class."""

    def test_service_error_basic(self):
        """Test basic service error."""
        error = StringDBServiceError("Service error")
        assert str(error) == "Service error"
        assert isinstance(error, StringDBLinkError)

    def test_service_error_with_method(self):
        """Test service error with method details."""
        error = StringDBServiceError("Method failed", operation="resolve_identifiers")
        assert error.operation == "resolve_identifiers"


class TestErrorInheritance:
    """Test error inheritance hierarchy."""

    def test_all_errors_inherit_from_base(self):
        """Test that all errors inherit from StringDBLinkError."""
        error_classes = [
            StringDBAPIError,
            StringDBTimeoutError,
            StringDBRateLimitError,
            ValidationError,
            ProteinNotFoundError,
            NetworkError,
            CacheError,
            ConfigurationError,
            MCPError,
            ServiceUnavailableError,
            StringDBServiceError,
        ]

        for error_class in error_classes:
            if error_class == ProteinNotFoundError:
                error = error_class("test_protein")
            else:
                error = error_class("Test message")
            assert isinstance(error, StringDBLinkError)

    def test_api_error_hierarchy(self):
        """Test API error hierarchy."""
        api_errors = [StringDBTimeoutError, StringDBRateLimitError]

        for error_class in api_errors:
            error = error_class("Test message")
            assert isinstance(error, StringDBAPIError)
            assert isinstance(error, StringDBLinkError)

    def test_error_class_names_in_dict(self):
        """Test that error class names are correctly set in to_dict."""
        errors = [
            (StringDBLinkError("test"), "StringDBLinkError"),
            (StringDBAPIError("test"), "StringDBAPIError"),
            (StringDBTimeoutError("test"), "StringDBTimeoutError"),
            (StringDBRateLimitError("test"), "StringDBRateLimitError"),
            (ValidationError("test"), "ValidationError"),
            (ProteinNotFoundError("test_protein"), "ProteinNotFoundError"),
            (NetworkError("test"), "NetworkError"),
            (CacheError("test"), "CacheError"),
            (ConfigurationError("test"), "ConfigurationError"),
            (MCPError("test"), "MCPError"),
            (ServiceUnavailableError("test"), "ServiceUnavailableError"),
            (StringDBServiceError("test"), "StringDBServiceError"),
        ]

        for error, expected_name in errors:
            result = error.to_dict()
            assert result["error"] == expected_name


class TestErrorUsagePatterns:
    """Test common error usage patterns."""

    def test_api_error_with_http_status_codes(self):
        """Test API errors with common HTTP status codes."""
        status_codes = [400, 401, 403, 404, 429, 500, 502, 503, 504]

        for status_code in status_codes:
            error = StringDBAPIError(f"Error {status_code}", status_code=status_code)
            assert error.status_code == status_code
            result = error.to_dict()
            assert result["status_code"] == status_code

    def test_error_chaining_pattern(self):
        """Test error details for chaining information."""
        original_error = ValueError("Connection refused")
        error = NetworkError("Failed to connect to StringDB", original_error=original_error)

        assert error.original_error == original_error
        result = error.to_dict()
        assert "original_error" in result["details"]

    def test_validation_error_field_patterns(self):
        """Test validation error patterns with field information."""
        field_errors = [
            ("identifiers", [], "Empty identifiers list"),
            ("species", -1, "Invalid species ID"),
            ("required_score", 1001, "Score out of range"),
        ]

        for field, value, message in field_errors:
            error = ValidationError(message, field=field, value=value)
            assert error.field == field
            assert error.value == value
