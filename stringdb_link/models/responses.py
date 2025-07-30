"""Response models for StringDB-Link API.

This module defines Pydantic models for all API response types to ensure
type safety and proper serialization.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseResponse(BaseModel):
    """Base response model with common configuration."""

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        populate_by_name=True,
    )


class StringIdMapping(BaseResponse):
    """Response model for protein identifier mapping."""

    query_item: str | None = Field(
        None,
        alias="queryItem",
        description="Original input protein identifier",
        json_schema_extra={"example": "p53"},
    )
    query_index: int = Field(
        ...,
        alias="queryIndex",
        description="Position of the protein in the input list (0-based)",
        json_schema_extra={"example": 0},
    )
    string_id: str = Field(
        ...,
        alias="stringId",
        description="STRING database identifier",
        json_schema_extra={"example": "9606.ENSP00000269305"},
    )
    ncbi_taxon_id: int = Field(
        ...,
        alias="ncbiTaxonId",
        description="NCBI taxonomy identifier",
        json_schema_extra={"example": 9606},
    )
    taxon_name: str = Field(
        ...,
        alias="taxonName",
        description="Species name",
        json_schema_extra={"example": "Homo sapiens"},
    )
    preferred_name: str = Field(
        ...,
        alias="preferredName",
        description="Preferred protein name",
        json_schema_extra={"example": "TP53"},
    )
    annotation: str = Field(
        ...,
        description="Protein annotation/description",
        json_schema_extra={"example": "cellular tumor antigen p53"},
    )


class NetworkInteraction(BaseResponse):
    """Response model for protein-protein interactions."""

    string_id_a: str = Field(
        ...,
        alias="stringId_A",
        description="STRING identifier for protein A",
        json_schema_extra={"example": "9606.ENSP00000269305"},
    )
    string_id_b: str = Field(
        ...,
        alias="stringId_B",
        description="STRING identifier for protein B",
        json_schema_extra={"example": "9606.ENSP00000344843"},
    )
    preferred_name_a: str = Field(
        ...,
        alias="preferredName_A",
        description="Preferred name for protein A",
        json_schema_extra={"example": "TP53"},
    )
    preferred_name_b: str = Field(
        ...,
        alias="preferredName_B",
        description="Preferred name for protein B",
        json_schema_extra={"example": "MDM2"},
    )
    ncbi_taxon_id: int = Field(
        ...,
        alias="ncbiTaxonId",
        description="NCBI taxonomy identifier",
        json_schema_extra={"example": 9606},
    )
    score: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Combined confidence score (0-1000)",
        json_schema_extra={"example": 999},
    )
    nscore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Gene neighborhood score",
        json_schema_extra={"example": 0},
    )
    fscore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Gene fusion score",
        json_schema_extra={"example": 0},
    )
    pscore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Phylogenetic profile score",
        json_schema_extra={"example": 0},
    )
    ascore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Coexpression score",
        json_schema_extra={"example": 203},
    )
    escore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Experimental score",
        json_schema_extra={"example": 938},
    )
    dscore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Database score",
        json_schema_extra={"example": 999},
    )
    tscore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Textmining score",
        json_schema_extra={"example": 995},
    )


class InteractionPartner(BaseResponse):
    """Response model for interaction partners."""

    string_id_a: str = Field(
        ...,
        alias="stringId_A",
        description="STRING identifier for query protein",
        json_schema_extra={"example": "9606.ENSP00000269305"},
    )
    string_id_b: str = Field(
        ...,
        alias="stringId_B",
        description="STRING identifier for partner protein",
        json_schema_extra={"example": "9606.ENSP00000344843"},
    )
    preferred_name_a: str = Field(
        ...,
        alias="preferredName_A",
        description="Preferred name for query protein",
        json_schema_extra={"example": "TP53"},
    )
    preferred_name_b: str = Field(
        ...,
        alias="preferredName_B",
        description="Preferred name for partner protein",
        json_schema_extra={"example": "MDM2"},
    )
    ncbi_taxon_id: int = Field(
        ...,
        alias="ncbiTaxonId",
        description="NCBI taxonomy identifier",
        json_schema_extra={"example": 9606},
    )
    score: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Combined confidence score (0-1000)",
        json_schema_extra={"example": 999},
    )
    nscore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Gene neighborhood score",
        json_schema_extra={"example": 5},
    )
    fscore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Gene fusion score",
        json_schema_extra={"example": 5},
    )
    pscore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Phylogenetic profile score",
        json_schema_extra={"example": 5},
    )
    ascore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Coexpression score",
        json_schema_extra={"example": 999},
    )
    escore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Experimental score",
        json_schema_extra={"example": 999},
    )
    dscore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Database score",
        json_schema_extra={"example": 999},
    )
    tscore: int = Field(
        ...,
        ge=0,
        le=1000,
        description="Textmining score",
        json_schema_extra={"example": 999},
    )


class EnrichmentTerm(BaseResponse):
    """Response model for functional enrichment terms."""

    category: str = Field(
        ...,
        description="Term category (e.g., GO Process, KEGG pathways)",
        json_schema_extra={"example": "Process"},
    )
    term: str = Field(
        ...,
        description="Enriched term ID",
        json_schema_extra={"example": "GO:0006915"},
    )
    number_of_genes: int = Field(
        ...,
        ge=0,
        description="Number of genes in input with this term",
        json_schema_extra={"example": 5},
    )
    number_of_genes_in_background: int = Field(
        ...,
        ge=0,
        description="Total genes in background with this term",
        json_schema_extra={"example": 1234},
    )
    ncbi_taxon_id: int = Field(
        ...,
        description="NCBI taxonomy identifier",
        json_schema_extra={"example": 9606},
    )
    input_genes: list[str] = Field(
        ...,
        description="Gene names from input with this term",
        json_schema_extra={"example": ["TP53", "MDM2", "ATM"]},
    )
    preferred_names: list[str] = Field(
        ...,
        description="Preferred protein names",
        json_schema_extra={"example": ["TP53", "MDM2", "ATM"]},
    )
    p_value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Raw p-value",
        json_schema_extra={"example": 0.001234},
    )
    fdr: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="False Discovery Rate (adjusted p-value)",
        json_schema_extra={"example": 0.01234},
    )
    description: str = Field(
        ...,
        description="Description of the enriched term",
        json_schema_extra={"example": "apoptotic process"},
    )


class FunctionalAnnotation(BaseResponse):
    """Response model for functional annotations."""

    category: str = Field(
        ...,
        description="Annotation category",
        json_schema_extra={"example": "Process"},
    )
    term: str = Field(
        ...,
        description="Annotation term ID",
        json_schema_extra={"example": "GO:0006915"},
    )
    number_of_genes: int = Field(
        ...,
        ge=0,
        description="Number of input genes with this annotation",
        json_schema_extra={"example": 5},
    )
    ratio_in_set: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of proteins in input with this term",
        json_schema_extra={"example": 0.5},
    )
    ncbi_taxon_id: int = Field(
        ...,
        description="NCBI taxonomy identifier",
        json_schema_extra={"example": 9606},
    )
    input_genes: list[str] = Field(
        ...,
        description="Gene names from input with this annotation",
        json_schema_extra={"example": ["TP53"]},
    )
    preferred_names: list[str] = Field(
        ...,
        description="Preferred protein names",
        json_schema_extra={"example": ["TP53"]},
    )
    description: str = Field(
        ...,
        description="Description of the annotation term",
        json_schema_extra={"example": "apoptotic process"},
    )


class HomologyScore(BaseResponse):
    """Response model for protein homology scores."""

    ncbi_taxon_id_a: int = Field(
        ...,
        description="NCBI taxonomy ID for protein A",
        json_schema_extra={"example": 9606},
    )
    string_id_a: str = Field(
        ...,
        description="STRING identifier for protein A",
        json_schema_extra={"example": "9606.ENSP00000269305"},
    )
    ncbi_taxon_id_b: int = Field(
        ...,
        description="NCBI taxonomy ID for protein B",
        json_schema_extra={"example": 9606},
    )
    string_id_b: str = Field(
        ...,
        description="STRING identifier for protein B",
        json_schema_extra={"example": "9606.ENSP00000344843"},
    )
    bitscore: float = Field(
        ...,
        ge=0.0,
        description="Smith-Waterman alignment bit score",
        json_schema_extra={"example": 125.5},
    )


class PPIEnrichmentResult(BaseResponse):
    """Response model for PPI enrichment analysis."""

    number_of_nodes: int = Field(
        ...,
        ge=0,
        description="Number of proteins in the network",
        json_schema_extra={"example": 5},
    )
    number_of_edges: int = Field(
        ...,
        ge=0,
        description="Number of interactions in the network",
        json_schema_extra={"example": 5},
    )
    average_node_degree: float = Field(
        ...,
        ge=0.0,
        description="Mean degree of nodes in the network",
        json_schema_extra={"example": 3.2},
    )
    local_clustering_coefficient: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average local clustering coefficient",
        json_schema_extra={"example": 0.75},
    )
    expected_number_of_edges: float = Field(
        ...,
        ge=0.0,
        description="Expected number of edges based on node degrees",
        json_schema_extra={"example": 2.1},
    )
    p_value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Significance of network having more interactions than expected",
        json_schema_extra={"example": 0.001},
    )


class VersionInfo(BaseResponse):
    """Response model for STRING version information."""

    string_version: str = Field(
        ...,
        description="Current STRING database version",
        json_schema_extra={"example": "12.0"},
    )
    string_stable_address: str = Field(
        ...,
        description="Stable URL for this STRING version",
        json_schema_extra={"example": "https://version-12-0.string-db.org"},
    )


class LinkInfo(BaseResponse):
    """Response model for STRING webpage links."""

    url: str = Field(
        ...,
        description="URL to STRING webpage showing the network",
        json_schema_extra={"example": "https://version-12-0.string-db.org/cgi/network?networkId=abc123"},
    )


class ErrorResponse(BaseResponse):
    """Response model for API errors."""

    error: str = Field(
        ...,
        description="Error type",
        json_schema_extra={"example": "ValidationError"},
    )
    message: str = Field(
        ...,
        description="Error message",
        json_schema_extra={"example": "Invalid protein identifier"},
    )
    status_code: int | None = Field(
        None,
        description="HTTP status code",
        json_schema_extra={"example": 400},
    )
    details: dict[str, Any] | None = Field(
        None,
        description="Additional error details",
        json_schema_extra={"example": {"field": "identifiers", "value": ""}},
    )


class HealthResponse(BaseResponse):
    """Response model for health check."""

    status: str = Field(
        ...,
        description="Overall health status",
        json_schema_extra={"example": "healthy"},
    )
    version: str = Field(
        ...,
        description="StringDB-Link version",
        json_schema_extra={"example": "0.1.0"},
    )
    stringdb_api: str = Field(
        ...,
        description="StringDB API status",
        json_schema_extra={"example": "available"},
    )
    cache: str = Field(
        ...,
        description="Cache system status",
        json_schema_extra={"example": "enabled"},
    )
    uptime_seconds: float = Field(
        ...,
        ge=0.0,
        description="Server uptime in seconds",
        json_schema_extra={"example": 3600.5},
    )


class NetworkImage(BaseResponse):
    """Model for network image data."""

    image_data: bytes = Field(
        ...,
        description="Binary image data",
    )
    image_format: str = Field(
        ...,
        description="Image format (image, highres_image, svg)",
        json_schema_extra={"example": "image"},
    )
    content_type: str = Field(
        ...,
        description="MIME type of the image",
        json_schema_extra={"example": "image/png"},
    )


class NetworkImageResponse(BaseResponse):
    """Response model for network images."""

    image: NetworkImage = Field(
        ...,
        description="Network image data",
    )


# Response wrappers for lists
class StringIdMappingListResponse(BaseResponse):
    """Response wrapper for list of identifier mappings."""

    mappings: list[StringIdMapping] = Field(
        ...,
        description="List of protein identifier mappings",
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of mappings",
    )


class NetworkInteractionListResponse(BaseResponse):
    """Response wrapper for list of network interactions."""

    interactions: list[NetworkInteraction] = Field(
        ...,
        description="List of protein-protein interactions",
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of interactions",
    )


class InteractionPartnerListResponse(BaseResponse):
    """Response wrapper for list of interaction partners."""

    partners: list[InteractionPartner] = Field(
        ...,
        description="List of interaction partners",
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of partners",
    )


class EnrichmentTermListResponse(BaseResponse):
    """Response wrapper for list of enrichment terms."""

    terms: list[EnrichmentTerm] = Field(
        ...,
        description="List of enriched terms",
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of enriched terms",
    )


class FunctionalAnnotationListResponse(BaseResponse):
    """Response wrapper for list of functional annotations."""

    annotations: list[FunctionalAnnotation] = Field(
        ...,
        description="List of functional annotations",
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of annotations",
    )


class HomologyScoreListResponse(BaseResponse):
    """Response wrapper for list of homology scores."""

    scores: list[HomologyScore] = Field(
        ...,
        description="List of homology scores",
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of scores",
    )
