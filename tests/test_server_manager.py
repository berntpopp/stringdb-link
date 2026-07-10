"""Comprehensive tests for server manager functionality."""

# Unused method arguments are pytest fixtures

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import uvicorn

from stringdb_link.server_manager import UnifiedServerManager


class TestUnifiedServerManager:
    """Test UnifiedServerManager class."""

    def test_init_with_logger(self):
        """Test initialization with logger."""
        mock_logger = MagicMock()
        manager = UnifiedServerManager(logger=mock_logger)

        assert manager.logger == mock_logger

    def test_init_without_logger(self):
        """Test initialization without logger."""
        manager = UnifiedServerManager()

        assert manager.logger is None

    @pytest.mark.asyncio
    @patch("stringdb_link.server_manager.uvicorn.Server")
    @patch("stringdb_link.server_manager.log_server_startup")
    @patch("stringdb_link.server_manager.app")
    @patch("stringdb_link.server_manager.mcp_app")
    @patch("stringdb_link.server_manager.settings")
    async def test_start_unified_server_with_logger(
        self, mock_settings, mock_mcp_app, mock_app, mock_log_startup, mock_server_class
    ):
        """Test start_unified_server with logger."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_settings.mcp_path = "/mcp"
        mock_mcp_http_app = MagicMock()
        mock_mcp_app.http_app.return_value = mock_mcp_http_app
        mock_server = AsyncMock()
        mock_server_class.return_value = mock_server

        # Create manager and start server
        manager = UnifiedServerManager(logger=mock_logger)
        await manager.start_unified_server(host="0.0.0.0", port=9000, reload=True)

        # Verify logging
        mock_log_startup.assert_called_once_with(mock_logger, "unified", "0.0.0.0", 9000)

        # Verify MCP endpoint mounting (stateless transport pattern)
        mock_mcp_app.http_app.assert_called_once_with(
            path="/mcp",
            stateless_http=True,
            json_response=True,
            host_origin_protection=True,
            allowed_hosts=mock_settings.allowed_hosts,
            allowed_origins=mock_settings.allowed_origins,
        )
        mock_app.mount.assert_called_once_with("/", mock_mcp_http_app)

        # Verify uvicorn config
        mock_server_class.assert_called_once()
        config_call = mock_server_class.call_args[0][0]
        assert config_call.app == mock_app
        assert config_call.host == "0.0.0.0"
        assert config_call.port == 9000
        assert config_call.reload is True
        assert config_call.log_config is None
        assert config_call.access_log is False

        # Verify server start
        mock_server.serve.assert_called_once()

    @pytest.mark.asyncio
    @patch("stringdb_link.server_manager.uvicorn.Server")
    @patch("stringdb_link.server_manager.app")
    @patch("stringdb_link.server_manager.mcp_app")
    @patch("stringdb_link.server_manager.settings")
    async def test_start_unified_server_without_logger(
        self, mock_settings, mock_mcp_app, mock_app, mock_server_class
    ):
        """Test start_unified_server without logger."""
        # Setup mocks
        mock_settings.mcp_path = "/mcp"
        mock_mcp_http_app = MagicMock()
        mock_mcp_app.http_app.return_value = mock_mcp_http_app
        mock_server = AsyncMock()
        mock_server_class.return_value = mock_server

        # Create manager without logger and start server
        manager = UnifiedServerManager()
        await manager.start_unified_server()

        # Verify MCP endpoint mounting (stateless transport pattern)
        mock_mcp_app.http_app.assert_called_once_with(
            path="/mcp",
            stateless_http=True,
            json_response=True,
            host_origin_protection=True,
            allowed_hosts=mock_settings.allowed_hosts,
            allowed_origins=mock_settings.allowed_origins,
        )
        mock_app.mount.assert_called_once_with("/", mock_mcp_http_app)

        # Verify server start
        mock_server.serve.assert_called_once()

    @pytest.mark.asyncio
    @patch("stringdb_link.server_manager.uvicorn.Server")
    @patch("stringdb_link.server_manager.log_server_startup")
    @patch("stringdb_link.server_manager.app")
    async def test_start_http_only_server_with_logger(
        self, mock_app, mock_log_startup, mock_server_class
    ):
        """Test start_http_only_server with logger."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_server = AsyncMock()
        mock_server_class.return_value = mock_server

        # Create manager and start server
        manager = UnifiedServerManager(logger=mock_logger)
        await manager.start_http_only_server(host="localhost", port=8080, reload=False)

        # Verify logging
        mock_log_startup.assert_called_once_with(mock_logger, "http", "localhost", 8080)

        # Verify uvicorn config
        mock_server_class.assert_called_once()
        config_call = mock_server_class.call_args[0][0]
        assert config_call.app == mock_app
        assert config_call.host == "localhost"
        assert config_call.port == 8080
        assert config_call.reload is False
        assert config_call.log_config is None
        assert config_call.access_log is False

        # Verify server start
        mock_server.serve.assert_called_once()

    @pytest.mark.asyncio
    @patch("stringdb_link.server_manager.uvicorn.Server")
    @patch("stringdb_link.server_manager.app")
    async def test_start_http_only_server_without_logger(self, mock_app, mock_server_class):
        """Test start_http_only_server without logger."""
        # Setup mocks
        mock_server = AsyncMock()
        mock_server_class.return_value = mock_server

        # Create manager without logger and start server
        manager = UnifiedServerManager()
        await manager.start_http_only_server()

        # Verify server start with default parameters
        mock_server_class.assert_called_once()
        config_call = mock_server_class.call_args[0][0]
        assert config_call.host == "127.0.0.1"
        assert config_call.port == 8000
        assert config_call.reload is False

        mock_server.serve.assert_called_once()

    @pytest.mark.asyncio
    @patch("stringdb_link.app.create_mcp_app")
    @patch("stringdb_link.app.create_app")
    @patch("stringdb_link.app.lifespan")
    async def test_start_stdio_server_with_logger(
        self, mock_lifespan, mock_create_app, mock_create_mcp_app
    ):
        """Test start_stdio_server with logger."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_app = MagicMock()
        mock_mcp = AsyncMock()
        mock_create_app.return_value = mock_app
        mock_create_mcp_app.return_value = mock_mcp
        mock_lifespan.return_value.__aenter__ = AsyncMock()
        mock_lifespan.return_value.__aexit__ = AsyncMock()

        # Create manager and start STDIO server
        manager = UnifiedServerManager(logger=mock_logger)
        await manager.start_stdio_server()

        # Verify logging calls
        assert mock_logger.info.call_count >= 1
        mock_logger.info.assert_any_call("Starting MCP STDIO server")

        # Verify MCP server start
        mock_mcp.run_async.assert_called_once_with(transport="stdio")

    @pytest.mark.asyncio
    @patch("stringdb_link.app.create_mcp_app")
    @patch("stringdb_link.app.create_app")
    @patch("stringdb_link.app.lifespan")
    async def test_start_stdio_server_without_logger(
        self, mock_lifespan, mock_create_app, mock_create_mcp_app
    ):
        """Test start_stdio_server without logger."""
        # Setup mocks
        mock_app = MagicMock()
        mock_mcp = AsyncMock()
        mock_create_app.return_value = mock_app
        mock_create_mcp_app.return_value = mock_mcp
        mock_lifespan.return_value.__aenter__ = AsyncMock()
        mock_lifespan.return_value.__aexit__ = AsyncMock()

        # Create manager without logger and start STDIO server
        manager = UnifiedServerManager()
        await manager.start_stdio_server()

        # Verify MCP server start
        mock_mcp.run_async.assert_called_once_with(transport="stdio")

    @pytest.mark.asyncio
    async def test_shutdown_with_logger(self):
        """Test shutdown with logger."""
        mock_logger = MagicMock()
        manager = UnifiedServerManager(logger=mock_logger)

        await manager.shutdown()

        mock_logger.info.assert_called_once_with("Shutting down server")

    @pytest.mark.asyncio
    async def test_shutdown_without_logger(self):
        """Test shutdown without logger."""
        manager = UnifiedServerManager()

        # Should not raise any exceptions
        await manager.shutdown()


class TestUnifiedServerManagerIntegration:
    """Integration tests for UnifiedServerManager."""

    @pytest.mark.asyncio
    @patch("stringdb_link.server_manager.uvicorn.Server")
    async def test_uvicorn_config_creation(self, mock_server_class):
        """Test that uvicorn.Config is created with correct parameters."""
        mock_server = AsyncMock()
        mock_server_class.return_value = mock_server

        manager = UnifiedServerManager()
        await manager.start_http_only_server(host="example.com", port=3000, reload=True)

        # Verify Config instantiation
        assert mock_server_class.called
        config = mock_server_class.call_args[0][0]
        assert isinstance(config, uvicorn.Config)
        assert config.host == "example.com"
        assert config.port == 3000
        assert config.reload is True

    @pytest.mark.asyncio
    @patch("stringdb_link.server_manager.uvicorn.Server")
    @patch("stringdb_link.server_manager.settings")
    @patch("stringdb_link.server_manager.app")
    @patch("stringdb_link.server_manager.mcp_app")
    async def test_unified_server_app_mounting(
        self, mock_mcp_app, mock_app, mock_settings, mock_server_class
    ):
        """Test that MCP app is properly mounted in unified mode."""
        mock_settings.mcp_path = "/custom-mcp"
        mock_mcp_http_app = MagicMock()
        mock_mcp_app.http_app.return_value = mock_mcp_http_app
        mock_server = AsyncMock()
        mock_server_class.return_value = mock_server

        manager = UnifiedServerManager()
        await manager.start_unified_server()

        # Verify the mount call (stateless transport pattern: path baked, mount at root)
        mock_mcp_app.http_app.assert_called_once_with(
            path="/custom-mcp",
            stateless_http=True,
            json_response=True,
            host_origin_protection=True,
            allowed_hosts=mock_settings.allowed_hosts,
            allowed_origins=mock_settings.allowed_origins,
        )
        mock_app.mount.assert_called_once_with("/", mock_mcp_http_app)


class TestUnifiedServerManagerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    @patch("stringdb_link.server_manager.uvicorn.Server")
    async def test_server_serve_exception(self, mock_server_class):
        """Test handling of exception during server.serve()."""
        mock_server = AsyncMock()
        mock_server.serve.side_effect = Exception("Server failed to start")
        mock_server_class.return_value = mock_server

        manager = UnifiedServerManager()

        with pytest.raises(Exception, match="Server failed to start"):
            await manager.start_http_only_server()

    @pytest.mark.asyncio
    @patch("stringdb_link.app.create_mcp_app")
    @patch("stringdb_link.app.create_app")
    @patch("stringdb_link.app.lifespan")
    async def test_stdio_server_calls_mcp_run_async(
        self, mock_lifespan, mock_create_app, mock_create_mcp_app
    ):
        """Test that MCP server run_async is called with correct transport."""
        # Setup mocks
        mock_app = MagicMock()
        mock_mcp = AsyncMock()
        mock_create_app.return_value = mock_app
        mock_create_mcp_app.return_value = mock_mcp
        mock_mcp.run_async = AsyncMock()

        # Set up the async context manager correctly
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock()
        async_context.__aexit__ = AsyncMock()
        mock_lifespan.return_value = async_context

        manager = UnifiedServerManager()

        # Should complete without exception
        await manager.start_stdio_server()

        # Verify the MCP server was called with correct transport
        mock_mcp.run_async.assert_called_once_with(transport="stdio")

    @pytest.mark.asyncio
    @patch("stringdb_link.server_manager.log_server_startup")
    @patch("stringdb_link.server_manager.uvicorn.Server")
    async def test_log_startup_exception(self, mock_server_class, mock_log_startup):
        """Test handling of exception during log_server_startup."""
        mock_log_startup.side_effect = Exception("Logging failed")
        mock_server = AsyncMock()
        mock_server_class.return_value = mock_server
        mock_logger = MagicMock()

        manager = UnifiedServerManager(logger=mock_logger)

        with pytest.raises(Exception, match="Logging failed"):
            await manager.start_http_only_server()

    def test_manager_state_persistence(self):
        """Test that manager maintains state across method calls."""
        mock_logger = MagicMock()
        manager = UnifiedServerManager(logger=mock_logger)

        # Logger should persist
        assert manager.logger == mock_logger

        # Create new manager without logger
        manager2 = UnifiedServerManager()
        assert manager2.logger is None
        assert manager.logger == mock_logger  # Original should be unchanged
