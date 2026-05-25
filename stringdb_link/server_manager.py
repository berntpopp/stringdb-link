"""Unified server management for different transport modes.

This module manages the server lifecycle for HTTP, MCP, and unified modes,
providing a consistent interface for starting and stopping the server.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI

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

        if mcp_app is None:
            msg = "MCP app is not available"
            raise RuntimeError(msg)

        # FastMCP 3 exposes hosted MCP as an ASGI app. Use path="/" so the
        # final endpoint is settings.mcp_path rather than a double-prefixed path.
        mcp_http_app = mcp_app.http_app(path="/")

        original_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def combined_lifespan(fastapi_app: FastAPI):
            async with mcp_http_app.lifespan(mcp_http_app), original_lifespan(fastapi_app):
                yield

        app.router.lifespan_context = combined_lifespan
        app.mount(settings.mcp_path, mcp_http_app)

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
        """Start STDIO MCP server (following litvar-link pattern)."""
        if self.logger:
            self.logger.info("Starting MCP STDIO server")

        # Create FastAPI app (for MCP introspection)
        from .app import create_app, create_mcp_app, lifespan

        app = create_app()

        # Use lifespan context manager for consistency with HTTP mode
        if self.logger:
            self.logger.info("Initializing app state using lifespan context...")

        async with lifespan(app):
            # Create MCP server within the lifespan context
            mcp = create_mcp_app()

            if self.logger:
                self.logger.info("STDIO MCP server ready")

            # Run MCP server in STDIO mode
            await mcp.run_async(transport="stdio")

    async def shutdown(self) -> None:
        """Shutdown the server gracefully."""
        if self.logger:
            self.logger.info("Shutting down server")
        # Additional cleanup logic can be added here if needed
