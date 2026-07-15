"""Image generation endpoints for StringDB-Link."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from stringdb_link.exceptions import StringDBServiceError, ValidationError
from stringdb_link.models.requests import ImageRequest
from stringdb_link.models.responses import NetworkImageResult
from stringdb_link.services.stringdb_service import StringDBService

from .dependencies import LoggerDep, StringDBServiceDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

router = APIRouter()


@router.post(
    "/images/network",
    response_model=NetworkImageResult,
    operation_id="get_network_image",
    tags=["visualization"],
)
async def get_network_image(
    request: ImageRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> NetworkImageResult:
    """Generate protein network visualization image (base64-encoded)."""
    try:
        logger.info("Generating network image", identifiers=request.identifiers)

        image_response = await service.get_network_image(request)
        image = image_response.image
        image_bytes = image.image_data or b""

        # STRING returns binary image data, which cannot ride inside a structured
        # MCP envelope. Encode it as base64 so the tool returns a non-empty,
        # decodable result instead of an empty structured payload / internal error.
        return NetworkImageResult(
            image_format=image.image_format,
            content_type=image.content_type,
            image_size_bytes=len(image_bytes),
            image_base64=base64.b64encode(image_bytes).decode("ascii"),
        )

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
