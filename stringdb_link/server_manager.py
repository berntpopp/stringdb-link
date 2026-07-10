"""Unified server management for different transport modes.

This module manages the server lifecycle for HTTP, MCP, and unified modes,
providing a consistent interface for starting and stopping the server.
"""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING, Any

# FastMCP >=3.4.3 enables a global localhost-only default that rejects the public
# proxy Host before application allowlists can apply. Disable that implicit guard;
# create_unified_app installs explicit outer and native guards with the same exact
# configured lists. The hasattr keeps imports safe on older transitional installs.
import fastmcp
import uvicorn
from fastapi import FastAPI

from .app import app, create_app, create_mcp_app, mcp_app
from .config import settings
from .logging_config import log_server_startup

if hasattr(fastmcp.settings, "http_host_origin_protection"):
    fastmcp.settings.http_host_origin_protection = False

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from structlog.typing import FilteringBoundLogger


def create_unified_app(
    fastapi_app: FastAPI | None = None,
    mcp: Any | None = None,
) -> FastAPI:
    """Create the shared FastAPI host with outer and native strict guards."""
    from fastmcp.server.http import HostOriginGuardMiddleware

    fastapi_app = fastapi_app or create_app()
    mcp = mcp or create_mcp_app()
    fastapi_app.add_middleware(
        HostOriginGuardMiddleware,
        allowed_hosts=settings.allowed_hosts,
        allowed_origins=settings.allowed_origins,
        mode="strict",
    )
    mcp_http_app = mcp.http_app(
        path=settings.mcp_path,
        stateless_http=True,
        json_response=True,
        host_origin_protection=True,
        allowed_hosts=settings.allowed_hosts,
        allowed_origins=settings.allowed_origins,
    )

    original_lifespan = fastapi_app.router.lifespan_context

    @asynccontextmanager
    async def combined_lifespan(active_app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(original_lifespan(active_app))
            await stack.enter_async_context(mcp_http_app.router.lifespan_context(active_app))
            yield

    fastapi_app.router.lifespan_context = combined_lifespan
    fastapi_app.mount("/", mcp_http_app)
    return fastapi_app


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

        unified_app = create_unified_app(app, mcp_app)

        config = uvicorn.Config(
            app=unified_app,
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
