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
from fastmcp.server.openapi import MCPType, RouteMap

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
            "High-performance unified API server for STRING "
            "protein-protein interaction database"
        ),
        version="0.1.0",
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
            "version": "0.1.0",
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
    """Create FastMCP server from FastAPI app."""
    app = create_app()

    # MCP tool name mappings (following litvar-link pattern)
    mcp_custom_names = {
        "resolve_identifiers": "resolve_protein_identifiers",
        "get_network_interactions": "search_protein_interactions",
        "get_interaction_partners": "get_interaction_partners",
        "get_functional_enrichment": "analyze_functional_enrichment",
        "get_functional_annotation": "get_functional_annotations",
        "get_network_image": "generate_network_visualization",
        "get_enrichment_image": "generate_enrichment_visualization",
        "get_homology_scores": "get_protein_homology_scores",
        "get_homology_best_hits": "get_protein_homology_best_hits",
        "get_network_link": "get_shareable_network_link",
        "get_ppi_enrichment": "analyze_ppi_enrichment",
    }

    # Route mappings for MCP tools (exclude utility endpoints)
    mcp_route_maps = [
        # Exclude health and monitoring endpoints
        RouteMap(pattern=r"^/api/health.*$", mcp_type=MCPType.EXCLUDE),
        # Exclude root and docs endpoints
        RouteMap(pattern=r"^/$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/docs$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/openapi.json$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/redoc$", mcp_type=MCPType.EXCLUDE),
        # Exclude some internal endpoints if needed
        RouteMap(pattern=r"^/api/version$", mcp_type=MCPType.EXCLUDE),
    ]

    # Create FastMCP instance
    return FastMCP.from_fastapi(
        app=app,
        name=settings.mcp_server_name,
        mcp_names=mcp_custom_names,
        route_maps=mcp_route_maps,
    )


# Create application instances
app = create_app()
mcp_app = create_mcp_app()
