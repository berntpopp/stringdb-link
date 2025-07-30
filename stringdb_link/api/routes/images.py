"""Image generation endpoints for StringDB-Link."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Response

from stringdb_link.exceptions import StringDBAPIError
from stringdb_link.models.requests import ImageRequest

from .dependencies import LoggerDep, StringDBClientDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from stringdb_link.api.client import StringDBClient

router = APIRouter()


@router.post("/images/network")
async def get_network_image(
    request: ImageRequest,
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> Response:
    """Generate protein network visualization image."""
    try:
        logger.info("Generating network image", identifiers=request.identifiers)

        image_data = await client.get_network_image(
            identifiers=request.identifiers,
            species=request.species,
            add_color_nodes=request.add_color_nodes,
            add_white_nodes=request.add_white_nodes,
            network_flavor=request.network_flavor.value,
            network_type=request.network_type.value,
            required_score=request.required_score,
            image_format=request.image_format.value,
        )

        # Determine content type based on format
        content_type = {
            "image": "image/png",
            "highres_image": "image/png",
            "svg": "image/svg+xml",
        }.get(request.image_format.value, "image/png")

        return Response(content=image_data, media_type=content_type)

    except StringDBAPIError as e:
        raise HTTPException(
            status_code=e.status_code or 502, detail=f"StringDB API error: {e.message}"
        )
    except Exception as e:
        logger.error("Error generating network image", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
