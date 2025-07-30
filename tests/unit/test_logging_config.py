"""Tests for logging configuration."""

from unittest.mock import MagicMock, patch

import pytest


def test_configure_logging_import():
    """Test that logging configuration can be imported."""
    from stringdb_link.logging_config import configure_logging

    assert configure_logging is not None


def test_log_server_startup_import():
    """Test that log_server_startup can be imported."""
    from stringdb_link.logging_config import log_server_startup

    assert log_server_startup is not None


@patch("stringdb_link.logging_config.structlog")
def test_configure_logging_basic(mock_structlog):
    """Test basic logging configuration."""
    from stringdb_link.logging_config import configure_logging

    mock_logger = MagicMock()
    mock_structlog.get_logger.return_value = mock_logger

    logger = configure_logging()

    # Should return a logger
    assert logger is not None
    mock_structlog.get_logger.assert_called_once()


def test_log_server_startup_basic():
    """Test log_server_startup function."""
    from stringdb_link.logging_config import log_server_startup

    mock_logger = MagicMock()

    # Should not raise an exception
    log_server_startup(mock_logger, "startup", "127.0.0.1", 8000)

    # Should have called the logger
    assert mock_logger.info.called


def test_configure_logging_with_debug():
    """Test logging configuration with debug mode."""
    from stringdb_link.logging_config import configure_logging

    # Should not raise an exception
    logger = configure_logging()
    assert logger is not None


def test_logging_imports():
    """Test that all logging-related imports work."""
    # Test that we can import logging functions without errors
    try:
        from stringdb_link.logging_config import (  # noqa: F401
            configure_logging,
            log_server_startup,
        )

        assert True
    except ImportError:
        pytest.fail("Failed to import logging configuration functions")
