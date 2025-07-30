"""Homology analysis endpoints for StringDB-Link API.

This module provides endpoints for protein homology analysis including
similarity scores and best hits between species.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from stringdb_link.exceptions import StringDBAPIError
from stringdb_link.models.requests import HomologyBestRequest, HomologyRequest
from stringdb_link.models.responses import HomologyScoreListResponse
from stringdb_link.models.stringdb import OutputFormat
from stringdb_link.services.stringdb_service import StringDBService

from .dependencies import StringDBServiceDep

if TYPE_CHECKING:
    from fastapi import Response

router = APIRouter(prefix="/homology", tags=["homology"])


@router.post(
    "/scores",
    response_model=HomologyScoreListResponse,
    summary="Get homology scores",
    description=(
        "Retrieve homology scores for proteins showing sequence similarity "
        "to proteins from other species. This endpoint helps identify "
        "evolutionarily related proteins across different organisms."
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
    output_format: OutputFormat = Query(
        OutputFormat.JSON,
        description="Output format for the response",
    ),
) -> Response:
    """Get protein homology scores.

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
            output_format=output_format,
        )

        if output_format == OutputFormat.JSON:
            return HomologyScoreListResponse(
                data=result,
                count=len(result),
                status="success",
            )
        # Return raw text for non-JSON formats
        return PlainTextResponse(
            content=result,
            media_type="text/plain",
        )

    except StringDBAPIError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}",
        ) from e


@router.post(
    "/best-hits",
    response_model=HomologyScoreListResponse,
    summary="Get best homology hits",
    description=(
        "Get the best homology hits between proteins from different species. "
        "This endpoint is useful for finding the closest evolutionary relatives "
        "of proteins across species boundaries."
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
    output_format: OutputFormat = Query(
        OutputFormat.JSON,
        description="Output format for the response",
    ),
) -> Response:
    """Get best homology hits between species.

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
            output_format=output_format,
        )

        if output_format == OutputFormat.JSON:
            return HomologyScoreListResponse(
                data=result,
                count=len(result),
                status="success",
            )
        # Return raw text for non-JSON formats
        return PlainTextResponse(
            content=result,
            media_type="text/plain",
        )

    except StringDBAPIError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}",
        ) from e
