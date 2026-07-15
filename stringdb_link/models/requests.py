"""Request models for StringDB-Link API.

This module defines Pydantic models for all API request types with validation
and documentation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .stringdb import (
    MAX_ADDITIONAL_NODES,
    MAX_CONFIDENCE_SCORE,
    MAX_IDENTIFIERS_PER_REQUEST,
    MIN_CONFIDENCE_SCORE,
    ConfidenceScore,
    EnrichmentCategory,
    ImageFormat,
    NetworkFlavor,
    NetworkType,
)


class BaseRequest(BaseModel):
    """Base request model with common fields."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )


class IdentifierRequest(BaseRequest):
    """Request model for protein identifier resolution."""

    identifiers: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_IDENTIFIERS_PER_REQUEST,
        description="List of protein identifiers to resolve",
        examples=[["p53", "BRCA1", "cdk2", "Q99835"]],
    )
    species: int | None = Field(
        None,
        ge=1,
        description="NCBI taxon identifier (e.g., 9606 for human)",
        examples=[9606],
    )
    echo_query: bool = Field(
        False,
        description="Include input identifiers in the output",
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Validate protein identifiers."""
        if not v:
            msg = "At least one identifier is required"
            raise ValueError(msg)

        # Remove empty strings and duplicates while preserving order
        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        if not cleaned:
            msg = "No valid identifiers provided"
            raise ValueError(msg)

        return cleaned


class NetworkRequest(BaseRequest):
    """Request model for protein network interactions."""

    identifiers: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_IDENTIFIERS_PER_REQUEST,
        description="List of protein identifiers",
        examples=[["TP53", "EGFR", "CDK2"]],
    )
    species: int | None = Field(
        None,
        ge=1,
        description="NCBI taxon identifier",
        examples=[9606],
    )
    required_score: float = Field(
        ConfidenceScore.MEDIUM,
        ge=MIN_CONFIDENCE_SCORE,
        le=MAX_CONFIDENCE_SCORE,
        description="Minimum confidence score (0.0-1.0)",
    )
    network_type: NetworkType = Field(
        NetworkType.FUNCTIONAL,
        description="Network type: functional or physical",
    )
    add_nodes: int = Field(
        0,
        ge=0,
        le=MAX_ADDITIONAL_NODES,
        description="Number of additional nodes to add to the network",
    )
    show_query_node_labels: bool = Field(
        False,
        description="Use submitted names as node labels",
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Validate protein identifiers."""
        if not v:
            msg = "At least one identifier is required"
            raise ValueError(msg)

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        if not cleaned:
            msg = "No valid identifiers provided"
            raise ValueError(msg)

        return cleaned


class InteractionPartnersRequest(BaseRequest):
    """Request model for getting interaction partners."""

    identifiers: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_IDENTIFIERS_PER_REQUEST,
        description="List of protein identifiers",
        examples=[["TP53", "CDK2"]],
    )
    species: int | None = Field(
        None,
        ge=1,
        description="NCBI taxon identifier",
        examples=[9606],
    )
    limit: int = Field(
        10,
        ge=1,
        le=500,
        description="Maximum number of interaction partners per protein",
    )
    required_score: float = Field(
        ConfidenceScore.MEDIUM,
        ge=MIN_CONFIDENCE_SCORE,
        le=MAX_CONFIDENCE_SCORE,
        description="Minimum confidence score (0.0-1.0)",
    )
    network_type: NetworkType = Field(
        NetworkType.FUNCTIONAL,
        description="Network type: functional or physical",
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Validate protein identifiers."""
        if not v:
            msg = "At least one identifier is required"
            raise ValueError(msg)

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        if not cleaned:
            msg = "No valid identifiers provided"
            raise ValueError(msg)

        return cleaned


class EnrichmentRequest(BaseRequest):
    """Request model for functional enrichment analysis."""

    identifiers: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_IDENTIFIERS_PER_REQUEST,
        description="List of protein identifiers",
        examples=[["trpA", "trpB", "trpC", "trpE", "trpGD"]],
    )
    species: int | None = Field(
        None,
        ge=1,
        description="NCBI taxon identifier",
        examples=[511145],
    )
    category: EnrichmentCategory | None = Field(
        None,
        description=(
            "Optional term-category filter. When set, only enrichment terms in "
            "this STRING category are returned (e.g. 'KEGG' for pathways, "
            "'Process' for GO biological process, 'DISEASES' for disease "
            "associations). Omit to return terms across all categories."
        ),
        examples=["KEGG"],
    )
    limit: int = Field(
        100,
        ge=1,
        le=1000,
        description=(
            "Maximum number of enrichment terms to return, taken as the most "
            "significant (lowest FDR) first. 'total_count' still reports the full "
            "number of matching terms, so a smaller limit never hides how many exist."
        ),
        examples=[25],
    )
    background_string_identifiers: list[str] | None = Field(
        None,
        description=(
            "Optional custom background proteome, given as STRING identifiers "
            "(e.g. '9606.ENSP00000269305'). MUST be a superset of the query "
            "identifiers; STRING rejects a background that omits any query protein."
        ),
        examples=[["9606.ENSP00000269305", "9606.ENSP00000350283"]],
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Validate protein identifiers."""
        if not v:
            msg = "At least one identifier is required"
            raise ValueError(msg)

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        if not cleaned:
            msg = "No valid identifiers provided"
            raise ValueError(msg)

        return cleaned

    @field_validator("background_string_identifiers")
    @classmethod
    def validate_background_identifiers(
        cls,
        v: list[str] | None,
    ) -> list[str] | None:
        """Validate background identifiers."""
        if v is None:
            return v

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        return cleaned if cleaned else None


class AnnotationRequest(BaseRequest):
    """Request model for functional annotations."""

    identifiers: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_IDENTIFIERS_PER_REQUEST,
        description="List of protein identifiers",
        examples=[["cdk1"]],
    )
    species: int | None = Field(
        None,
        ge=1,
        description="NCBI taxon identifier",
        examples=[9606],
    )
    allow_pubmed: bool = Field(
        False,
        description="Include PubMed annotations",
    )
    only_pubmed: bool = Field(
        False,
        description="Return only PubMed annotations",
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Validate protein identifiers."""
        if not v:
            msg = "At least one identifier is required"
            raise ValueError(msg)

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        if not cleaned:
            msg = "No valid identifiers provided"
            raise ValueError(msg)

        return cleaned


class ImageRequest(BaseRequest):
    """Request model for network image generation."""

    identifiers: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_IDENTIFIERS_PER_REQUEST,
        description="List of protein identifiers",
        examples=[["nup100"]],
    )
    species: int | None = Field(
        None,
        ge=1,
        description="NCBI taxon identifier",
        examples=[4932],
    )
    add_color_nodes: int = Field(
        0,
        ge=0,
        le=MAX_ADDITIONAL_NODES,
        description="Number of colored nodes to add",
    )
    add_white_nodes: int = Field(
        0,
        ge=0,
        le=MAX_ADDITIONAL_NODES,
        description="Number of white nodes to add",
    )
    network_flavor: NetworkFlavor = Field(
        NetworkFlavor.EVIDENCE,
        description="Network visualization style",
    )
    network_type: NetworkType = Field(
        NetworkType.FUNCTIONAL,
        description="Network type: functional or physical",
    )
    required_score: float = Field(
        ConfidenceScore.MEDIUM,
        ge=MIN_CONFIDENCE_SCORE,
        le=MAX_CONFIDENCE_SCORE,
        description="Minimum confidence score (0.0-1.0)",
    )
    image_format: ImageFormat = Field(
        ImageFormat.PNG,
        description="Image format: PNG, high-res PNG, or SVG",
    )
    hide_node_labels: bool = Field(
        False,
        description="Hide protein names from the image",
    )
    hide_disconnected_nodes: bool = Field(
        False,
        description="Hide proteins not connected to any other protein",
    )
    show_query_node_labels: bool = Field(
        False,
        description="Use submitted names as protein labels",
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Validate protein identifiers."""
        if not v:
            msg = "At least one identifier is required"
            raise ValueError(msg)

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        if not cleaned:
            msg = "No valid identifiers provided"
            raise ValueError(msg)

        return cleaned


class HomologyRequest(BaseRequest):
    """Request model for protein homology scores."""

    identifiers: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_IDENTIFIERS_PER_REQUEST,
        description="List of protein identifiers",
        examples=[["CDK1", "CDK2"]],
    )
    species: int | None = Field(
        None,
        ge=1,
        description="NCBI taxon identifier",
        examples=[9606],
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Validate protein identifiers."""
        if not v:
            msg = "At least one identifier is required"
            raise ValueError(msg)

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        if not cleaned:
            msg = "No valid identifiers provided"
            raise ValueError(msg)

        return cleaned


class HomologyBestRequest(BaseRequest):
    """Request model for best homology hits between species."""

    identifiers: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_IDENTIFIERS_PER_REQUEST,
        description="List of protein identifiers",
        examples=[["CDK1"]],
    )
    species: int | None = Field(
        None,
        ge=1,
        description="Source species NCBI taxon identifier",
        examples=[9606],
    )
    species_b: list[int] | None = Field(
        None,
        description="Target species NCBI taxon identifiers",
        examples=[[10090]],
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Validate protein identifiers."""
        if not v:
            msg = "At least one identifier is required"
            raise ValueError(msg)

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        if not cleaned:
            msg = "No valid identifiers provided"
            raise ValueError(msg)

        return cleaned

    @field_validator("species_b")
    @classmethod
    def validate_species_b(cls, v: list[int] | None) -> list[int] | None:
        """Validate target species list."""
        if v is None:
            return v

        # Remove duplicates while preserving order
        cleaned = []
        seen = set()
        for species_id in v:
            if species_id > 0 and species_id not in seen:
                cleaned.append(species_id)
                seen.add(species_id)

        return cleaned if cleaned else None


class PPIEnrichmentRequest(BaseRequest):
    """Request model for protein-protein interaction enrichment."""

    identifiers: list[str] = Field(
        ...,
        min_length=2,  # Need at least 2 proteins for PPI enrichment
        max_length=MAX_IDENTIFIERS_PER_REQUEST,
        description="List of protein identifiers",
        examples=[["trpA", "trpB", "trpC", "trpE", "trpGD"]],
    )
    species: int | None = Field(
        None,
        ge=1,
        description="NCBI taxon identifier",
        examples=[511145],
    )
    required_score: float = Field(
        ConfidenceScore.MEDIUM,
        ge=MIN_CONFIDENCE_SCORE,
        le=MAX_CONFIDENCE_SCORE,
        description="Minimum confidence score (0.0-1.0)",
    )
    background_string_identifiers: list[str] | None = Field(
        None,
        description=(
            "Optional custom background proteome, given as STRING identifiers "
            "(e.g. '9606.ENSP00000269305'). MUST be a superset of the query "
            "identifiers; STRING rejects a background that omits any query protein."
        ),
        examples=[["9606.ENSP00000269305", "9606.ENSP00000350283"]],
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Validate protein identifiers."""
        if not v:
            msg = "At least two identifiers are required for PPI enrichment"
            raise ValueError(msg)

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        if len(cleaned) < 2:
            msg = "At least two unique identifiers are required for PPI enrichment"
            raise ValueError(msg)

        return cleaned

    @field_validator("background_string_identifiers")
    @classmethod
    def validate_background_identifiers(
        cls,
        v: list[str] | None,
    ) -> list[str] | None:
        """Validate background identifiers."""
        if v is None:
            return v

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        return cleaned if cleaned else None


class EnrichmentImageRequest(BaseRequest):
    """Request model for enrichment visualization."""

    identifiers: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_IDENTIFIERS_PER_REQUEST,
        description="List of protein identifiers",
        examples=[["ARRB1", "ARRB2", "EVC", "PTCH1", "SHH", "SMO"]],
    )
    species: int = Field(
        ...,
        ge=1,
        description="NCBI taxon identifier (required for enrichment)",
        examples=[9606],
    )
    category: EnrichmentCategory = Field(
        EnrichmentCategory.PROCESS,
        description="Enrichment category",
    )
    group_by_similarity: float | None = Field(
        None,
        ge=0.1,
        le=1.0,
        description="Threshold for grouping related terms (0.1-1.0)",
    )
    color_palette: str = Field(
        "mint_blue",
        pattern=r"^(mint_blue|lime_emerald|green_blue|peach_purple|straw_navy|yellow_pink)$",
        description="Color palette for FDR values",
    )
    number_of_terms_shown: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of terms to display",
    )
    x_axis: str = Field(
        "signal",
        pattern=r"^(signal|strength|FDR|gene_count)$",
        description="Variable for X-axis and term ordering",
    )
    image_format: ImageFormat = Field(
        ImageFormat.PNG,
        description="Image format: PNG, high-res PNG, or SVG",
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Validate protein identifiers."""
        if not v:
            msg = "At least one identifier is required"
            raise ValueError(msg)

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        if not cleaned:
            msg = "No valid identifiers provided"
            raise ValueError(msg)

        return cleaned


class LinkRequest(BaseRequest):
    """Request model for getting shareable STRING webpage links."""

    identifiers: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_IDENTIFIERS_PER_REQUEST,
        description="List of protein identifiers",
        examples=[["p53", "BRCA1", "MDM2"]],
    )
    species: int | None = Field(
        None,
        ge=1,
        description="NCBI taxon identifier",
        examples=[9606],
    )
    required_score: float = Field(
        ConfidenceScore.MEDIUM,
        ge=MIN_CONFIDENCE_SCORE,
        le=MAX_CONFIDENCE_SCORE,
        description="Minimum confidence score (0.0-1.0)",
    )
    network_type: NetworkType = Field(
        NetworkType.FUNCTIONAL,
        description="Network type: functional or physical",
    )
    network_flavor: NetworkFlavor = Field(
        NetworkFlavor.EVIDENCE,
        description="Network visualization style",
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Validate protein identifiers."""
        if not v:
            msg = "At least one identifier is required"
            raise ValueError(msg)

        cleaned = []
        seen = set()
        for identifier in v:
            identifier = identifier.strip()
            if identifier and identifier not in seen:
                cleaned.append(identifier)
                seen.add(identifier)

        if not cleaned:
            msg = "No valid identifiers provided"
            raise ValueError(msg)

        return cleaned
