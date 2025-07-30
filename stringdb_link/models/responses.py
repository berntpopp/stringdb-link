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
        example="p53",
    )
    query_index: int = Field(
        ...,
        alias="queryIndex",
        description="Position of the protein in the input list (0-based)",
        example=0,
    )
    string_id: str = Field(
        ...,
        alias="stringId",
        description="STRING database identifier",
        example="9606.ENSP00000269305",
    )
    ncbi_taxon_id: int = Field(
        ...,
        alias="ncbiTaxonId",
        description="NCBI taxonomy identifier",
        example=9606,
    )
    taxon_name: str = Field(
        ...,
        alias="taxonName",
        description="Species name",
        example="Homo sapiens",
    )
    preferred_name: str = Field(
        ...,
        alias="preferredName",
        description="Preferred protein name",
        example="TP53",
    )
    annotation: str = Field(
        ...,
        description="Protein annotation/description",
        example="cellular tumor antigen p53",
    )


class NetworkInteraction(BaseResponse):
    """Response model for protein-protein interactions."""

    string_id_a: str = Field(
        ...,
        alias="stringId_A",
        description="STRING identifier for protein A",
        example="9606.ENSP00000269305",
    )
    string_id_b: str = Field(
        ...,
        alias="stringId_B",
        description="STRING identifier for protein B",
        example="9606.ENSP00000344843",
    )
    preferred_name_a: str = Field(
        ...,
        alias="preferredName_A",
        description="Preferred name for protein A",
        example="TP53",
    )
    preferred_name_b: str = Field(
        ...,
        alias="preferredName_B",
        description="Preferred name for protein B",
        example="MDM2",
    )
    ncbi_taxon_id: int = Field(
        ...,
        alias="ncbiTaxonId",
        description="NCBI taxonomy identifier",
        example=9606,
    )
    score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Combined confidence score (0-1)",
        example=0.999,
    )
    nscore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Gene neighborhood score",
        example=0.0,
    )
    fscore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Gene fusion score",
        example=0.0,
    )
    pscore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Phylogenetic profile score",
        example=0.0,
    )
    ascore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Coexpression score",
        example=0.203,
    )
    escore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Experimental score",
        example=0.938,
    )
    dscore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Database score",
        example=0.999,
    )
    tscore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Textmining score",
        example=0.995,
    )


class InteractionPartner(BaseResponse):
    """Response model for interaction partners."""

    string_id_a: str = Field(
        ...,
        alias="stringId_A",
        description="STRING identifier for query protein",
        example="9606.ENSP00000269305",
    )
    string_id_b: str = Field(
        ...,
        alias="stringId_B",
        description="STRING identifier for partner protein",
        example="9606.ENSP00000344843",
    )
    preferred_name_a: str = Field(
        ...,
        alias="preferredName_A",
        description="Preferred name for query protein",
        example="TP53",
    )
    preferred_name_b: str = Field(
        ...,
        alias="preferredName_B",
        description="Preferred name for partner protein",
        example="MDM2",
    )
    ncbi_taxon_id: int = Field(
        ...,
        alias="ncbiTaxonId",
        description="NCBI taxonomy identifier",
        example=9606,
    )
    score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Combined confidence score (0-1000)",
        example=0.999,
    )
    nscore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Gene neighborhood score",
        example=5,
    )
    fscore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Gene fusion score",
        example=5,
    )
    pscore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Phylogenetic profile score",
        example=5,
    )
    ascore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Coexpression score",
        example=0.999,
    )
    escore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Experimental score",
        example=0.999,
    )
    dscore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Database score",
        example=0.999,
    )
    tscore: float = Field(
        ...,
        ge=0,
        le=1,
        description="Textmining score",
        example=0.999,
    )


class EnrichmentTerm(BaseResponse):
    """Response model for functional enrichment terms."""

    category: str = Field(
        ...,
        description="Term category (e.g., GO Process, KEGG pathways)",
        example="Process",
    )
    term: str = Field(
        ...,
        description="Enriched term ID",
        example="GO:0006915",
    )
    number_of_genes: int = Field(
        ...,
        ge=0,
        description="Number of genes in input with this term",
        example=5,
    )
    number_of_genes_in_background: int = Field(
        ...,
        ge=0,
        description="Total genes in background with this term",
        example=1234,
    )
    ncbi_taxon_id: int = Field(
        ...,
        description="NCBI taxonomy identifier",
        example=9606,
    )
    input_genes: list[str] = Field(
        ...,
        description="Gene names from input with this term",
        example=["TP53", "MDM2", "ATM"],
    )
    preferred_names: list[str] = Field(
        ...,
        description="Preferred protein names",
        example=["TP53", "MDM2", "ATM"],
    )
    p_value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Raw p-value",
        example=0.001234,
    )
    fdr: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="False Discovery Rate (adjusted p-value)",
        example=0.01234,
    )
    description: str = Field(
        ...,
        description="Description of the enriched term",
        example="apoptotic process",
    )


class FunctionalAnnotation(BaseResponse):
    """Response model for functional annotations."""

    category: str = Field(
        ...,
        description="Annotation category",
        example="Process",
    )
    term: str = Field(
        ...,
        description="Annotation term ID",
        example="GO:0006915",
    )
    number_of_genes: int = Field(
        ...,
        ge=0,
        description="Number of input genes with this annotation",
        example=5,
    )
    ratio_in_set: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of proteins in input with this term",
        example=0.5,
    )
    ncbi_taxon_id: int = Field(
        ...,
        description="NCBI taxonomy identifier",
        example=9606,
    )
    input_genes: list[str] = Field(
        ...,
        description="Gene names from input with this annotation",
        example=["TP53"],
    )
    preferred_names: list[str] = Field(
        ...,
        description="Preferred protein names",
        example=["TP53"],
    )
    description: str = Field(
        ...,
        description="Description of the annotation term",
        example="apoptotic process",
    )


class HomologyScore(BaseResponse):
    """Response model for protein homology scores."""

    ncbi_taxon_id_a: int = Field(
        ...,
        description="NCBI taxonomy ID for protein A",
        example=9606,
    )
    string_id_a: str = Field(
        ...,
        description="STRING identifier for protein A",
        example="9606.ENSP00000269305",
    )
    ncbi_taxon_id_b: int = Field(
        ...,
        description="NCBI taxonomy ID for protein B",
        example=9606,
    )
    string_id_b: str = Field(
        ...,
        description="STRING identifier for protein B",
        example="9606.ENSP00000344843",
    )
    bitscore: float = Field(
        ...,
        ge=0.0,
        description="Smith-Waterman alignment bit score",
        example=125.5,
    )


class PPIEnrichmentResult(BaseResponse):
    """Response model for PPI enrichment analysis."""

    number_of_nodes: int = Field(
        ...,
        ge=0,
        description="Number of proteins in the network",
        example=5,
    )
    number_of_edges: int = Field(
        ...,
        ge=0,
        description="Number of interactions in the network",
        example=5,
    )
    average_node_degree: float = Field(
        ...,
        ge=0.0,
        description="Mean degree of nodes in the network",
        example=3.2,
    )
    local_clustering_coefficient: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average local clustering coefficient",
        example=0.75,
    )
    expected_number_of_edges: float = Field(
        ...,
        ge=0.0,
        description="Expected number of edges based on node degrees",
        example=2.1,
    )
    p_value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Significance of network having more interactions than expected",
        example=0.001,
    )


class VersionInfo(BaseResponse):
    """Response model for STRING version information."""

    string_version: str = Field(
        ...,
        description="Current STRING database version",
        example="12.0",
    )
    string_stable_address: str = Field(
        ...,
        description="Stable URL for this STRING version",
        example="https://version-12-0.string-db.org",
    )


class LinkInfo(BaseResponse):
    """Response model for STRING webpage links."""

    url: str = Field(
        ...,
        description="URL to STRING webpage showing the network",
        example="https://version-12-0.string-db.org/cgi/network?networkId=abc123",
    )


class ErrorResponse(BaseResponse):
    """Response model for API errors."""

    error: str = Field(
        ...,
        description="Error type",
        example="ValidationError",
    )
    message: str = Field(
        ...,
        description="Error message",
        example="Invalid protein identifier",
    )
    status_code: int | None = Field(
        None,
        description="HTTP status code",
        example=0.999,
    )
    details: dict[str, Any] | None = Field(
        None,
        description="Additional error details",
        example={"field": "identifiers", "value": ""},
    )


class HealthResponse(BaseResponse):
    """Response model for health check."""

    status: str = Field(
        ...,
        description="Overall health status",
        example="healthy",
    )
    version: str = Field(
        ...,
        description="StringDB-Link version",
        example="0.1.0",
    )
    stringdb_api: str = Field(
        ...,
        description="StringDB API status",
        example="available",
    )
    cache: str = Field(
        ...,
        description="Cache system status",
        example="enabled",
    )
    uptime_seconds: float = Field(
        ...,
        ge=0.0,
        description="Server uptime in seconds",
        example=3600.5,
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
        example="image",
    )
    content_type: str = Field(
        ...,
        description="MIME type of the image",
        example="image/png",
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
