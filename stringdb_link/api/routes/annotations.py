"""Functional annotation endpoints for StringDB-Link."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from stringdb_link.exceptions import StringDBAPIError
from stringdb_link.models.requests import AnnotationRequest
from stringdb_link.models.responses import FunctionalAnnotation, FunctionalAnnotationListResponse

from .dependencies import LoggerDep, StringDBClientDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from stringdb_link.api.client import StringDBClient

router = APIRouter()


@router.post("/annotations/functional", response_model=FunctionalAnnotationListResponse)
async def get_functional_annotations(
    request: AnnotationRequest,
    client: StringDBClient = StringDBClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> FunctionalAnnotationListResponse:
    """Get functional annotations for proteins."""
    try:
        logger.info("Getting functional annotations", identifiers=request.identifiers)

        raw_annotations = await client.get_functional_annotation(
            identifiers=request.identifiers,
            species=request.species,
            allow_pubmed=request.allow_pubmed,
            only_pubmed=request.only_pubmed,
        )

        annotations = [FunctionalAnnotation(**annotation) for annotation in raw_annotations]

        return FunctionalAnnotationListResponse(
            annotations=annotations, total_count=len(annotations)
        )

    except StringDBAPIError as e:
        raise HTTPException(
            status_code=e.status_code or 502, detail=f"StringDB API error: {e.message}"
        )
    except Exception as e:
        logger.error("Error getting functional annotations", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
