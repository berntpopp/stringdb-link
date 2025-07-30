"""Network interaction endpoints for StringDB-Link.

This module provides endpoints for retrieving protein-protein interaction
networks and interaction partners.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

if TYPE_CHECKING:
    from fastapi import Response

from stringdb_link.exceptions import StringDBAPIError, ValidationError
from stringdb_link.models.requests import InteractionPartnersRequest, LinkRequest, NetworkRequest
from stringdb_link.models.responses import (
    InteractionPartner,
    InteractionPartnerListResponse,
    LinkInfo,
    NetworkInteraction,
    NetworkInteractionListResponse,
)
from stringdb_link.models.stringdb import OutputFormat

from .dependencies import LoggerDep, StringDBClientDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from stringdb_link.api.client import StringDBClient

router = APIRouter()


@router.post("/networks/interactions", response_model=NetworkInteractionListResponse)
async def get_network_interactions(
    request: NetworkRequest,
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> NetworkInteractionListResponse:
    """Get protein-protein interaction network.

    Retrieves the protein-protein interaction network for the given proteins.
    If only one protein is provided and add_nodes is 0, additional nodes will
    be automatically added to show the interaction neighborhood.

    Args:
        request: Network interaction request
        client: StringDB HTTP client
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

        # Call StringDB API
        raw_interactions = await client.get_network_interactions(
            identifiers=request.identifiers,
            species=request.species,
            required_score=request.required_score,
            network_type=request.network_type.value,
            add_nodes=request.add_nodes,
            show_query_node_labels=request.show_query_node_labels,
        )

        # Convert to response models
        interactions = [NetworkInteraction(**interaction) for interaction in raw_interactions]

        logger.info(
            "Successfully retrieved network interactions",
            input_count=len(request.identifiers),
            interaction_count=len(interactions),
        )

        return NetworkInteractionListResponse(
            interactions=interactions,
            total_count=len(interactions),
        )

    except StringDBAPIError as e:
        logger.exception(
            "StringDB API error during network interaction retrieval",
            error=str(e),
            status_code=e.status_code,
        )
        raise HTTPException(
            status_code=e.status_code or 502,
            detail=f"StringDB API error: {e.message}",
        )

    except ValidationError as e:
        logger.exception(
            "Validation error during network interaction retrieval",
            error=str(e),
            field=e.field,
            value=e.value,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {e.message}",
        )

    except Exception as e:
        logger.error(
            "Unexpected error during network interaction retrieval",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during network interaction retrieval",
        )


@router.post("/networks/partners", response_model=InteractionPartnerListResponse)
async def get_interaction_partners(
    request: InteractionPartnersRequest,
    client: StringDBClient = StringDBClientDep,
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

        # Call StringDB API
        raw_partners = await client.get_interaction_partners(
            identifiers=request.identifiers,
            species=request.species,
            limit=request.limit,
            required_score=request.required_score,
            network_type=request.network_type.value,
        )

        # Convert to response models
        partners = [InteractionPartner(**partner) for partner in raw_partners]

        logger.info(
            "Successfully retrieved interaction partners",
            input_count=len(request.identifiers),
            partner_count=len(partners),
        )

        return InteractionPartnerListResponse(
            partners=partners,
            total_count=len(partners),
        )

    except StringDBAPIError as e:
        logger.exception(
            "StringDB API error during interaction partner retrieval",
            error=str(e),
            status_code=e.status_code,
        )
        raise HTTPException(
            status_code=e.status_code or 502,
            detail=f"StringDB API error: {e.message}",
        )

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
        )

    except Exception as e:
        logger.error(
            "Unexpected error during interaction partner retrieval",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during interaction partner retrieval",
        )


@router.get("/networks/interactions/{identifier}")
async def get_single_protein_network(
    identifier: str,
    species: int = Query(None, description="NCBI taxon identifier"),
    required_score: int = Query(400, description="Minimum confidence score (0-1000)"),
    add_nodes: int = Query(10, description="Number of additional nodes to add"),
    network_type: str = Query("functional", description="Network type (functional or physical)"),
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> NetworkInteractionListResponse:
    """Get interaction network for a single protein.

    Convenience endpoint for getting the interaction network of a single
    protein without requiring a JSON request body.

    Args:
        identifier: Protein identifier
        species: NCBI taxon identifier
        required_score: Minimum confidence score (0-1000)
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
            network_type=network_type,
            add_nodes=add_nodes,
        )

        # Use the main endpoint logic
        return await get_network_interactions(request, client, logger)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during single protein network retrieval",
            identifier=identifier,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during network retrieval",
        )


@router.get("/networks/partners/{identifier}")
async def get_single_protein_partners(
    identifier: str,
    species: int = Query(None, description="NCBI taxon identifier"),
    limit: int = Query(10, description="Maximum number of partners"),
    required_score: int = Query(400, description="Minimum confidence score (0-1000)"),
    network_type: str = Query("functional", description="Network type (functional or physical)"),
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> InteractionPartnerListResponse:
    """Get interaction partners for a single protein.

    Convenience endpoint for getting interaction partners of a single
    protein without requiring a JSON request body.

    Args:
        identifier: Protein identifier
        species: NCBI taxon identifier
        limit: Maximum number of partners
        required_score: Minimum confidence score (0-1000)
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
            network_type=network_type,
        )

        # Use the main endpoint logic
        return await get_interaction_partners(request, client, logger)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during single protein partner retrieval",
            identifier=identifier,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during partner retrieval",
        )


@router.post("/networks/link", response_model=LinkInfo)
async def get_network_link(
    request: LinkRequest,
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
    output_format: OutputFormat = Query(
        OutputFormat.JSON,
        description="Output format for the response",
    ),
) -> Response:
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

        # Prepare additional parameters for link generation
        link_params = {
            "required_score": request.required_score,
            "network_type": request.network_type.value,
            "network_flavor": request.network_flavor.value,
        }

        result = await client.get_link(
            identifiers=request.identifiers,
            species=request.species,
            output_format=output_format,
            **link_params,
        )

        if output_format == OutputFormat.JSON:
            # Extract URL from result
            if isinstance(result, dict):
                url = result.get("url", str(result))
            else:
                url = str(result)

            logger.info(
                "Successfully generated network link",
                identifiers=request.identifiers,
                url=url,
            )

            return LinkInfo(url=url)
        # Return raw text for non-JSON formats
        return PlainTextResponse(
            content=result,
            media_type="text/plain",
        )

    except StringDBAPIError as e:
        logger.error(
            "StringDB API error during link generation",
            identifiers=request.identifiers,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.error(
            "Unexpected error during link generation",
            identifiers=request.identifiers,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}",
        ) from e
