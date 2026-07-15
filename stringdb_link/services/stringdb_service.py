"""StringDB service with caching and business logic.

This module provides the StringDBService class that acts as an intermediary
between API routes and the StringDB client, implementing business logic,
caching, and data transformations.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, cast

from pydantic import ValidationError as PydanticValidationError

from stringdb_link.config import settings
from stringdb_link.exceptions import StringDBServiceError, ValidationError
from stringdb_link.logging_config import get_logger
from stringdb_link.models.responses import (
    EnrichmentTerm,
    EnrichmentTermListResponse,
    FunctionalAnnotation,
    FunctionalAnnotationListResponse,
    InteractionPartner,
    InteractionPartnerListResponse,
    NetworkImage,
    NetworkImageResponse,
    NetworkInteraction,
    NetworkInteractionListResponse,
    StringIdMapping,
    StringIdMappingListResponse,
)
from stringdb_link.models.stringdb import OutputFormat
from stringdb_link.utils.caching import cache_manager

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from stringdb_link.api.client import StringDBClient
    from stringdb_link.models.requests import (
        AnnotationRequest,
        EnrichmentRequest,
        IdentifierRequest,
        ImageRequest,
        InteractionPartnersRequest,
        LinkRequest,
        NetworkRequest,
        PPIEnrichmentRequest,
    )
    from stringdb_link.models.responses import LinkInfo, PPIEnrichmentResult


#: Field named in the invalid_input envelope when STRING reports an in-band error
#: about the caller-supplied background proteome.
_BACKGROUND_FIELD = "background_string_identifiers"
#: Default offending field for any OTHER STRING in-band error: the query proteins are
#: what STRING validates (unknown/misspelled identifiers, unsupported species, etc.).
_DEFAULT_INPUT_FIELD = "identifiers"
#: Fixed, server-authored messages. The upstream STRING error prose is NEVER echoed
#: (it is caller-influenceable); only these constants and the offending field name
#: reach the caller (security posture).
_BACKGROUND_ERROR_MESSAGE = (
    "The custom background proteome is invalid: it must be a superset of the query "
    "identifiers. Adjust 'background_string_identifiers' so it contains every query "
    "protein, or omit it to use the whole-genome background."
)
_GENERIC_INPUT_MESSAGE = (
    "The upstream STRING API rejected the request as invalid; check the query "
    "'identifiers' (and 'species'). This is not a transient outage — retrying "
    "unchanged will fail identically."
)

#: STRING in-band error type -> the offending input field it names. Any type not
#: listed falls back to ``_DEFAULT_INPUT_FIELD`` — the general class is handled, not
#: just the one known case (a new STRING error type still yields invalid_input with a
#: named field, never a false retryable upstream_unavailable or a field-less error).
_STRING_ERROR_FIELD: dict[str, str] = {
    "background_error": _BACKGROUND_FIELD,
}


def _raise_if_string_error(payload: object) -> None:
    """Map STRING's in-band error shape onto a client-side ``invalid_input``.

    STRING returns HTTP 200 with a body like ``[{"error": "background_error",
    "message": "..."}]`` for a bad request. Left unhandled, building a typed model
    from that body raises a validation error that the service mis-maps to
    ``upstream_unavailable`` (retryable) — a false "the upstream is down, retry
    forever". Detect the shape here for the GENERAL class (any ``{"error": ...}``
    item) and raise ``ValidationError`` (400 → invalid_input, non-retryable) naming
    the offending parameter, without echoing the upstream prose.
    """
    item: dict[str, object] | None = None
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        item = payload[0]
    elif isinstance(payload, dict):
        item = payload
    if item is None or not item.get("error"):
        return
    error_type = str(item.get("error"))
    if error_type == "background_error":
        raise ValidationError(_BACKGROUND_ERROR_MESSAGE, field=_BACKGROUND_FIELD)
    field = _STRING_ERROR_FIELD.get(error_type, _DEFAULT_INPUT_FIELD)
    raise ValidationError(_GENERIC_INPUT_MESSAGE, field=field)


def _extract_url(raw: str) -> str:
    """Pull the shareable URL out of STRING's tsv/tsv-no-header/xml link response.

    get_link conveys the same URL in every format (``url\\n<url>`` for tsv, the bare
    line for tsv-no-header, ``<url>...</url>`` for xml). Match the first ``http(s)``
    token; fall back to the stripped body so the structured ``url`` is never empty.
    """
    # Exclude whitespace and markup delimiters so the trailing ``</url>`` in the xml
    # form (``<url>https://...</url>``) is not swallowed into the URL.
    match = re.search(r"https?://[^\s<>\"']+", raw)
    if match:
        return match.group(0)
    return raw.strip()


def _limit_partners_per_protein(
    partners: list[InteractionPartner], limit: int
) -> list[InteractionPartner]:
    """Return at most ``limit`` partners PER QUERY PROTEIN, preserving order.

    STRING's ``limit`` is per-protein and its rows arrive grouped by the query
    protein (``string_id_a`` / ``stringId_A``), most-confident first. Grouping here
    — rather than a global ``partners[:limit]`` — guarantees every queried protein is
    represented: a global head-slice returns only the first protein's partners once
    it has ``limit`` of them and silently omits every later protein.
    """
    counts: dict[str, int] = {}
    kept: list[InteractionPartner] = []
    for partner in partners:
        query_id = partner.string_id_a
        seen = counts.get(query_id, 0)
        if seen >= limit:
            continue
        counts[query_id] = seen + 1
        kept.append(partner)
    return kept


class StringDBService:
    """Service for StringDB operations with caching and business logic."""

    def __init__(
        self,
        client: StringDBClient,
        logger: FilteringBoundLogger | None = None,
    ) -> None:
        """Initialize StringDB service.

        Args:
            client: StringDB API client
            logger: Optional logger instance
        """
        self.client = client
        self.logger = logger or get_logger(__name__)

    async def resolve_identifiers(self, request: IdentifierRequest) -> StringIdMappingListResponse:
        """Resolve protein identifiers to STRING database identifiers.

        Args:
            request: Identifier resolution request

        Returns:
            List of identifier mappings

        Raises:
            StringDBServiceError: If the operation fails
            ValidationError: If request validation fails
        """
        try:
            self.logger.info(
                "Resolving protein identifiers",
                identifiers=request.identifiers,
                species=request.species,
                echo_query=request.echo_query,
            )

            # Call cached implementation
            mappings = await self._cached_resolve_identifiers(
                identifiers=tuple(request.identifiers),  # Use tuple for hashability
                species=request.species,
                echo_query=request.echo_query,
            )

            self.logger.info(
                "Successfully resolved identifiers",
                input_count=len(request.identifiers),
                output_count=len(mappings),
            )

            return StringIdMappingListResponse(
                mappings=mappings,
                total_count=len(mappings),
            )

        except Exception as e:
            self.logger.exception(
                "Error resolving identifiers",
                error=str(e),
                identifiers=request.identifiers,
            )
            msg = f"Failed to resolve identifiers: {e}"
            raise StringDBServiceError(msg) from e

    @cache_manager.cached(
        maxsize=1000,
        ttl=settings.cache_identifier_ttl,
        cache_name="identifier_resolution",
    )
    async def _cached_resolve_identifiers(
        self,
        identifiers: tuple[str, ...],
        species: int | None,
        echo_query: bool,
    ) -> list[StringIdMapping]:
        """Get cached identifier resolution results."""
        raw_mappings = await self.client.get_string_ids(
            identifiers=list(identifiers),
            species=species,
            echo_query=echo_query,
        )
        records = raw_mappings if isinstance(raw_mappings, list) else []
        return [StringIdMapping(**mapping) for mapping in records]

    async def get_network_interactions(
        self, request: NetworkRequest
    ) -> NetworkInteractionListResponse:
        """Get protein-protein interaction network.

        Args:
            request: Network interaction request

        Returns:
            List of protein-protein interactions

        Raises:
            StringDBServiceError: If the operation fails
        """
        try:
            self.logger.info(
                "Getting network interactions",
                identifiers=request.identifiers,
                species=request.species,
                required_score=request.required_score,
                network_type=request.network_type,
                add_nodes=request.add_nodes,
            )

            interactions = await self._cached_get_network_interactions(
                identifiers=tuple(request.identifiers),
                species=request.species,
                required_score=round(request.required_score * 1000),
                network_type=request.network_type.value,
                add_nodes=request.add_nodes,
                show_query_node_labels=request.show_query_node_labels,
            )

            self.logger.info(
                "Successfully retrieved network interactions",
                input_count=len(request.identifiers),
                interaction_count=len(interactions),
            )

            return NetworkInteractionListResponse(
                interactions=interactions,
                total_count=len(interactions),
            )

        except Exception as e:
            self.logger.exception(
                "Error getting network interactions",
                error=str(e),
                identifiers=request.identifiers,
            )
            msg = f"Failed to get network interactions: {e}"
            status = 502 if isinstance(e, PydanticValidationError) else None
            raise StringDBServiceError(msg, original_error=e, status_code=status) from e

    @cache_manager.cached(
        maxsize=500,
        ttl=settings.cache_network_ttl,
        cache_name="network_interactions",
    )
    async def _cached_get_network_interactions(
        self,
        identifiers: tuple[str, ...],
        species: int | None,
        required_score: int,
        network_type: str,
        add_nodes: int,
        show_query_node_labels: bool,
    ) -> list[NetworkInteraction]:
        """Get cached network interaction results."""
        raw_interactions = await self.client.get_network_interactions(
            identifiers=list(identifiers),
            species=species,
            required_score=required_score,
            network_type=network_type,
            add_nodes=add_nodes,
            show_query_node_labels=show_query_node_labels,
        )
        records = raw_interactions if isinstance(raw_interactions, list) else []
        return [NetworkInteraction(**interaction) for interaction in records]

    async def get_interaction_partners(
        self, request: InteractionPartnersRequest
    ) -> InteractionPartnerListResponse:
        """Get interaction partners for proteins.

        Args:
            request: Interaction partners request

        Returns:
            List of interaction partners

        Raises:
            StringDBServiceError: If the operation fails
        """
        try:
            self.logger.info(
                "Getting interaction partners",
                identifiers=request.identifiers,
                species=request.species,
                limit=request.limit,
                required_score=request.required_score,
                network_type=request.network_type,
            )

            # STRING's ``limit`` is PER PROTEIN. Fetch the FULL partner set (no upstream
            # limit) so ``total_count`` is the true count, invariant of the caller's
            # ``limit``; then apply ``limit`` PER QUERY PROTEIN so every queried protein
            # is represented (a global head-slice would return only the first protein's
            # partners and omit every later protein entirely).
            all_partners = await self._cached_get_interaction_partners(
                identifiers=tuple(request.identifiers),
                species=request.species,
                limit=None,
                required_score=round(request.required_score * 1000),
                network_type=request.network_type.value,
            )
            limited = _limit_partners_per_protein(all_partners, request.limit)
            total = len(all_partners)

            self.logger.info(
                "Successfully retrieved interaction partners",
                input_count=len(request.identifiers),
                partner_count=len(limited),
                total_count=total,
            )

            return InteractionPartnerListResponse(
                partners=limited,
                total_count=total,
                truncated=total > len(limited),
            )

        except Exception as e:
            self.logger.exception(
                "Error getting interaction partners",
                error=str(e),
                identifiers=request.identifiers,
            )
            msg = f"Failed to get interaction partners: {e}"
            raise StringDBServiceError(msg) from e

    @cache_manager.cached(
        maxsize=500,
        ttl=settings.cache_network_ttl,
        cache_name="interaction_partners",
    )
    async def _cached_get_interaction_partners(
        self,
        identifiers: tuple[str, ...],
        species: int | None,
        limit: int | None,
        required_score: int,
        network_type: str,
    ) -> list[InteractionPartner]:
        """Get cached interaction partner results."""
        raw_partners = await self.client.get_interaction_partners(
            identifiers=list(identifiers),
            species=species,
            limit=limit,
            required_score=required_score,
            network_type=network_type,
        )
        records = raw_partners if isinstance(raw_partners, list) else []
        return [InteractionPartner(**partner) for partner in records]

    async def get_functional_enrichment(
        self, request: EnrichmentRequest
    ) -> EnrichmentTermListResponse:
        """Get functional enrichment analysis.

        Args:
            request: Enrichment analysis request

        Returns:
            List of enrichment terms

        Raises:
            StringDBServiceError: If the operation fails
        """
        try:
            self.logger.info(
                "Getting functional enrichment",
                identifiers=request.identifiers,
                species=request.species,
            )

            terms = await self._cached_get_functional_enrichment(
                identifiers=tuple(request.identifiers),
                species=request.species,
                background_string_identifiers=(
                    tuple(request.background_string_identifiers)
                    if request.background_string_identifiers
                    else None
                ),
            )

            # Optional category filter (closed vocabulary) and top-N truncation.
            # ``total_count`` reports the FULL number of matching terms so a smaller
            # ``limit`` never hides how many exist (honest total, invariant of limit).
            if request.category is not None:
                category_value = request.category.value
                terms = [term for term in terms if term.category == category_value]
            terms = sorted(terms, key=lambda term: term.fdr)
            total = len(terms)
            limited = terms[: request.limit]

            self.logger.info(
                "Successfully retrieved functional enrichment",
                input_count=len(request.identifiers),
                term_count=len(limited),
                total_count=total,
            )

            return EnrichmentTermListResponse(
                terms=limited,
                total_count=total,
                truncated=total > len(limited),
            )

        except ValidationError:
            # STRING in-band error (e.g. background_error) already classified as
            # invalid_input — propagate unwrapped so it is not re-mapped to 5xx.
            raise
        except Exception as e:
            self.logger.exception(
                "Error getting functional enrichment",
                error=str(e),
                identifiers=request.identifiers,
            )
            msg = f"Failed to get functional enrichment: {e}"
            status = 502 if isinstance(e, PydanticValidationError) else None
            raise StringDBServiceError(msg, original_error=e, status_code=status) from e

    @cache_manager.cached(
        maxsize=300,
        ttl=settings.cache_enrichment_ttl,
        cache_name="functional_enrichment",
    )
    async def _cached_get_functional_enrichment(
        self,
        identifiers: tuple[str, ...],
        species: int | None,
        background_string_identifiers: tuple[str, ...] | None,
    ) -> list[EnrichmentTerm]:
        """Get cached functional enrichment results."""
        raw_terms = await self.client.get_functional_enrichment(
            identifiers=list(identifiers),
            species=species,
            background_string_identifiers=(
                list(background_string_identifiers) if background_string_identifiers else None
            ),
        )
        # Detect STRING's in-band error body (HTTP 200 + [{"error": ...}]) before
        # attempting to build typed models from it (defect: was mis-mapped to
        # upstream_unavailable/retryable).
        _raise_if_string_error(raw_terms)
        records = raw_terms if isinstance(raw_terms, list) else []
        return [EnrichmentTerm(**term) for term in records]

    async def get_functional_annotation(
        self, request: AnnotationRequest
    ) -> FunctionalAnnotationListResponse:
        """Get functional annotations for proteins.

        Args:
            request: Annotation request

        Returns:
            List of functional annotations

        Raises:
            StringDBServiceError: If the operation fails
        """
        try:
            self.logger.info(
                "Getting functional annotations",
                identifiers=request.identifiers,
                species=request.species,
                allow_pubmed=request.allow_pubmed,
                only_pubmed=request.only_pubmed,
            )

            annotations = await self._cached_get_functional_annotation(
                identifiers=tuple(request.identifiers),
                species=request.species,
                allow_pubmed=request.allow_pubmed,
                only_pubmed=request.only_pubmed,
            )

            self.logger.info(
                "Successfully retrieved functional annotations",
                input_count=len(request.identifiers),
                annotation_count=len(annotations),
            )

            return FunctionalAnnotationListResponse(
                annotations=annotations,
                total_count=len(annotations),
            )

        except Exception as e:
            self.logger.exception(
                "Error getting functional annotations",
                error=str(e),
                identifiers=request.identifiers,
            )
            msg = f"Failed to get functional annotations: {e}"
            raise StringDBServiceError(msg) from e

    @cache_manager.cached(
        maxsize=400,
        ttl=settings.cache_enrichment_ttl,
        cache_name="functional_annotations",
    )
    async def _cached_get_functional_annotation(
        self,
        identifiers: tuple[str, ...],
        species: int | None,
        allow_pubmed: bool,
        only_pubmed: bool,
    ) -> list[FunctionalAnnotation]:
        """Get cached functional annotation results."""
        raw_annotations = await self.client.get_functional_annotation(
            identifiers=list(identifiers),
            species=species,
            allow_pubmed=allow_pubmed,
            only_pubmed=only_pubmed,
        )
        records = raw_annotations if isinstance(raw_annotations, list) else []
        return [FunctionalAnnotation(**annotation) for annotation in records]

    async def get_network_image(self, request: ImageRequest) -> NetworkImageResponse:
        """Generate network visualization image.

        Args:
            request: Image generation request

        Returns:
            Network image response

        Raises:
            StringDBServiceError: If the operation fails
        """
        try:
            self.logger.info(
                "Generating network image",
                identifiers=request.identifiers,
                species=request.species,
                image_format=request.image_format,
                network_flavor=request.network_flavor,
            )

            image = await self._cached_get_network_image(
                identifiers=tuple(request.identifiers),
                species=request.species,
                add_color_nodes=request.add_color_nodes,
                add_white_nodes=request.add_white_nodes,
                network_flavor=request.network_flavor.value,
                network_type=request.network_type.value,
                required_score=round(request.required_score * 1000),
                image_format=request.image_format.value,
                hide_node_labels=request.hide_node_labels,
                hide_disconnected_nodes=request.hide_disconnected_nodes,
                show_query_node_labels=request.show_query_node_labels,
            )

            self.logger.info(
                "Successfully generated network image",
                input_count=len(request.identifiers),
                image_size=len(image.image_data) if image.image_data else 0,
            )

            return NetworkImageResponse(image=image)

        except Exception as e:
            self.logger.exception(
                "Error generating network image",
                error=str(e),
                identifiers=request.identifiers,
            )
            msg = f"Failed to generate network image: {e}"
            raise StringDBServiceError(msg) from e

    @cache_manager.cached(
        maxsize=100,
        ttl=settings.cache_image_ttl,
        cache_name="network_images",
    )
    async def _cached_get_network_image(
        self,
        identifiers: tuple[str, ...],
        species: int | None,
        add_color_nodes: int,
        add_white_nodes: int,
        network_flavor: str,
        network_type: str,
        required_score: int,
        image_format: str,
        hide_node_labels: bool,
        hide_disconnected_nodes: bool,
        show_query_node_labels: bool,
    ) -> NetworkImage:
        """Get cached network image results."""
        raw_image_data = await self.client.get_network_image(
            identifiers=list(identifiers),
            species=species,
            add_color_nodes=add_color_nodes,
            add_white_nodes=add_white_nodes,
            network_flavor=network_flavor,
            network_type=network_type,
            required_score=required_score,
            image_format=image_format,
            hide_node_labels=hide_node_labels,
            hide_disconnected_nodes=hide_disconnected_nodes,
            show_query_node_labels=show_query_node_labels,
        )

        return NetworkImage(
            image_data=raw_image_data,
            image_format=image_format,
            content_type=self._get_image_content_type(image_format),
        )

    def _get_image_content_type(self, image_format: str) -> str:
        """Get content type for image format."""
        format_mapping = {
            "image": "image/png",
            "highres_image": "image/png",
            "svg": "image/svg+xml",
        }
        return format_mapping.get(image_format, "image/png")

    async def get_homology_scores(
        self,
        identifiers: list[str],
        species: int | None = None,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> list[dict[str, Any]] | str:
        """Get protein homology scores.

        Args:
            identifiers: List of protein identifiers
            species: NCBI taxon ID for source species
            output_format: Output format (json, tsv, xml, psi-mi)

        Returns:
            Homology scores data

        Raises:
            StringDBServiceError: If the operation fails
        """
        try:
            self.logger.info(
                "Getting homology scores",
                input_count=len(identifiers),
                species=species,
                output_format=output_format.value,
            )

            result = await self.client.get_homology_scores(
                identifiers=identifiers,
                species=species,
                output_format=output_format,
            )

            if output_format == OutputFormat.JSON:
                self.logger.info(
                    "Successfully retrieved homology scores",
                    input_count=len(identifiers),
                    result_count=len(result) if isinstance(result, list) else "N/A",
                )
            else:
                self.logger.info(
                    "Successfully retrieved homology scores",
                    input_count=len(identifiers),
                    output_format=output_format.value,
                )

            return result

        except Exception as e:
            self.logger.exception(
                "Error getting homology scores",
                error=str(e),
                identifiers=identifiers,
                species=species,
            )
            msg = f"Failed to get homology scores: {e}"
            raise StringDBServiceError(msg) from e

    async def get_homology_best_hits(
        self,
        identifiers: list[str],
        species: int | None = None,
        species_b: list[int] | None = None,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> list[dict[str, Any]] | str:
        """Get best homology hits between species.

        Args:
            identifiers: List of protein identifiers
            species: Source species NCBI taxon ID
            species_b: Target species list
            output_format: Output format (json, tsv, xml, psi-mi)

        Returns:
            Best homology hits data

        Raises:
            StringDBServiceError: If the operation fails
        """
        try:
            self.logger.info(
                "Getting homology best hits",
                input_count=len(identifiers),
                species=species,
                species_b=species_b,
                output_format=output_format.value,
            )

            result = await self.client.get_homology_best_hits(
                identifiers=identifiers,
                species=species,
                species_b=species_b,
                output_format=output_format,
            )

            if output_format == OutputFormat.JSON:
                self.logger.info(
                    "Successfully retrieved homology best hits",
                    input_count=len(identifiers),
                    result_count=len(result) if isinstance(result, list) else "N/A",
                )
            else:
                self.logger.info(
                    "Successfully retrieved homology best hits",
                    input_count=len(identifiers),
                    output_format=output_format.value,
                )

            return result

        except Exception as e:
            self.logger.exception(
                "Error getting homology best hits",
                error=str(e),
                identifiers=identifiers,
                species=species,
                species_b=species_b,
            )
            msg = f"Failed to get homology best hits: {e}"
            raise StringDBServiceError(msg) from e

    async def get_ppi_enrichment(self, request: PPIEnrichmentRequest) -> PPIEnrichmentResult:
        """Get protein-protein interaction enrichment analysis.

        Args:
            request: PPI enrichment analysis request

        Returns:
            PPI enrichment analysis result

        Raises:
            StringDBServiceError: If the operation fails
        """
        try:
            self.logger.info(
                "Getting PPI enrichment",
                identifiers=request.identifiers,
                species=request.species,
            )

            raw_result = await self.client.get_ppi_enrichment(
                identifiers=request.identifiers,
                species=request.species,
                required_score=round(request.required_score * 1000),
                background_string_identifiers=request.background_string_identifiers,
            )

            # Same STRING in-band error shape as functional enrichment: a bad
            # background returns {"error": "background_error", ...} at HTTP 200.
            _raise_if_string_error(raw_result)

            from stringdb_link.models.responses import PPIEnrichmentResult

            result = PPIEnrichmentResult(**cast("dict[str, Any]", raw_result))

            self.logger.info(
                "Successfully retrieved PPI enrichment",
                identifiers=request.identifiers,
                species=request.species,
            )

            return result

        except ValidationError:
            raise
        except Exception as e:
            self.logger.exception(
                "Error getting PPI enrichment",
                error=str(e),
                identifiers=request.identifiers,
                species=request.species,
            )
            msg = f"Failed to get PPI enrichment: {e}"
            raise StringDBServiceError(msg) from e

    async def get_network_link(self, request: LinkRequest, output_format: str = "json") -> LinkInfo:
        """Get shareable link to STRING webpage for the network.

        Args:
            request: Link generation request
            output_format: STRING serialization to render (json/tsv/tsv-no-header/xml).
                Every format conveys the same shareable URL; for non-json formats the
                raw STRING text is returned in ``LinkInfo.formatted`` and the URL is
                extracted into ``LinkInfo.url`` so the MCP result is never empty.

        Returns:
            Link information with URL (and, for non-json, the formatted serialization)

        Raises:
            StringDBServiceError: If the operation fails
        """
        try:
            self.logger.info(
                "Getting network link",
                identifiers=request.identifiers,
                species=request.species,
            )

            # Prepare additional parameters for link generation
            link_params = {
                "required_score": round(request.required_score * 1000),
                "network_type": request.network_type.value,
                "network_flavor": request.network_flavor.value,
            }

            fmt = OutputFormat(output_format)
            result = await self.client.get_link(
                identifiers=request.identifiers,
                species=request.species,
                output_format=fmt,
                **link_params,
            )

            from stringdb_link.models.responses import LinkInfo

            if fmt == OutputFormat.JSON:
                # client.get_link already unwrapped STRING's ["<url>"] to the url string
                # (or a {"url": ...} dict for defensive parity).
                url = result.get("url", str(result)) if isinstance(result, dict) else str(result)
                link_info = LinkInfo(url=url, output_format=fmt.value, formatted=None)
            else:
                raw = str(result)
                link_info = LinkInfo(url=_extract_url(raw), output_format=fmt.value, formatted=raw)

            # Count/status only — never the raw identifiers or generated URL (PII).
            self.logger.info(
                "Successfully generated network link",
                identifier_count=len(request.identifiers),
                output_format=fmt.value,
            )

            return link_info

        except Exception as e:
            self.logger.exception(
                "Error getting network link",
                error=str(e),
                identifiers=request.identifiers,
                species=request.species,
            )
            msg = f"Failed to get network link: {e}"
            raise StringDBServiceError(msg) from e

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring."""
        return await cache_manager.get_stats()

    async def clear_cache(self) -> None:
        """Clear all service caches."""
        await cache_manager.clear_all_caches()
        self.logger.info("Service caches cleared")
