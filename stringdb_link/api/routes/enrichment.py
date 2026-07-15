"""Enrichment analysis endpoints for StringDB-Link."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from stringdb_link.exceptions import StringDBServiceError, ValidationError
from stringdb_link.models.requests import EnrichmentRequest, PPIEnrichmentRequest
from stringdb_link.models.responses import (
    EnrichmentTermListResponse,
    PPIEnrichmentResult,
)
from stringdb_link.services.stringdb_service import StringDBService

from .dependencies import LoggerDep, StringDBServiceDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

router = APIRouter()


@router.post(
    "/enrichment/functional",
    response_model=EnrichmentTermListResponse,
    operation_id="compute_functional_enrichment",
    tags=["enrichment"],
)
async def get_functional_enrichment(
    request: EnrichmentRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> EnrichmentTermListResponse:
    """Perform functional enrichment analysis."""
    try:
        logger.debug(
            "Received functional enrichment request",
            identifiers=request.identifiers,
            species=request.species,
            species_type=type(request.species).__name__,
        )
        logger.info("Performing functional enrichment analysis", identifiers=request.identifiers)

        # Service already returns the wrapped response.
        return await service.get_functional_enrichment(request)

    except StringDBServiceError as e:
        logger.exception(
            "Service error during functional enrichment",
            error=str(e),
            operation=e.operation,
        )
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=f"Service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during functional enrichment",
            error=str(e),
            field=e.field,
            value=e.value,
        )
        # Emit the FastAPI validation-list shape when the offending parameter is
        # known, so the error envelope can name it (e.g. background_string_identifiers)
        # without echoing any upstream prose. The fixed "msg" is never surfaced.
        detail: object = (
            [{"loc": ["body", e.field], "msg": "invalid value"}]
            if e.field
            else f"Validation error: {e.message}"
        )
        raise HTTPException(status_code=400, detail=detail) from e

    except Exception as e:
        logger.exception(
            "Unexpected error during functional enrichment",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during functional enrichment",
        ) from e


@router.post(
    "/enrichment/ppi",
    response_model=PPIEnrichmentResult,
    operation_id="compute_ppi_enrichment",
    tags=["enrichment"],
)
async def get_ppi_enrichment(
    request: PPIEnrichmentRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> PPIEnrichmentResult:
    """Perform protein-protein interaction enrichment analysis."""
    try:
        logger.info("Performing PPI enrichment analysis", identifiers=request.identifiers)

        return await service.get_ppi_enrichment(request)

    except StringDBServiceError as e:
        logger.exception(
            "Service error during PPI enrichment",
            error=str(e),
            operation=e.operation,
        )
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=f"Service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during PPI enrichment",
            error=str(e),
            field=e.field,
            value=e.value,
        )
        # Emit the FastAPI validation-list shape when the offending parameter is
        # known, so the error envelope can name it (e.g. background_string_identifiers)
        # without echoing any upstream prose. The fixed "msg" is never surfaced.
        detail: object = (
            [{"loc": ["body", e.field], "msg": "invalid value"}]
            if e.field
            else f"Validation error: {e.message}"
        )
        raise HTTPException(status_code=400, detail=detail) from e

    except Exception as e:
        logger.exception(
            "Unexpected error during PPI enrichment",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during PPI enrichment",
        ) from e
