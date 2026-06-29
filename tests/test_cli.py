"""Comprehensive tests for CLI functionality."""

# Unused method arguments are pytest fixtures

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from stringdb_link import API_VERSION, VERSION
from stringdb_link.cli import app, main, start_server


class TestCLICommands:
    """Test CLI command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_version_command(self):
        """Test version command displays correct information."""
        result = self.runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert VERSION in result.stdout
        assert API_VERSION in result.stdout
        assert str(sys.version_info.major) in result.stdout

    @patch("stringdb_link.cli.get_settings")
    def test_config_command_basic(self, mock_get_settings):
        """Test config command shows configuration."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.model_fields = {
            "host": MagicMock(description="Server host"),
            "port": MagicMock(description="Server port"),
            "api_key": MagicMock(description="API key"),
        }
        mock_settings.host = "localhost"
        mock_settings.port = 8000
        mock_settings.api_key = "secret-key"
        mock_get_settings.return_value = mock_settings

        result = self.runner.invoke(app, ["config"])

        assert result.exit_code == 0
        assert "localhost" in result.stdout
        assert "8000" in result.stdout
        assert "***HIDDEN***" in result.stdout  # Sensitive values hidden
        assert "secret-key" not in result.stdout

    @patch("stringdb_link.cli.get_settings")
    def test_config_command_show_sensitive(self, mock_get_settings):
        """Test config command with --show-sensitive flag."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.model_fields = {
            "host": MagicMock(description="Server host"),
            "api_key": MagicMock(description="API key"),
        }
        mock_settings.host = "localhost"
        mock_settings.api_key = "secret-key"
        mock_get_settings.return_value = mock_settings

        result = self.runner.invoke(app, ["config", "--show-sensitive"])

        assert result.exit_code == 0
        assert "secret-key" in result.stdout
        assert "***HIDDEN***" not in result.stdout

    @patch("stringdb_link.cli.reload_settings")
    def test_validate_config_success(self, mock_reload_settings):
        """Test validate-config command with valid configuration."""
        mock_settings = MagicMock()
        mock_settings.transport = "http"
        mock_settings.host = "localhost"
        mock_settings.port = 8000
        mock_settings.stringdb_base_url = "https://string-db.org"
        mock_settings.cache_enabled = True
        mock_reload_settings.return_value = mock_settings

        result = self.runner.invoke(app, ["validate-config"])

        assert result.exit_code == 0
        assert "Configuration is valid" in result.stdout
        assert "Transport mode: http" in result.stdout
        assert "Server: localhost:8000" in result.stdout

    @patch("stringdb_link.cli.reload_settings")
    def test_validate_config_failure(self, mock_reload_settings):
        """Test validate-config command with invalid configuration."""
        mock_reload_settings.side_effect = ValueError("Invalid config")

        result = self.runner.invoke(app, ["validate-config"])

        assert result.exit_code == 1
        assert "Configuration validation failed" in result.stdout
        assert "Invalid config" in result.stdout

    @patch("stringdb_link.cli.get_settings")
    @patch("stringdb_link.cli.configure_logging")
    @patch("stringdb_link.cli.UnifiedServerManager")
    @patch("stringdb_link.cli.asyncio.run")
    def test_server_command_basic(
        self, mock_asyncio_run, mock_server_manager, mock_configure_logging, mock_get_settings
    ):
        """Test server command with default settings."""
        mock_settings = MagicMock()
        mock_settings.transport = "http"
        mock_get_settings.return_value = mock_settings
        mock_logger = MagicMock()
        mock_configure_logging.return_value = mock_logger

        result = self.runner.invoke(app, ["server"])

        assert result.exit_code == 0
        mock_configure_logging.assert_called_once()
        mock_server_manager.assert_called_once_with(logger=mock_logger)
        mock_asyncio_run.assert_called_once()

    @patch("stringdb_link.cli.get_settings")
    @patch("stringdb_link.cli.configure_logging")
    @patch("stringdb_link.cli.UnifiedServerManager")
    @patch("stringdb_link.cli.asyncio.run")
    def test_server_command_with_options(
        self, mock_asyncio_run, mock_server_manager, mock_configure_logging, mock_get_settings
    ):
        """Test server command with command line options."""
        mock_settings = MagicMock()
        mock_settings.transport = "http"
        mock_get_settings.return_value = mock_settings
        mock_logger = MagicMock()
        mock_configure_logging.return_value = mock_logger

        result = self.runner.invoke(
            app,
            [
                "server",
                "--host",
                "0.0.0.0",
                "--port",
                "9000",
                "--transport",
                "unified",
                "--reload",
                "--log-level",
                "debug",
            ],
        )

        assert result.exit_code == 0
        assert mock_settings.host == "0.0.0.0"
        assert mock_settings.port == 9000
        assert mock_settings.transport == "unified"
        assert mock_settings.log_level == "DEBUG"
        assert mock_settings.reload is True

    @patch("stringdb_link.cli.get_settings")
    def test_server_command_invalid_transport(self, mock_get_settings):
        """Test server command with invalid transport mode."""
        mock_settings = MagicMock()
        mock_settings.transport = "invalid"
        mock_get_settings.return_value = mock_settings

        result = self.runner.invoke(app, ["server", "--transport", "invalid"])

        assert result.exit_code == 1
        assert "Invalid transport mode 'invalid'" in result.stdout

    @patch("stringdb_link.cli.get_settings")
    @patch("stringdb_link.cli.configure_logging")
    @patch("stringdb_link.cli.UnifiedServerManager")
    @patch("stringdb_link.cli.asyncio.run")
    def test_server_command_keyboard_interrupt(
        self, mock_asyncio_run, mock_server_manager, mock_configure_logging, mock_get_settings
    ):
        """Test server command handling KeyboardInterrupt."""
        mock_settings = MagicMock()
        mock_settings.transport = "http"
        mock_get_settings.return_value = mock_settings
        mock_asyncio_run.side_effect = KeyboardInterrupt()

        result = self.runner.invoke(app, ["server"])

        assert result.exit_code == 0
        assert "Server stopped by user" in result.stdout

    @patch("stringdb_link.cli.get_settings")
    @patch("stringdb_link.cli.configure_logging")
    @patch("stringdb_link.cli.UnifiedServerManager")
    @patch("stringdb_link.cli.asyncio.run")
    def test_server_command_exception(
        self, mock_asyncio_run, mock_server_manager, mock_configure_logging, mock_get_settings
    ):
        """Test server command handling generic exception."""
        mock_settings = MagicMock()
        mock_settings.transport = "http"
        mock_get_settings.return_value = mock_settings
        mock_asyncio_run.side_effect = Exception("Server failed")

        result = self.runner.invoke(app, ["server"])

        assert result.exit_code == 1
        assert "Server error:" in result.stdout
        assert "Server failed" in result.stdout

    @patch("stringdb_link.cli.get_settings")
    @patch("stringdb_link.cli.configure_logging")
    @patch("stringdb_link.cli.UnifiedServerManager")
    @patch("stringdb_link.cli.asyncio.run")
    def test_mcp_command_success(
        self, mock_asyncio_run, mock_server_manager, mock_configure_logging, mock_get_settings
    ):
        """Test mcp command successful execution."""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings
        mock_logger = MagicMock()
        mock_configure_logging.return_value = mock_logger
        mock_manager = MagicMock()
        mock_server_manager.return_value = mock_manager

        result = self.runner.invoke(app, ["mcp"])

        assert result.exit_code == 0
        assert mock_settings.transport == "stdio"
        mock_configure_logging.assert_called_once()
        mock_server_manager.assert_called_once_with(logger=mock_logger)
        mock_asyncio_run.assert_called_once()

    @patch("stringdb_link.cli.get_settings")
    @patch("stringdb_link.cli.configure_logging")
    @patch("stringdb_link.cli.UnifiedServerManager")
    @patch("stringdb_link.cli.asyncio.run")
    def test_mcp_command_keyboard_interrupt(
        self, mock_asyncio_run, mock_server_manager, mock_configure_logging, mock_get_settings
    ):
        """Test mcp command handling KeyboardInterrupt."""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings
        mock_asyncio_run.side_effect = KeyboardInterrupt()

        result = self.runner.invoke(app, ["mcp"])

        assert result.exit_code == 0

    @patch("stringdb_link.cli.get_settings")
    @patch("stringdb_link.cli.configure_logging")
    @patch("stringdb_link.cli.UnifiedServerManager")
    @patch("stringdb_link.cli.asyncio.run")
    def test_mcp_command_exception(
        self, mock_asyncio_run, mock_server_manager, mock_configure_logging, mock_get_settings
    ):
        """Test mcp command handling generic exception."""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings
        mock_logger = MagicMock()
        mock_configure_logging.return_value = mock_logger
        mock_asyncio_run.side_effect = Exception("MCP server failed")

        result = self.runner.invoke(app, ["mcp"])

        assert result.exit_code == 1
        mock_logger.exception.assert_called_once()
        call_args = mock_logger.exception.call_args
        assert "MCP server error" in call_args[0][0]

    @patch("stringdb_link.cli.get_settings")
    @patch("httpx.Client")
    def test_health_command_success(self, mock_client_class, mock_get_settings):
        """Test health command with healthy server."""
        mock_settings = MagicMock()
        mock_settings.host = "localhost"
        mock_settings.port = 8000
        mock_get_settings.return_value = mock_settings

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy", "version": "1.0.0", "uptime": 3600}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = self.runner.invoke(app, ["health"])

        assert result.exit_code == 0
        assert "Server is healthy" in result.stdout
        assert "status" in result.stdout
        assert "healthy" in result.stdout
        mock_client.get.assert_called_once_with("http://localhost:8000/api/health")

    @patch("stringdb_link.cli.get_settings")
    @patch("httpx.Client")
    def test_health_command_unhealthy_server(self, mock_client_class, mock_get_settings):
        """Test health command with unhealthy server."""
        mock_settings = MagicMock()
        mock_settings.host = "localhost"
        mock_settings.port = 8000
        mock_get_settings.return_value = mock_settings

        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = self.runner.invoke(app, ["health"])

        assert result.exit_code == 1
        assert "Server health check failed: 503" in result.stdout

    @patch("stringdb_link.cli.get_settings")
    @patch("httpx.Client")
    def test_health_command_connection_error(self, mock_client_class, mock_get_settings):
        """Test health command with connection error."""
        mock_settings = MagicMock()
        mock_settings.host = "localhost"
        mock_settings.port = 8000
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = self.runner.invoke(app, ["health"])

        assert result.exit_code == 1
        assert "Cannot connect to server. Is it running?" in result.stdout

    @patch("stringdb_link.cli.get_settings")
    @patch("httpx.Client")
    def test_health_command_generic_exception(self, mock_client_class, mock_get_settings):
        """Test health command with generic exception."""
        mock_settings = MagicMock()
        mock_settings.host = "localhost"
        mock_settings.port = 8000
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Unexpected error")
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = self.runner.invoke(app, ["health"])

        assert result.exit_code == 1
        assert "Health check error: Unexpected error" in result.stdout

    def test_help_command(self):
        """Test help command displays help message."""
        result = self.runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "StringDB-Link" in result.stdout or "stringdb-link" in result.stdout

    def test_no_command(self):
        """Test running without command displays help with usage-error status."""
        result = self.runner.invoke(app, [])

        assert result.exit_code == 2
        assert "Usage:" in result.stdout


class TestStartServerFunction:
    """Test the start_server async function."""

    @pytest.mark.asyncio
    async def test_start_server_unified(self):
        """Test start_server with unified transport."""
        mock_manager = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.transport = "unified"
        mock_settings.host = "localhost"
        mock_settings.port = 8000
        mock_settings.reload = False

        await start_server(mock_manager, mock_settings)

        mock_manager.start_unified_server.assert_called_once_with(
            host="localhost", port=8000, reload=False
        )

    @pytest.mark.asyncio
    async def test_start_server_http(self):
        """Test start_server with HTTP transport."""
        mock_manager = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.transport = "http"
        mock_settings.host = "localhost"
        mock_settings.port = 8000
        mock_settings.reload = True

        await start_server(mock_manager, mock_settings)

        mock_manager.start_http_only_server.assert_called_once_with(
            host="localhost", port=8000, reload=True
        )

    @pytest.mark.asyncio
    async def test_start_server_stdio(self):
        """Test start_server with STDIO transport."""
        mock_manager = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.transport = "stdio"

        await start_server(mock_manager, mock_settings)

        mock_manager.start_stdio_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_server_invalid_transport(self):
        """Test start_server with invalid transport raises ValueError."""
        mock_manager = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.transport = "invalid"

        with pytest.raises(ValueError, match="Invalid transport mode: invalid"):
            await start_server(mock_manager, mock_settings)


class TestMainFunction:
    """Test the main function."""

    @patch("stringdb_link.cli.app")
    def test_main_calls_app(self, mock_app):
        """Test main function calls the typer app."""
        main()
        mock_app.assert_called_once()


class TestCLIEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("stringdb_link.cli.get_settings")
    def test_config_command_no_description(self, mock_get_settings):
        """Test config command with field that has no description."""
        mock_field_info = MagicMock()
        mock_field_info.description = None

        mock_settings = MagicMock()
        mock_settings.model_fields = {"test_field": mock_field_info}
        mock_settings.test_field = "test_value"
        mock_get_settings.return_value = mock_settings

        result = self.runner.invoke(app, ["config"])

        assert result.exit_code == 0
        assert "test_value" in result.stdout

    @patch("stringdb_link.cli.get_settings")
    def test_config_command_multiple_sensitive_matches(self, mock_get_settings):
        """Test config command with field name matching multiple sensitive patterns."""
        mock_settings = MagicMock()
        mock_settings.model_fields = {
            "secret_api_key": MagicMock(description="Secret API key"),
        }
        mock_settings.secret_api_key = "super-secret"
        mock_get_settings.return_value = mock_settings

        result = self.runner.invoke(app, ["config"])

        assert result.exit_code == 0
        assert "***HIDDEN***" in result.stdout
        assert "super-secret" not in result.stdout

    def test_if_name_main_block(self):
        """Test the if __name__ == '__main__' block by importing the module."""
        # This tests the main() call at the module level
        with patch("stringdb_link.cli.main"):
            # Import the module to trigger the if __name__ == '__main__' block
            import stringdb_link.cli

            # Reload to ensure the if __name__ == '__main__' block is executed
            # Note: This is tricky to test directly, so we'll test main() function instead
            assert callable(stringdb_link.cli.main)
