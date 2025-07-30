"""Image generation endpoints for StringDB-Link."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Response

from stringdb_link.exceptions import StringDBServiceError, ValidationError
from stringdb_link.models.requests import ImageRequest
from stringdb_link.services.stringdb_service import StringDBService

from .dependencies import LoggerDep, StringDBServiceDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

router = APIRouter()


@router.post("/images/network")
async def get_network_image(
    request: ImageRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> Response:
    """Generate protein network visualization image."""
    try:
        logger.info("Generating network image", identifiers=request.identifiers)

        image_response = await service.get_network_image(request)
        image_data = image_response.image.image_data
        content_type = image_response.image.content_type

        return Response(content=image_data, media_type=content_type)

    except StringDBServiceError as e:
        logger.exception(
            "Service error during network image generation",
            error=str(e),
            operation=e.operation,
        )
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=f"Service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during network image generation",
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
            "Unexpected error during network image generation",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during network image generation",
        ) from e
