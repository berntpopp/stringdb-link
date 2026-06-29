"""StringDB-specific data models and enums.

This module defines enums, constants, and utility classes specific to the
STRING protein-protein interaction database.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class NetworkType(StrEnum):
    """Network types supported by STRING."""

    FUNCTIONAL = "functional"
    PHYSICAL = "physical"


class NetworkFlavor(StrEnum):
    """Network visualization styles supported by STRING."""

    EVIDENCE = "evidence"
    CONFIDENCE = "confidence"
    ACTIONS = "actions"


class OutputFormat(StrEnum):
    """Output formats supported by STRING API."""

    JSON = "json"
    TSV = "tsv"
    TSV_NO_HEADER = "tsv-no-header"
    XML = "xml"
    PSI_MI = "psi-mi"
    PSI_MI_TAB = "psi-mi-tab"
    IMAGE = "image"
    HIGHRES_IMAGE = "highres_image"
    SVG = "svg"


class ImageFormat(StrEnum):
    """Image formats for network visualization."""

    PNG = "image"
    PNG_HIGHRES = "highres_image"
    SVG = "svg"


class EnrichmentCategory(StrEnum):
    """Enrichment analysis categories."""

    PROCESS = "Process"  # Biological Process (Gene Ontology)
    FUNCTION = "Function"  # Molecular Function (Gene Ontology)
    COMPONENT = "Component"  # Cellular Component (Gene Ontology)
    KEYWORD = "Keyword"  # Annotated Keywords (UniProt)
    KEGG = "KEGG"  # KEGG Pathways
    RCTM = "RCTM"  # Reactome Pathways
    HPO = "HPO"  # Human Phenotype (Monarch)
    MPO = "MPO"  # The Mammalian Phenotype Ontology (Monarch)
    DPO = "DPO"  # Drosophila Phenotype (Monarch)
    WPO = "WPO"  # C. elegans Phenotype Ontology (Monarch)
    ZPO = "ZPO"  # Zebrafish Phenotype Ontology (Monarch)
    FYPO = "FYPO"  # Fission Yeast Phenotype Ontology (Monarch)
    PFAM = "Pfam"  # Protein Domains (Pfam)
    SMART = "SMART"  # Protein Domains (SMART)
    INTERPRO = "InterPro"  # Protein Domains and Features (InterPro)
    PMID = "PMID"  # Reference Publications (PubMed)
    NETWORK_NEIGHBOR_AL = "NetworkNeighborAL"  # Local Network Cluster (STRING)
    COMPARTMENTS = "COMPARTMENTS"  # Subcellular Localization (COMPARTMENTS)
    TISSUES = "TISSUES"  # Tissue Expression (TISSUES)
    DISEASES = "DISEASES"  # Disease-gene Associations (DISEASES)
    WIKI_PATHWAYS = "WikiPathways"  # WikiPathways


# Common species NCBI taxon IDs
class Species:
    """Common species NCBI taxon identifiers."""

    HUMAN: Final[int] = 9606
    MOUSE: Final[int] = 10090
    RAT: Final[int] = 10116
    DROSOPHILA: Final[int] = 7227
    CAENORHABDITIS_ELEGANS: Final[int] = 6239
    YEAST: Final[int] = 4932
    ARABIDOPSIS: Final[int] = 3702
    ESCHERICHIA_COLI: Final[int] = 511145
    ZEBRAFISH: Final[int] = 7955
    CHICKEN: Final[int] = 9031
    DOG: Final[int] = 9615
    PIG: Final[int] = 9823
    COW: Final[int] = 9913
    MACAQUE: Final[int] = 9544


# Confidence score thresholds (normalized 0.0-1.0)
class ConfidenceScore:
    """Standard confidence score thresholds (normalized 0.0-1.0)."""

    LOW: Final[float] = 0.15
    MEDIUM: Final[float] = 0.4
    HIGH: Final[float] = 0.7
    HIGHEST: Final[float] = 0.9


# API endpoint constants
class Endpoints:
    """STRING API endpoint constants."""

    GET_STRING_IDS: Final[str] = "get_string_ids"
    NETWORK: Final[str] = "network"
    INTERACTION_PARTNERS: Final[str] = "interaction_partners"
    ENRICHMENT: Final[str] = "enrichment"
    FUNCTIONAL_ANNOTATION: Final[str] = "functional_annotation"
    ENRICHMENT_FIGURE: Final[str] = "enrichmentfigure"
    PPI_ENRICHMENT: Final[str] = "ppi_enrichment"
    HOMOLOGY: Final[str] = "homology"
    HOMOLOGY_BEST: Final[str] = "homology_best"
    GET_LINK: Final[str] = "get_link"
    VERSION: Final[str] = "version"


# STRING identifier patterns
STRING_ID_PATTERN: Final[str] = r"^\d+\.[A-Za-z0-9_.-]+$"
UNIPROT_ID_PATTERN: Final[str] = (
    r"^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$"
)
ENSEMBL_PROTEIN_ID_PATTERN: Final[str] = r"^ENSP\d{11}$"
ENSEMBL_GENE_ID_PATTERN: Final[str] = r"^ENSG\d{11}$"

# Default limits
DEFAULT_INTERACTION_LIMIT: Final[int] = 10
MAX_IDENTIFIERS_PER_REQUEST: Final[int] = 100
MAX_ADDITIONAL_NODES: Final[int] = 50

# Score ranges (normalized 0.0-1.0)
MIN_CONFIDENCE_SCORE: Final[float] = 0.0
MAX_CONFIDENCE_SCORE: Final[float] = 1.0

# Cache TTL defaults (in seconds)
DEFAULT_CACHE_TTL: Final[int] = 3600
IDENTIFIER_CACHE_TTL: Final[int] = 86400  # 24 hours
NETWORK_CACHE_TTL: Final[int] = 43200  # 12 hours
ENRICHMENT_CACHE_TTL: Final[int] = 21600  # 6 hours
IMAGE_CACHE_TTL: Final[int] = 7200  # 2 hours
