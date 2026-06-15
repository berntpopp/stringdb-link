"""Main FastAPI application with FastMCP integration.

This module creates the FastAPI application with all routes, middleware,
and MCP integration configured.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, RouteMap

from .api.routes import (
    annotations,
    enrichment,
    health,
    homology,
    identifiers,
    images,
    networks,
)
from .config import settings
from .logging_config import configure_logging, log_server_startup

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger = configure_logging()
    log_server_startup(logger, "startup", settings.host, settings.port)

    yield

    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="StringDB-Link",
        description=(
            "High-performance unified API server for STRING protein-protein interaction database"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Include routers
    app.include_router(identifiers.router, prefix="/api", tags=["identifiers"])
    app.include_router(networks.router, prefix="/api", tags=["networks"])
    app.include_router(enrichment.router, prefix="/api", tags=["enrichment"])
    app.include_router(annotations.router, prefix="/api", tags=["annotations"])
    app.include_router(homology.router, prefix="/api", tags=["homology"])
    app.include_router(images.router, prefix="/api", tags=["images"])
    app.include_router(health.router)  # Health router already has /api/health prefix

    # Root endpoint
    @app.get("/")
    async def root() -> dict[str, Any]:
        """Root endpoint with service information."""
        return {
            "name": "StringDB-Link",
            "version": "1.0.0",
            "description": (
                "High-performance unified API server "
                "for STRING protein-protein interaction database"
            ),
            "docs": "/docs",
            "health": "/api/health",
            "mcp_endpoint": settings.mcp_path,
            "stringdb_api": settings.stringdb_base_url,
        }

    return app


def create_mcp_app() -> FastMCP:
    """Create FastMCP server from FastAPI app.

    Tool names are taken verbatim from each route's ``operation_id`` (set in the
    route decorators), so they conform to the GeneFoundry Tool-Naming Standard v1
    (``verb_noun`` snake_case, canonical verb, unprefixed). The gateway adds the
    ``stringdb`` namespace at mount time (tools surface as ``stringdb_<tool>``).
    The CI guard ``tests/unit/test_tool_names.py`` enforces this on every route.
    """
    app = create_app()

    # Route mappings for MCP tools. Everything not excluded becomes a tool, named
    # after its ``operation_id``.
    mcp_route_maps = [
        # Exclude health and monitoring endpoints.
        RouteMap(pattern=r"^/api/health.*$", mcp_type=MCPType.EXCLUDE),
        # Exclude root and docs endpoints.
        RouteMap(pattern=r"^/$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/docs$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/openapi.json$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/redoc$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/api/version$", mcp_type=MCPType.EXCLUDE),
        # Exclude single-identifier GET convenience routes: they duplicate the
        # list-based POST tools and are not part of the curated MCP surface.
        RouteMap(pattern=r"^/api/identifiers/resolve/[^/]+$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/api/networks/interactions/[^/]+$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/api/networks/partners/[^/]+$", mcp_type=MCPType.EXCLUDE),
        # Exclude raw bulk-download routes: non-canonical verb, poor MCP
        # ergonomics, and redundant with the JSON tools.
        RouteMap(pattern=r"^/api/homology/scores/download$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/api/homology/best-hits/download$", mcp_type=MCPType.EXCLUDE),
    ]

    # Create FastMCP instance.
    return FastMCP.from_fastapi(
        app=app,
        name=settings.mcp_server_name,
        route_maps=mcp_route_maps,
    )


# Create application instances
app = create_app()

# Create MCP app conditionally to avoid schema generation issues
try:
    mcp_app = create_mcp_app()
except Exception as e:
    import warnings

    warnings.warn(f"MCP app creation failed: {e}", UserWarning)
    mcp_app = None
