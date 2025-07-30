"""Health check endpoints for StringDB-Link."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fastapi import APIRouter

from stringdb_link.models.responses import HealthResponse

from .dependencies import LoggerDep, StringDBClientDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from stringdb_link.api.client import StringDBClient

router = APIRouter(prefix="/api/health", tags=["health"])

# Track server start time for uptime calculation
_start_time = time.time()


@router.get("/", response_model=HealthResponse)
async def health_check(
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> HealthResponse:
    """Health check for the StringDB-Link service."""
    # Check StringDB API health
    stringdb_status = "healthy"
    try:
        await client.get_version()
    except Exception as e:
        logger.warning("StringDB API health check failed", error=str(e))
        stringdb_status = "degraded"

    uptime = time.time() - _start_time

    logger.info(
        "Health check completed",
        overall_status=stringdb_status,
        stringdb_status=stringdb_status,
    )

    return HealthResponse(
        status=stringdb_status,
        version="0.1.0",
        stringdb_api=stringdb_status,
        cache="enabled",
        uptime_seconds=uptime,
    )
