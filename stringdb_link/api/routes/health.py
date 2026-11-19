"""Health check endpoints for StringDB-Link."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter

from stringdb_link import __version__
from stringdb_link.config import settings
from stringdb_link.models.responses import HealthResponse

from .dependencies import LoggerDep, StringDBClientDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from stringdb_link.api.client import StringDBClient

router = APIRouter(prefix="/api", tags=["health"])

# Track server start time for uptime calculation
_start_time = time.time()

# The container healthcheck polls /api/health every ~20 s; probing STRING on each
# poll flooded the log and turned upstream 5xx into ASGI 500s (#127). Cache it.
UPSTREAM_PROBE_TTL_SECONDS = 300.0
_upstream_probe: tuple[float, str] | None = None  # (checked_at monotonic, status)


@router.get("/health", response_model=HealthResponse)
async def health_check(
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> HealthResponse:
    """Health check for the StringDB-Link service."""
    global _upstream_probe
    now = time.monotonic()
    if _upstream_probe is None or now - _upstream_probe[0] >= UPSTREAM_PROBE_TTL_SECONDS:
        error_type = None
        try:
            await client.get_version()
            stringdb_status = "available"
        except Exception as e:  # any upstream failure degrades, never raises
            stringdb_status = "unavailable"
            error_type = type(e).__name__
        previous = _upstream_probe[1] if _upstream_probe else None
        _upstream_probe = (now, stringdb_status)
        if stringdb_status != previous:  # log on state change only
            if stringdb_status == "available":
                logger.info("StringDB API reachable")
            else:
                logger.warning("StringDB API health check failed", error_type=error_type)
    stringdb_status = _upstream_probe[1]
    overall_status = "healthy" if stringdb_status == "available" else "degraded"

    uptime = time.time() - _start_time
    cache_status = "enabled" if settings.cache_enabled else "disabled"

    logger.debug(
        "Health check completed",
        overall_status=overall_status,
        stringdb_status=stringdb_status,
    )

    return HealthResponse(
        status=overall_status,
        version=__version__,
        transport="streamable-http-stateless",
        stringdb_api=stringdb_status,
        cache=cache_status,
        uptime_seconds=uptime,
    )


@router.get("/version")
async def version_info() -> dict[str, Any]:
    """Get version information."""
    return {
        "version": __version__,
        "api_version": "v1",
        "stringdb_api": settings.stringdb_base_url,
    }
