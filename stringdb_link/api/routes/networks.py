"""Network interaction endpoints for StringDB-Link.

This module provides endpoints for retrieving protein-protein interaction
networks and interaction partners.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from fastapi import APIRouter, HTTPException, Query

from stringdb_link.exceptions import StringDBServiceError, ValidationError
from stringdb_link.models.requests import InteractionPartnersRequest, LinkRequest, NetworkRequest
from stringdb_link.models.responses import (
    InteractionPartnerListResponse,
    LinkInfo,
    NetworkInteractionListResponse,
)
from stringdb_link.models.stringdb import NetworkType

from .dependencies import LoggerDep, StringDBServiceDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from stringdb_link.services.stringdb_service import StringDBService

router = APIRouter()


@router.post(
    "/networks/interactions",
    response_model=NetworkInteractionListResponse,
    operation_id="search_protein_interactions",
    tags=["network"],
)
async def get_network_interactions(
    request: NetworkRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> NetworkInteractionListResponse:
    """Get protein-protein interaction network.

    Retrieves the protein-protein interaction network for the given proteins.
    If only one protein is provided and add_nodes is 0, additional nodes will
    be automatically added to show the interaction neighborhood.

    Args:
        request: Network interaction request
        service: StringDB service instance
        logger: Logger instance

    Returns:
        List of protein-protein interactions

    Raises:
        HTTPException: If the request fails
    """
    try:
        logger.info(
            "Getting network interactions",
            identifiers=request.identifiers,
            species=request.species,
            required_score=request.required_score,
            network_type=request.network_type,
            add_nodes=request.add_nodes,
        )

        # Call StringDB service (already returns the wrapped response)
        response = await service.get_network_interactions(request)

        logger.info(
            "Successfully retrieved network interactions",
            input_count=len(request.identifiers),
            interaction_count=response.total_count,
        )

        return response

    except StringDBServiceError as e:
        logger.exception(
            "StringDB service error during network interaction retrieval",
            error=str(e),
            status_code=e.status_code,
        )
        raise HTTPException(
            status_code=e.status_code or 502,
            detail=f"StringDB service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during network interaction retrieval",
            error=str(e),
        )
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {e.message}",
        ) from e

    except Exception as e:
        logger.exception(
            "Unexpected error during network interaction retrieval",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during network interaction retrieval",
        ) from e


@router.post(
    "/networks/partners",
    response_model=InteractionPartnerListResponse,
    operation_id="get_interaction_partners",
    tags=["network"],
)
async def get_interaction_partners(
    request: InteractionPartnersRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> InteractionPartnerListResponse:
    """Get interaction partners for proteins.

    Retrieves all interaction partners for the given proteins, not just
    interactions between the input proteins. Useful for finding all
    proteins that interact with your proteins of interest.

    Args:
        request: Interaction partners request
        client: StringDB HTTP client
        logger: Logger instance

    Returns:
        List of interaction partners

    Raises:
        HTTPException: If the request fails
    """
    try:
        logger.info(
            "Getting interaction partners",
            identifiers=request.identifiers,
            species=request.species,
            limit=request.limit,
            required_score=request.required_score,
            network_type=request.network_type,
        )

        # The service already builds the response with an honest, limit-invariant
        # total_count and the truncated flag; return it directly rather than
        # rebuilding it with total_count=len(partners) (which tracked the page size).
        partners_response = await service.get_interaction_partners(request)

        logger.info(
            "Successfully retrieved interaction partners",
            input_count=len(request.identifiers),
            partner_count=len(partners_response.partners),
            total_count=partners_response.total_count,
        )

        return partners_response

    except StringDBServiceError as e:
        logger.exception(
            "StringDB service error during interaction partner retrieval",
            error=str(e),
            status_code=e.status_code,
        )
        raise HTTPException(
            status_code=e.status_code or 502,
            detail=f"StringDB service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during interaction partner retrieval",
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
            "Unexpected error during interaction partner retrieval",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during interaction partner retrieval",
        ) from e


@router.get("/networks/interactions/{identifier}")
async def get_single_protein_network(
    identifier: str,
    species: int = Query(None, description="NCBI taxon identifier"),
    required_score: float = Query(0.4, description="Minimum confidence score (0.0-1.0)"),
    add_nodes: int = Query(10, description="Number of additional nodes to add"),
    network_type: str = Query("functional", description="Network type (functional or physical)"),
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> NetworkInteractionListResponse:
    """Get interaction network for a single protein.

    Convenience endpoint for getting the interaction network of a single
    protein without requiring a JSON request body.

    Args:
        identifier: Protein identifier
        species: NCBI taxon identifier
        required_score: Minimum confidence score (0.0-1.0)
        add_nodes: Number of additional nodes to add
        network_type: Network type (functional or physical)
        client: StringDB HTTP client
        logger: Logger instance

    Returns:
        List of protein-protein interactions

    Raises:
        HTTPException: If the request fails
    """
    try:
        # Create request object
        request = NetworkRequest(
            identifiers=[identifier],
            species=species,
            required_score=required_score,
            network_type=NetworkType(network_type),
            add_nodes=add_nodes,
            show_query_node_labels=False,
        )

        # Use the main endpoint logic
        return await get_network_interactions(request, service, logger)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error during single protein network retrieval",
            identifier=identifier,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during network retrieval",
        ) from e


@router.get("/networks/partners/{identifier}")
async def get_single_protein_partners(
    identifier: str,
    species: int = Query(None, description="NCBI taxon identifier"),
    limit: int = Query(10, description="Maximum number of partners"),
    required_score: float = Query(0.4, description="Minimum confidence score (0.0-1.0)"),
    network_type: str = Query("functional", description="Network type (functional or physical)"),
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> InteractionPartnerListResponse:
    """Get interaction partners for a single protein.

    Convenience endpoint for getting interaction partners of a single
    protein without requiring a JSON request body.

    Args:
        identifier: Protein identifier
        species: NCBI taxon identifier
        limit: Maximum number of partners
        required_score: Minimum confidence score (0.0-1.0)
        network_type: Network type (functional or physical)
        client: StringDB HTTP client
        logger: Logger instance

    Returns:
        List of interaction partners

    Raises:
        HTTPException: If the request fails
    """
    try:
        # Create request object
        request = InteractionPartnersRequest(
            identifiers=[identifier],
            species=species,
            limit=limit,
            required_score=required_score,
            network_type=NetworkType(network_type),
        )

        # Use the main endpoint logic
        return await get_interaction_partners(request, service, logger)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error during single protein partner retrieval",
            identifier=identifier,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during partner retrieval",
        ) from e


@router.post(
    "/networks/link",
    response_model=LinkInfo,
    operation_id="get_network_link",
    tags=["network"],
)
async def get_network_link(
    request: LinkRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
    output_format: Literal["json"] = Query(
        "json",
        description=(
            "Response format. Only 'json' is supported: it returns the shareable "
            "STRING URL inside a structured envelope. Any other value is rejected."
        ),
        examples=["json"],
    ),
) -> LinkInfo:
    """Get shareable link to STRING webpage for the network.

    This endpoint generates a shareable URL that leads to the STRING database
    website showing the protein interaction network for the specified proteins.
    The link includes all visualization parameters and can be shared with others.

    The generated link allows users to:
    - View the network interactively on the STRING website
    - Access additional features like network customization
    - Share the exact network view with collaborators
    """
    try:
        logger.info(
            "Generating network link",
            identifiers=request.identifiers,
            species=request.species,
        )

        # ``output_format`` is constrained to "json" at the schema boundary, so the
        # only reachable path returns the structured LinkInfo envelope. The former
        # plain-text branch produced an empty MCP structured result (silent-empty)
        # and has been removed.
        return await service.get_network_link(request)

    except StringDBServiceError as e:
        # Log the error type only. The raw identifiers and str(e) can embed the
        # caller-supplied (possibly patient-derived) gene list; the sink-level
        # redaction processor is the backstop for any field that slips through.
        logger.exception(
            "StringDB service error during link generation",
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.exception(
            "Unexpected error during link generation",
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}",
        ) from e
