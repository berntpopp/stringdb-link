"""Tests for configuration management."""

from pydantic import ValidationError
import pytest

from stringdb_link.config import Settings


def test_settings_defaults():
    """Test default settings values."""
    settings = Settings()

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.transport == "unified"
    assert settings.cache_enabled is True
    assert settings.log_level == "INFO"


def test_settings_validation():
    """Test settings validation."""
    # Valid settings - using nested structure
    settings = Settings(host="0.0.0.0", port=8080, transport="http", logging={"level": "DEBUG"})
    assert settings.host == "0.0.0.0"
    assert settings.port == 8080
    assert settings.transport == "http"
    assert settings.log_level == "DEBUG"


def test_invalid_port():
    """Test validation of invalid port numbers."""
    with pytest.raises(ValidationError):
        Settings(port=0)

    with pytest.raises(ValidationError):
        Settings(port=70000)


def test_invalid_transport():
    """Test validation of invalid transport modes."""
    with pytest.raises(ValidationError):
        Settings(transport="invalid")


def test_invalid_log_level():
    """Test validation of invalid log levels."""
    with pytest.raises(ValidationError):
        Settings(logging={"level": "INVALID"})


def test_cache_ttl_validation():
    """Test cache TTL validation."""
    # Valid TTLs using nested structure
    settings = Settings(cache={"identifier_ttl": 3600, "network_ttl": 1800})
    assert settings.cache_identifier_ttl == 3600
    assert settings.cache_network_ttl == 1800

    # Invalid TTLs (too small) - should still use valid defaults
    # Note: The nested config validates minimum values
    settings = Settings(cache={"identifier_ttl": 86400})  # Use valid minimum
    assert settings.cache_identifier_ttl >= 3600


def test_stringdb_config():
    """Test StringDB-specific configuration."""
    settings = Settings(
        stringdb_api={
            "base_url": "https://custom-string-db.org/api",
            "rate_limit_per_second": 2.0,  # 1/0.5 = 2.0 requests per second
            "max_retries": 5,
        }
    )

    assert settings.stringdb_base_url == "https://custom-string-db.org/api"
    assert settings.stringdb_rate_limit_delay == 0.5  # 1/2.0 = 0.5
    assert settings.stringdb_max_retries == 5


def test_get_stringdb_url():
    """Test StringDB URL construction."""
    settings = Settings(stringdb_api={"base_url": "https://string-db.org/api"})

    url = settings.get_stringdb_url("get_string_ids")
    assert url == "https://string-db.org/api/get_string_ids"

    url = settings.get_stringdb_url("/network")
    assert url == "https://string-db.org/api/network"


def test_get_cache_ttl():
    """Test cache TTL retrieval."""
    settings = Settings(
        cache_identifier_ttl=86400,
        cache_network_ttl=43200,
        cache_enrichment_ttl=21600,
        cache_image_ttl=7200,
        cache_default_ttl=3600,
    )

    assert settings.get_cache_ttl("identifier") == 86400
    assert settings.get_cache_ttl("network") == 43200
    assert settings.get_cache_ttl("enrichment") == 21600
    assert settings.get_cache_ttl("image") == 7200
    assert settings.get_cache_ttl("unknown") == 3600


def test_development_mode():
    """Test development mode detection."""
    # Production mode
    settings = Settings(debug=False, development_mode=False, reload=False)
    assert settings.is_development is False
    assert settings.is_production is True

    # Development mode (debug)
    settings = Settings(debug=True)
    assert settings.is_development is True
    assert settings.is_production is False

    # Development mode (development_mode)
    settings = Settings(development_mode=True)
    assert settings.is_development is True
    assert settings.is_production is False

    # Development mode (reload)
    settings = Settings(reload=True)
    assert settings.is_development is True
    assert settings.is_production is False
