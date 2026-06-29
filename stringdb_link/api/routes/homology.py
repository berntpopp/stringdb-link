"""Homology analysis endpoints for StringDB-Link API.

This module provides endpoints for protein homology analysis including
similarity scores and best hits between species.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from stringdb_link.exceptions import StringDBServiceError, ValidationError
from stringdb_link.models.requests import HomologyBestRequest, HomologyRequest
from stringdb_link.models.responses import HomologyScoreListResponse
from stringdb_link.models.stringdb import OutputFormat
from stringdb_link.services.stringdb_service import StringDBService

from .dependencies import LoggerDep, StringDBServiceDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

router = APIRouter(prefix="/homology", tags=["homology"])


@router.post(
    "/scores",
    response_model=HomologyScoreListResponse,
    operation_id="get_protein_homology_scores",
    tags=["homology"],
    summary="Get homology scores (JSON)",
    description=(
        "Retrieve homology scores for proteins showing sequence similarity "
        "to proteins from other species. This endpoint helps identify "
        "evolutionarily related proteins across different organisms. "
        "Returns structured JSON data."
    ),
    responses={
        200: {
            "description": "Homology scores retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "stringId_A": "9606.ENSP00000000233",
                                "stringId_B": "10090.ENSMUSP00000000001",
                                "species_A": 9606,
                                "species_B": 10090,
                                "bitscore": 850,
                                "evalue": 0.0,
                            }
                        ],
                        "count": 1,
                        "status": "success",
                    }
                }
            },
        },
        400: {"description": "Invalid request parameters"},
        422: {"description": "Request validation error"},
        500: {"description": "StringDB API error"},
    },
)
async def get_homology_scores(
    request: HomologyRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> HomologyScoreListResponse:
    """Get protein homology scores (JSON format).

    This endpoint retrieves homology scores showing sequence similarity
    between the input proteins and proteins from other species. The scores
    help identify evolutionarily related proteins across different organisms.

    The response includes:
    - STRING IDs for both proteins
    - Species information
    - Bit score (higher = better match)
    - E-value (lower = better match)
    """
    try:
        result = await service.get_homology_scores(
            identifiers=request.identifiers,
            species=request.species,
            output_format=OutputFormat.JSON,
        )

        return HomologyScoreListResponse(
            data=result,
            count=len(result),
            status="success",
        )

    except StringDBServiceError as e:
        logger.exception(
            "Service error during homology score retrieval",
            error=str(e),
            operation=e.operation,
        )
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=f"Service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during homology score retrieval",
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
            "Unexpected error during homology score retrieval",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during homology score retrieval",
        ) from e


@router.post(
    "/scores/download",
    summary="Download homology scores",
    description=(
        "Download homology scores in various formats (TSV, XML, PSI-MI). "
        "This endpoint returns raw text data suitable for download or "
        "processing by external tools."
    ),
    responses={
        200: {
            "description": "Homology scores in specified format",
            "content": {
                "text/plain": {
                    "example": (
                        "stringId_A\tstringId_B\tbitscore\tevalue\nprotein1\tprotein2\t850\t0.0"
                    )
                }
            },
        },
        400: {"description": "Invalid request parameters"},
        422: {"description": "Request validation error"},
        500: {"description": "StringDB API error"},
    },
)
async def download_homology_scores(
    request: HomologyRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
    output_format: OutputFormat = Query(
        OutputFormat.TSV,
        description="Output format (TSV, XML, PSI-MI)",
    ),
) -> PlainTextResponse:
    """Download protein homology scores in text formats."""
    try:
        result = await service.get_homology_scores(
            identifiers=request.identifiers,
            species=request.species,
            output_format=output_format,
        )

        # Return raw text for download
        return PlainTextResponse(
            content=result,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=homology_scores.{output_format.value}"
            },
        )

    except StringDBServiceError as e:
        logger.exception(
            "Service error during homology score download",
            error=str(e),
            operation=e.operation,
        )
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=f"Service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during homology score download",
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
            "Unexpected error during homology score download",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during homology score download",
        ) from e


@router.post(
    "/best-hits",
    response_model=HomologyScoreListResponse,
    operation_id="get_protein_homology_best_hits",
    tags=["homology"],
    summary="Get best homology hits (JSON)",
    description=(
        "Get the best homology hits between proteins from different species. "
        "This endpoint is useful for finding the closest evolutionary relatives "
        "of proteins across species boundaries. Returns structured JSON data."
    ),
    responses={
        200: {
            "description": "Best homology hits retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "stringId_A": "9606.ENSP00000000233",
                                "stringId_B": "10090.ENSMUSP00000000001",
                                "species_A": 9606,
                                "species_B": 10090,
                                "bitscore": 850,
                                "evalue": 0.0,
                            }
                        ],
                        "count": 1,
                        "status": "success",
                    }
                }
            },
        },
        400: {"description": "Invalid request parameters"},
        422: {"description": "Request validation error"},
        500: {"description": "StringDB API error"},
    },
)
async def get_homology_best_hits(
    request: HomologyBestRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> HomologyScoreListResponse:
    """Get best homology hits between species (JSON format).

    This endpoint retrieves the best homology matches for input proteins
    when compared against proteins from specified target species. It's
    particularly useful for comparative genomics and finding orthologs.

    The response includes the same fields as homology scores but filtered
    to show only the best matches per protein.
    """
    try:
        result = await service.get_homology_best_hits(
            identifiers=request.identifiers,
            species=request.species,
            species_b=request.species_b,
            output_format=OutputFormat.JSON,
        )

        return HomologyScoreListResponse(
            data=result,
            count=len(result),
            status="success",
        )

    except StringDBServiceError as e:
        logger.exception(
            "Service error during homology best hits retrieval",
            error=str(e),
            operation=e.operation,
        )
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=f"Service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during homology best hits retrieval",
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
            "Unexpected error during homology best hits retrieval",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during homology best hits retrieval",
        ) from e


@router.post(
    "/best-hits/download",
    summary="Download best homology hits",
    description=(
        "Download best homology hits in various formats (TSV, XML, PSI-MI). "
        "This endpoint returns raw text data suitable for download or "
        "processing by external tools."
    ),
    responses={
        200: {
            "description": "Best homology hits in specified format",
            "content": {
                "text/plain": {
                    "example": (
                        "stringId_A\tstringId_B\tbitscore\tevalue\nprotein1\tprotein2\t850\t0.0"
                    )
                }
            },
        },
        400: {"description": "Invalid request parameters"},
        422: {"description": "Request validation error"},
        500: {"description": "StringDB API error"},
    },
)
async def download_homology_best_hits(
    request: HomologyBestRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
    output_format: OutputFormat = Query(
        OutputFormat.TSV,
        description="Output format (TSV, XML, PSI-MI)",
    ),
) -> PlainTextResponse:
    """Download best homology hits in text formats."""
    try:
        result = await service.get_homology_best_hits(
            identifiers=request.identifiers,
            species=request.species,
            species_b=request.species_b,
            output_format=output_format,
        )

        # Return raw text for download
        return PlainTextResponse(
            content=result,
            media_type="text/plain",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=homology_best_hits.{output_format.value}"
                )
            },
        )

    except StringDBServiceError as e:
        logger.exception(
            "Service error during homology best hits download",
            error=str(e),
            operation=e.operation,
        )
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=f"Service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during homology best hits download",
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
            "Unexpected error during homology best hits download",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during homology best hits download",
        ) from e
