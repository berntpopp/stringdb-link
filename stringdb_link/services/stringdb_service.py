"""StringDB service with caching and business logic.

This module provides the StringDBService class that acts as an intermediary
between API routes and the StringDB client, implementing business logic,
caching, and data transformations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from stringdb_link.config import settings
from stringdb_link.exceptions import StringDBServiceError
from stringdb_link.logging_config import get_logger
from stringdb_link.models.requests import (
    AnnotationRequest,
    EnrichmentRequest,
    IdentifierRequest,
    ImageRequest,
    InteractionPartnersRequest,
    NetworkRequest,
)
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
            self.logger.error(
                "Error resolving identifiers",
                error=str(e),
                identifiers=request.identifiers,
                exc_info=True,
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

        return [StringIdMapping(**mapping) for mapping in raw_mappings]

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
                required_score=request.required_score,
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
            self.logger.error(
                "Error getting network interactions",
                error=str(e),
                identifiers=request.identifiers,
                exc_info=True,
            )
            msg = f"Failed to get network interactions: {e}"
            raise StringDBServiceError(msg) from e

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

        return [NetworkInteraction(**interaction) for interaction in raw_interactions]

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

            partners = await self._cached_get_interaction_partners(
                identifiers=tuple(request.identifiers),
                species=request.species,
                limit=request.limit,
                required_score=request.required_score,
                network_type=request.network_type.value,
            )

            self.logger.info(
                "Successfully retrieved interaction partners",
                input_count=len(request.identifiers),
                partner_count=len(partners),
            )

            return InteractionPartnerListResponse(
                partners=partners,
                total_count=len(partners),
            )

        except Exception as e:
            self.logger.error(
                "Error getting interaction partners",
                error=str(e),
                identifiers=request.identifiers,
                exc_info=True,
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
        limit: int,
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

        return [InteractionPartner(**partner) for partner in raw_partners]

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

            self.logger.info(
                "Successfully retrieved functional enrichment",
                input_count=len(request.identifiers),
                term_count=len(terms),
            )

            return EnrichmentTermListResponse(
                terms=terms,
                total_count=len(terms),
            )

        except Exception as e:
            self.logger.error(
                "Error getting functional enrichment",
                error=str(e),
                identifiers=request.identifiers,
                exc_info=True,
            )
            msg = f"Failed to get functional enrichment: {e}"
            raise StringDBServiceError(msg) from e

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

        return [EnrichmentTerm(**term) for term in raw_terms]

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
            self.logger.error(
                "Error getting functional annotations",
                error=str(e),
                identifiers=request.identifiers,
                exc_info=True,
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

        return [FunctionalAnnotation(**annotation) for annotation in raw_annotations]

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
                required_score=request.required_score,
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
            self.logger.error(
                "Error generating network image",
                error=str(e),
                identifiers=request.identifiers,
                exc_info=True,
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
            self.logger.error(
                "Error getting homology scores",
                error=str(e),
                identifiers=identifiers,
                species=species,
                exc_info=True,
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
            self.logger.error(
                "Error getting homology best hits",
                error=str(e),
                identifiers=identifiers,
                species=species,
                species_b=species_b,
                exc_info=True,
            )
            msg = f"Failed to get homology best hits: {e}"
            raise StringDBServiceError(msg) from e

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring."""
        return await cache_manager.get_stats()

    async def clear_cache(self) -> None:
        """Clear all service caches."""
        await cache_manager.clear_all_caches()
        self.logger.info("Service caches cleared")
