"""Enrichment analysis endpoints for StringDB-Link."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from stringdb_link.exceptions import StringDBAPIError
from stringdb_link.models.requests import EnrichmentRequest, PPIEnrichmentRequest
from stringdb_link.models.responses import (
    EnrichmentTerm,
    EnrichmentTermListResponse,
    PPIEnrichmentResult,
)

from .dependencies import LoggerDep, StringDBClientDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from stringdb_link.api.client import StringDBClient

router = APIRouter()


@router.post("/enrichment/functional", response_model=EnrichmentTermListResponse)
async def get_functional_enrichment(
    request: EnrichmentRequest,
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> EnrichmentTermListResponse:
    """Perform functional enrichment analysis."""
    try:
        logger.info("Performing functional enrichment analysis", identifiers=request.identifiers)

        raw_terms = await client.get_functional_enrichment(
            identifiers=request.identifiers,
            species=request.species,
            background_string_identifiers=request.background_string_identifiers,
        )

        terms = [EnrichmentTerm(**term) for term in raw_terms]

        return EnrichmentTermListResponse(terms=terms, total_count=len(terms))

    except StringDBAPIError as e:
        raise HTTPException(
            status_code=e.status_code or 502, detail=f"StringDB API error: {e.message}"
        )
    except Exception as e:
        logger.error("Error during functional enrichment", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/enrichment/ppi", response_model=PPIEnrichmentResult)
async def get_ppi_enrichment(
    request: PPIEnrichmentRequest,
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> PPIEnrichmentResult:
    """Perform protein-protein interaction enrichment analysis."""
    try:
        logger.info("Performing PPI enrichment analysis", identifiers=request.identifiers)

        raw_result = await client.get_ppi_enrichment(
            identifiers=request.identifiers,
            species=request.species,
            required_score=request.required_score,
            background_string_identifiers=request.background_string_identifiers,
        )

        return PPIEnrichmentResult(**raw_result)

    except StringDBAPIError as e:
        raise HTTPException(
            status_code=e.status_code or 502, detail=f"StringDB API error: {e.message}"
        )
    except Exception as e:
        logger.error("Error during PPI enrichment", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
