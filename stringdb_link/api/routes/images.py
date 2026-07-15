"""Image generation endpoints for StringDB-Link."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Response

from stringdb_link.exceptions import StringDBServiceError, ValidationError
from stringdb_link.models.requests import ImageRequest
from stringdb_link.models.responses import NetworkImageResult
from stringdb_link.services.stringdb_service import StringDBService

from .dependencies import LoggerDep, StringDBServiceDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

router = APIRouter()

_EMPTY_IMAGE_DETAIL = "STRING returned an empty image for this network; no image is available."


def _translate_image_errors(e: Exception, logger: FilteringBoundLogger) -> HTTPException:
    """Map a service/validation/unexpected failure to the right HTTP status."""
    if isinstance(e, StringDBServiceError):
        logger.exception("Service error during network image generation", error=str(e))
        return HTTPException(status_code=e.status_code or 500, detail=f"Service error: {e.message}")
    if isinstance(e, ValidationError):
        logger.exception("Validation error during network image generation", field=e.field)
        return HTTPException(status_code=400, detail=f"Validation error: {e.message}")
    logger.exception("Unexpected error during network image generation", error=str(e))
    return HTTPException(
        status_code=500, detail="Internal server error during network image generation"
    )


@router.post(
    "/images/network",
    operation_id="download_network_image",
    tags=["visualization"],
    response_class=Response,
    responses={200: {"content": {"image/png": {}, "image/svg+xml": {}}}},
)
async def download_network_image(
    request: ImageRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> Response:
    """Download the raw binary network image (REST clients).

    Returns STRING's image bytes with their native media type. This is the REST
    download contract; the MCP surface uses ``get_network_image`` (JSON base64),
    since binary cannot ride inside a structured MCP envelope. Excluded from MCP.
    """
    try:
        logger.info("Downloading network image", identifiers=request.identifiers)
        image = (await service.get_network_image(request)).image
        return Response(content=image.image_data or b"", media_type=image.content_type)
    except Exception as e:  # every failure is translated to an HTTP status
        raise _translate_image_errors(e, logger) from e


@router.post(
    "/images/network/json",
    response_model=NetworkImageResult,
    operation_id="get_network_image",
    tags=["visualization"],
)
async def get_network_image(
    request: ImageRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> NetworkImageResult:
    """Generate a protein network visualization image as base64 (MCP surface)."""
    try:
        logger.info("Generating network image", identifiers=request.identifiers)
        image = (await service.get_network_image(request)).image
        image_bytes = image.image_data or b""

        # An empty upstream body is NOT a successful zero-byte image — that would be a
        # silent-empty success. Surface it as a retryable upstream failure instead.
        if not image_bytes:
            raise HTTPException(status_code=502, detail=_EMPTY_IMAGE_DETAIL)

        # STRING returns binary image data, which cannot ride inside a structured MCP
        # envelope. Encode it as base64 so the tool returns a non-empty, decodable
        # result instead of an empty structured payload / internal error.
        return NetworkImageResult(
            image_format=image.image_format,
            content_type=image.content_type,
            image_size_bytes=len(image_bytes),
            image_base64=base64.b64encode(image_bytes).decode("ascii"),
        )

    except HTTPException:
        raise
    except Exception as e:  # every failure is translated to an HTTP status
        raise _translate_image_errors(e, logger) from e
