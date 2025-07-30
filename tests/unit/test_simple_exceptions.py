"""Simple tests for exception classes to increase coverage."""

from stringdb_link.exceptions import (
    CacheError,
    ConfigurationError,
    NetworkError,
    StringDBAPIError,
    StringDBRateLimitError,
    StringDBServiceError,
    StringDBTimeoutError,
    ValidationError,
)


def test_validation_error():
    """Test ValidationError basic functionality."""
    error = ValidationError("Invalid input")
    assert error.message == "Invalid input"
    assert str(error) == "Invalid input"

    # Test to_dict method
    error_dict = error.to_dict()
    assert error_dict["error"] == "ValidationError"
    assert error_dict["message"] == "Invalid input"


def test_configuration_error():
    """Test ConfigurationError basic functionality."""
    error = ConfigurationError("Config missing")
    assert error.message == "Config missing"
    assert str(error) == "Config missing"


def test_stringdb_api_error():
    """Test StringDBAPIError basic functionality."""
    error = StringDBAPIError("API error", status_code=500)
    assert error.message == "API error"
    assert error.status_code == 500

    error_dict = error.to_dict()
    assert error_dict["status_code"] == 500


def test_network_error():
    """Test NetworkError basic functionality."""
    error = NetworkError("Connection failed")
    assert error.message == "Connection failed"
    assert str(error) == "Connection failed"


def test_stringdb_rate_limit_error():
    """Test StringDBRateLimitError basic functionality."""
    error = StringDBRateLimitError("Rate limited")
    assert error.message == "Rate limited"
    assert isinstance(error, StringDBAPIError)


def test_stringdb_timeout_error():
    """Test StringDBTimeoutError basic functionality."""
    error = StringDBTimeoutError("Timeout")
    assert error.message == "Timeout"
    assert isinstance(error, StringDBAPIError)


def test_cache_error():
    """Test CacheError basic functionality."""
    error = CacheError("Cache failed")
    assert error.message == "Cache failed"


def test_stringdb_service_error():
    """Test StringDBServiceError basic functionality."""
    error = StringDBServiceError("Service error")
    assert error.message == "Service error"
    assert str(error) == "Service error"
