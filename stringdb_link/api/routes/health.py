"""Health check endpoints for StringDB-Link."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import httpx
from fastapi import APIRouter

from stringdb_link.config import settings
from stringdb_link.models.responses import HealthResponse

from .dependencies import LoggerDep, StringDBClientDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from stringdb_link.api.client import StringDBClient

router = APIRouter(prefix="/api", tags=["health"])

# Track server start time for uptime calculation
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> HealthResponse:
    """Health check for the StringDB-Link service."""
    # Check StringDB API health
    stringdb_status = "available"
    overall_status = "healthy"
    try:
        await client.get_version()
    except (TimeoutError, httpx.HTTPError) as e:
        logger.warning("StringDB API health check failed", error=str(e))
        stringdb_status = "unavailable"
        overall_status = "degraded"

    uptime = time.time() - _start_time
    cache_status = "enabled" if settings.cache_enabled else "disabled"

    logger.info(
        "Health check completed",
        overall_status=overall_status,
        stringdb_status=stringdb_status,
    )

    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        stringdb_api=stringdb_status,
        cache=cache_status,
        uptime_seconds=uptime,
    )


@router.get("/version")
async def version_info() -> dict[str, Any]:
    """Get version information."""
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "stringdb_api": settings.stringdb_base_url,
    }
