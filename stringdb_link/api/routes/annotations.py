"""Functional annotation endpoints for StringDB-Link."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from stringdb_link.exceptions import StringDBServiceError, ValidationError
from stringdb_link.models.requests import AnnotationRequest
from stringdb_link.models.responses import FunctionalAnnotationListResponse
from stringdb_link.services.stringdb_service import StringDBService

from .dependencies import LoggerDep, StringDBServiceDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

router = APIRouter()


@router.post("/annotations/functional", response_model=FunctionalAnnotationListResponse)
async def get_functional_annotations(
    request: AnnotationRequest,
    service: StringDBService = StringDBServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> FunctionalAnnotationListResponse:
    """Get functional annotations for proteins."""
    try:
        logger.info("Getting functional annotations", identifiers=request.identifiers)

        return await service.get_functional_annotation(request)

    except StringDBServiceError as e:
        logger.exception(
            "Service error during functional annotation retrieval",
            error=str(e),
            operation=e.operation,
        )
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=f"Service error: {e.message}",
        ) from e

    except ValidationError as e:
        logger.exception(
            "Validation error during functional annotation retrieval",
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
            "Unexpected error during functional annotation retrieval",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during functional annotation retrieval",
        ) from e
