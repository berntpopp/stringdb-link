"""Identifier resolution endpoints for StringDB-Link.

This module provides endpoints for mapping protein identifiers
to STRING database identifiers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from stringdb_link.exceptions import StringDBServiceError, ValidationError
from stringdb_link.models.requests import IdentifierRequest
from stringdb_link.models.responses import StringIdMapping, StringIdMappingListResponse

from .dependencies import LoggerDep, StringDBServiceDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from stringdb_link.services.stringdb_service import StringDBService

router = APIRouter()


@router.post(
    "/identifiers/resolve",
    response_model=StringIdMappingListResponse,
    summary="Resolve protein identifiers to STRING IDs",
    description="""
    Maps common protein names, gene symbols, UniProt IDs, and other identifiers
    to STRING database identifiers. The STRING database uses an intelligent
    mapping system to find the best matching identifier for each input.

    **Supported identifier types:**
    - Gene symbols (e.g., p53, BRCA1, CDK2)
    - UniProt IDs (e.g., P04637, P38398)
    - Ensembl IDs (e.g., ENSP00000269305)
    - RefSeq IDs (e.g., NP_000537)
    - Common protein names

    **Species support:**
    - Humans (9606), Mouse (10090), E. coli (511145), and 2000+ other species
    - If no species is specified, STRING attempts cross-species mapping
    """,
    operation_id="resolve_protein_identifiers",
    responses={
        200: {
            "description": "Identifiers resolved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "mappings": [
                            {
                                "query_index": 0,
                                "query_item": "p53",
                                "string_id": "9606.ENSP00000269305",
                                "ncbi_taxon_id": 9606,
                                "taxon_name": "Homo sapiens",
                                "preferred_name": "TP53",
                                "annotation": "tumor protein p53",
                            },
                            {
                                "query_index": 1,
                                "query_item": "BRCA1",
                                "string_id": "9606.ENSP00000350283",
                                "ncbi_taxon_id": 9606,
                                "taxon_name": "Homo sapiens",
                                "preferred_name": "BRCA1",
                                "annotation": "BRCA1 DNA repair associated",
                            },
                        ],
                        "total_count": 2,
                    }
                }
            },
        },
        400: {
            "description": "Invalid request parameters",
            "content": {
                "application/json": {
                    "example": {"detail": "Validation error: At least one identifier is required"}
                }
            },
        },
        404: {
            "description": "No identifiers could be resolved",
            "content": {
                "application/json": {
                    "example": {
                        "mappings": [],
                        "total_count": 0,
                        "message": "No valid identifiers found for the given input",
                    }
                }
            },
        },
        502: {
            "description": "STRING API communication error",
            "content": {
                "application/json": {
                    "example": {"detail": "Service error: Failed to resolve identifiers"}
                }
            },
        },
    },
)
async def resolve_identifiers(
    request: IdentifierRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> StringIdMappingListResponse:
    """Resolve protein identifiers to STRING database identifiers."""
    try:
        logger.debug(
            "Received identifier resolution request",
            identifiers=request.identifiers,
            species=request.species,
            species_type=type(request.species).__name__,
            echo_query=request.echo_query,
        )
        return await service.resolve_identifiers(request)

    except StringDBServiceError as e:
        logger.exception(
            "Service error during identifier resolution",
            error=str(e),
            operation=e.operation,
        )
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=f"Service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during identifier resolution",
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
            "Unexpected error during identifier resolution",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during identifier resolution",
        ) from e


@router.get("/identifiers/resolve/{identifier}")
async def resolve_single_identifier(
    identifier: str,
    species: int | None = None,
    echo_query: bool = False,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> StringIdMapping:
    """Resolve a single protein identifier to STRING database identifier.

    Convenience endpoint for resolving a single identifier without
    requiring a JSON request body.

    Args:
        identifier: Protein identifier to resolve
        species: NCBI taxon identifier (optional)
        echo_query: Include input identifier in output
        service: StringDB service instance
        logger: Logger instance

    Returns:
        Single identifier mapping

    Raises:
        HTTPException: If the identifier cannot be resolved
    """
    try:
        # Create request object
        request = IdentifierRequest(
            identifiers=[identifier],
            species=species,
            echo_query=echo_query,
        )

        # Resolve using the service
        result = await service.resolve_identifiers(request)

        if not result.mappings:
            raise HTTPException(
                status_code=404,
                detail=f"Identifier '{identifier}' could not be resolved",
            )

        # Return the first (and only) mapping
        return result.mappings[0]

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except StringDBServiceError as e:
        logger.exception(
            "Service error during single identifier resolution",
            identifier=identifier,
            error=str(e),
            operation=e.operation,
        )
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=f"Service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during single identifier resolution",
            identifier=identifier,
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
            "Unexpected error during single identifier resolution",
            identifier=identifier,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during identifier resolution",
        ) from e
