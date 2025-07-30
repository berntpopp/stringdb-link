"""Unified server management for different transport modes.

This module manages the server lifecycle for HTTP, MCP, and unified modes,
providing a consistent interface for starting and stopping the server.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import uvicorn

from .app import app, mcp_app
from .config import settings
from .logging_config import log_server_startup

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger


class UnifiedServerManager:
    """Manages unified server with multiple transport protocols."""

    def __init__(self, logger: FilteringBoundLogger | None = None) -> None:
        """Initialize server manager.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger

    async def start_unified_server(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = False,
    ) -> None:
        """Start unified server (HTTP + MCP).

        Args:
            host: Server host
            port: Server port
            reload: Enable auto-reload
        """
        if self.logger:
            log_server_startup(self.logger, "unified", host, port)

        # Add MCP endpoint to the main app
        app.mount(settings.mcp_path, mcp_app.mcp_router)

        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            reload=reload,
            log_config=None,  # Use our custom logging
            access_log=False,  # Disable default access log
        )

        server = uvicorn.Server(config)
        await server.serve()

    async def start_http_only_server(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = False,
    ) -> None:
        """Start HTTP-only server.

        Args:
            host: Server host
            port: Server port
            reload: Enable auto-reload
        """
        if self.logger:
            log_server_startup(self.logger, "http", host, port)

        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            reload=reload,
            log_config=None,  # Use our custom logging
            access_log=False,  # Disable default access log
        )

        server = uvicorn.Server(config)
        await server.serve()

    async def start_stdio_server(self) -> None:
        """Start MCP server in STDIO mode.

        This mode is used for Claude Desktop integration where communication
        happens over stdin/stdout.
        """
        if self.logger:
            self.logger.info("Starting MCP STDIO server")

        # Run the MCP server in STDIO mode
        await mcp_app.run_stdio()

    async def shutdown(self) -> None:
        """Shutdown the server gracefully."""
        if self.logger:
            self.logger.info("Shutting down server")
        # Additional cleanup logic can be added here if needed
