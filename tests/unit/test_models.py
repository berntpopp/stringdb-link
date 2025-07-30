"""Tests for data models."""

from pydantic import ValidationError
import pytest

from stringdb_link.models.requests import (
    EnrichmentRequest,
    IdentifierRequest,
    NetworkRequest,
)
from stringdb_link.models.responses import (
    EnrichmentTerm,
    NetworkInteraction,
    StringIdMapping,
)
from stringdb_link.models.stringdb import NetworkType, Species


class TestRequestModels:
    """Test request model validation."""

    def test_identifier_request_valid(self):
        """Test valid identifier request."""
        request = IdentifierRequest(
            identifiers=["p53", "BRCA1"],
            species=Species.HUMAN,
            echo_query=True,
        )

        assert request.identifiers == ["p53", "BRCA1"]
        assert request.species == 9606
        assert request.echo_query is True

    def test_identifier_request_cleanup(self):
        """Test identifier cleanup."""
        request = IdentifierRequest(
            identifiers=["  p53  ", "", "BRCA1", "p53", "  "],
        )

        # Should remove empty strings, whitespace, and duplicates
        assert request.identifiers == ["p53", "BRCA1"]

    def test_identifier_request_empty(self):
        """Test empty identifier list validation."""
        with pytest.raises(ValidationError):
            IdentifierRequest(identifiers=[])

        with pytest.raises(ValidationError):
            IdentifierRequest(identifiers=["", "  ", ""])

    def test_network_request_valid(self):
        """Test valid network request."""
        request = NetworkRequest(
            identifiers=["TP53", "MDM2"],
            species=Species.HUMAN,
            required_score=400,
            network_type=NetworkType.FUNCTIONAL,
            add_nodes=10,
        )

        assert request.identifiers == ["TP53", "MDM2"]
        assert request.species == 9606
        assert request.required_score == 400
        assert request.network_type == NetworkType.FUNCTIONAL
        assert request.add_nodes == 10

    def test_network_request_score_validation(self):
        """Test confidence score validation."""
        # Valid scores
        request = NetworkRequest(
            identifiers=["TP53"],
            required_score=0,
        )
        assert request.required_score == 0

        request = NetworkRequest(
            identifiers=["TP53"],
            required_score=1000,
        )
        assert request.required_score == 1000

        # Invalid scores
        with pytest.raises(ValidationError):
            NetworkRequest(identifiers=["TP53"], required_score=-1)

        with pytest.raises(ValidationError):
            NetworkRequest(identifiers=["TP53"], required_score=1001)

    def test_enrichment_request_background(self):
        """Test enrichment request with background."""
        request = EnrichmentRequest(
            identifiers=["TP53", "MDM2"],
            species=Species.HUMAN,
            background_string_identifiers=[
                "9606.ENSP00000269305",
                "9606.ENSP00000344843",
            ],
        )

        assert len(request.background_string_identifiers) == 2


class TestResponseModels:
    """Test response model serialization."""

    def test_string_id_mapping(self):
        """Test StringIdMapping model."""
        mapping = StringIdMapping(
            query_item="p53",
            query_index=0,
            string_id="9606.ENSP00000269305",
            ncbi_taxon_id=9606,
            taxon_name="Homo sapiens",
            preferred_name="TP53",
            annotation="cellular tumor antigen p53",
        )

        assert mapping.query_item == "p53"
        assert mapping.string_id == "9606.ENSP00000269305"
        assert mapping.preferred_name == "TP53"

    def test_network_interaction(self):
        """Test NetworkInteraction model."""
        interaction = NetworkInteraction(
            string_id_a="9606.ENSP00000269305",
            string_id_b="9606.ENSP00000344843",
            preferred_name_a="TP53",
            preferred_name_b="MDM2",
            ncbi_taxon_id=9606,
            score=0.999,
            nscore=0.0,
            fscore=0.0,
            pscore=0.0,
            ascore=0.203,
            escore=0.938,
            dscore=0.999,
            tscore=0.995,
        )

        assert interaction.string_id_a == "9606.ENSP00000269305"
        assert interaction.preferred_name_a == "TP53"
        assert interaction.score == 0.999

    def test_enrichment_term(self):
        """Test EnrichmentTerm model."""
        term = EnrichmentTerm(
            category="Process",
            term="GO:0006915",
            number_of_genes=1,
            number_of_genes_in_background=1234,
            ncbi_taxon_id=9606,
            input_genes=["TP53"],
            preferred_names=["TP53"],
            p_value=0.001,
            fdr=0.01,
            description="apoptotic process",
        )

        assert term.category == "Process"
        assert term.term == "GO:0006915"
        assert term.p_value == 0.001
        assert term.fdr == 0.01
        assert "TP53" in term.input_genes

    def test_score_validation(self):
        """Test score field validation."""
        # Valid scores
        interaction = NetworkInteraction(
            string_id_a="9606.ENSP00000269305",
            string_id_b="9606.ENSP00000344843",
            preferred_name_a="TP53",
            preferred_name_b="MDM2",
            ncbi_taxon_id=9606,
            score=0,
            nscore=0,
            fscore=0,
            pscore=0,
            ascore=0,
            escore=0,
            dscore=0,
            tscore=0,
        )
        assert interaction.score == 0

        # Invalid scores
        with pytest.raises(ValidationError):
            NetworkInteraction(
                string_id_a="9606.ENSP00000269305",
                string_id_b="9606.ENSP00000344843",
                preferred_name_a="TP53",
                preferred_name_b="MDM2",
                ncbi_taxon_id=9606,
                score=-1,  # Invalid
                nscore=0,
                fscore=0,
                pscore=0,
                ascore=0,
                escore=0,
                dscore=0,
                tscore=0,
            )


class TestStringDBModels:
    """Test StringDB-specific models and constants."""

    def test_network_type_enum(self):
        """Test NetworkType enum."""
        assert NetworkType.FUNCTIONAL == "functional"
        assert NetworkType.PHYSICAL == "physical"

    def test_species_constants(self):
        """Test species constants."""
        assert Species.HUMAN == 9606
        assert Species.MOUSE == 10090
        assert Species.YEAST == 4932
