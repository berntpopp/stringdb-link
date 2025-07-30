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


@router.post("/enrichment/functional", response_model=EnrichmentTermListResponse)
async def get_functional_enrichment(
    request: EnrichmentRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> EnrichmentTermListResponse:
    """Perform functional enrichment analysis."""
    try:
        logger.info("Performing functional enrichment analysis", identifiers=request.identifiers)

        terms = await service.get_functional_enrichment(request)

        return EnrichmentTermListResponse(terms=terms, total_count=len(terms))

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
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {e.message}",
        ) from e

    except Exception as e:
        logger.exception(
            "Unexpected error during functional enrichment",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during functional enrichment",
        ) from e


@router.post("/enrichment/ppi", response_model=PPIEnrichmentResult)
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
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {e.message}",
        ) from e

    except Exception as e:
        logger.exception(
            "Unexpected error during PPI enrichment",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during PPI enrichment",
        ) from e
