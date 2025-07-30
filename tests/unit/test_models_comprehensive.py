"""Comprehensive tests for models beyond basic functionality."""


from stringdb_link.models.requests import (
    EnrichmentRequest,
    IdentifierRequest,
    NetworkRequest,
)
from stringdb_link.models.responses import (
    EnrichmentTerm,
    ErrorResponse,
    HealthResponse,
    NetworkInteraction,
    StringIdMapping,
)
from stringdb_link.models.stringdb import Species


class TestAdvancedRequestValidation:
    """Test advanced request model validation scenarios."""

    def test_identifier_request_large_list(self):
        """Test identifier request with large identifier list."""
        # Test with many identifiers
        identifiers = [f"protein_{i}" for i in range(100)]
        request = IdentifierRequest(identifiers=identifiers)
        assert len(request.identifiers) == 100

    def test_identifier_request_unicode_identifiers(self):
        """Test identifier request with unicode characters."""
        request = IdentifierRequest(identifiers=["protein_α", "protein_β", "protein_π"])
        assert "protein_α" in request.identifiers
        assert "protein_β" in request.identifiers
        assert "protein_π" in request.identifiers

    def test_identifier_request_special_characters(self):
        """Test identifier request with special characters."""
        identifiers = ["protein-1", "protein_2", "protein.3", "protein@4"]
        request = IdentifierRequest(identifiers=identifiers)
        assert len(request.identifiers) == 4

    def test_identifier_request_case_sensitivity(self):
        """Test identifier request case sensitivity."""
        request = IdentifierRequest(identifiers=["p53", "P53", "tp53", "TP53"])
        # Should preserve case and not deduplicate different cases
        assert len(request.identifiers) == 4

    def test_identifier_request_mixed_whitespace(self):
        """Test identifier request with mixed whitespace."""
        request = IdentifierRequest(identifiers=["  p53  ", "\tp21\n", " BRCA1 ", "MDM2"])
        # Should clean whitespace but preserve all identifiers
        expected = ["p53", "p21", "BRCA1", "MDM2"]
        assert request.identifiers == expected

    def test_network_request_edge_scores(self):
        """Test network request with edge case scores."""
        # Test minimum score
        request = NetworkRequest(identifiers=["p53"], required_score=0)
        assert request.required_score == 0

        # Test maximum score
        request = NetworkRequest(identifiers=["p53"], required_score=1000)
        assert request.required_score == 1000

    def test_network_request_all_network_types(self):
        """Test network request with all network types."""
        network_types = ["functional", "physical"]

        for network_type in network_types:
            request = NetworkRequest(identifiers=["p53"], network_type=network_type)
            assert request.network_type == network_type

    def test_network_request_large_add_nodes(self):
        """Test network request with large add_nodes value."""
        request = NetworkRequest(identifiers=["p53"], add_nodes=50)
        assert request.add_nodes == 50

    def test_enrichment_request_large_background(self):
        """Test enrichment request with large background set."""
        background = [f"9606.ENSP{i:011d}" for i in range(1000)]
        request = EnrichmentRequest(
            identifiers=["p53", "BRCA1"], background_string_identifiers=background
        )
        assert len(request.background_string_identifiers) == 1000

    def test_enrichment_request_empty_background(self):
        """Test enrichment request with empty background."""
        request = EnrichmentRequest(identifiers=["p53", "BRCA1"], background_string_identifiers=[])
        assert request.background_string_identifiers is None


class TestResponseModelEdgeCases:
    """Test response model edge cases."""

    def test_string_id_mapping_null_query_item(self):
        """Test StringIdMapping with null query item."""
        mapping = StringIdMapping(
            query_item=None,
            query_index=0,
            string_id="9606.ENSP00000269305",
            ncbi_taxon_id=9606,
            taxon_name="Homo sapiens",
            preferred_name="TP53",
            annotation="cellular tumor antigen p53",
        )
        assert mapping.query_item is None

    def test_string_id_mapping_empty_annotation(self):
        """Test StringIdMapping with empty annotation."""
        mapping = StringIdMapping(
            query_item="p53",
            query_index=0,
            string_id="9606.ENSP00000269305",
            ncbi_taxon_id=9606,
            taxon_name="Homo sapiens",
            preferred_name="TP53",
            annotation="",
        )
        assert mapping.annotation == ""

    def test_network_interaction_all_zero_scores(self):
        """Test NetworkInteraction with all zero scores."""
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
        assert interaction.nscore == 0

    def test_network_interaction_max_scores(self):
        """Test NetworkInteraction with maximum scores."""
        interaction = NetworkInteraction(
            string_id_a="9606.ENSP00000269305",
            string_id_b="9606.ENSP00000344843",
            preferred_name_a="TP53",
            preferred_name_b="MDM2",
            ncbi_taxon_id=9606,
            score=1000,
            nscore=1000,
            fscore=1000,
            pscore=1000,
            ascore=1000,
            escore=1000,
            dscore=1000,
            tscore=1000,
        )
        assert all(
            score == 1000
            for score in [
                interaction.score,
                interaction.nscore,
                interaction.fscore,
                interaction.pscore,
                interaction.ascore,
                interaction.escore,
                interaction.dscore,
                interaction.tscore,
            ]
        )

    def test_enrichment_term_extreme_p_values(self):
        """Test EnrichmentTerm with extreme p-values."""
        # Test very small p-value
        term = EnrichmentTerm(
            category="Process",
            term="GO:0006915",
            number_of_genes=1,
            number_of_genes_in_background=1000,
            ncbi_taxon_id=9606,
            input_genes=["TP53"],
            preferred_names=["TP53"],
            p_value=1e-10,
            fdr=1e-8,
            description="apoptotic process",
        )
        assert term.p_value == 1e-10
        assert term.fdr == 1e-8

        # Test p-value of 1.0
        term = EnrichmentTerm(
            category="Process",
            term="GO:0000000",
            number_of_genes=1000,
            number_of_genes_in_background=1000,
            ncbi_taxon_id=9606,
            input_genes=["RANDOM"],
            preferred_names=["RANDOM"],
            p_value=1.0,
            fdr=1.0,
            description="random process",
        )
        assert term.p_value == 1.0
        assert term.fdr == 1.0

    def test_enrichment_term_large_gene_lists(self):
        """Test EnrichmentTerm with large gene lists."""
        genes = [f"GENE_{i}" for i in range(100)]
        term = EnrichmentTerm(
            category="Process",
            term="GO:0006915",
            number_of_genes=100,
            number_of_genes_in_background=10000,
            ncbi_taxon_id=9606,
            input_genes=genes,
            preferred_names=genes,
            p_value=0.001,
            fdr=0.01,
            description="large gene set process",
        )
        assert len(term.input_genes) == 100
        assert len(term.preferred_names) == 100

    def test_error_response_comprehensive(self):
        """Test ErrorResponse with various configurations."""
        # Basic error
        error = ErrorResponse(error="ValidationError", message="Invalid input")
        assert error.error == "ValidationError"
        assert error.message == "Invalid input"
        assert error.status_code is None
        assert error.details is None

        # Error with status code
        error = ErrorResponse(error="StringDBAPIError", message="Server error", status_code=500)
        assert error.status_code == 500

        # Error with details
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid field",
            details={"field": "identifiers", "value": ""},
        )
        assert error.details["field"] == "identifiers"

    def test_health_response_all_states(self):
        """Test HealthResponse with different health states."""
        # Healthy state
        health = HealthResponse(
            status="healthy",
            version="0.1.0",
            stringdb_api="available",
            cache="enabled",
            uptime_seconds=3600.0,
        )
        assert health.status == "healthy"
        assert health.stringdb_api == "available"
        assert health.cache == "enabled"

        # Unhealthy state
        health = HealthResponse(
            status="unhealthy",
            version="0.1.0",
            stringdb_api="unavailable",
            cache="disabled",
            uptime_seconds=60.0,
        )
        assert health.status == "unhealthy"
        assert health.stringdb_api == "unavailable"
        assert health.cache == "disabled"

        # Degraded state
        health = HealthResponse(
            status="degraded",
            version="0.1.0",
            stringdb_api="slow",
            cache="partial",
            uptime_seconds=1800.0,
        )
        assert health.status == "degraded"
        assert health.stringdb_api == "slow"
        assert health.cache == "partial"


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_request_model_dict_roundtrip(self):
        """Test request models can roundtrip through dict."""
        original = IdentifierRequest(
            identifiers=["p53", "BRCA1"], species=Species.HUMAN, echo_query=True
        )

        # Convert to dict and back
        data = original.model_dump()
        reconstructed = IdentifierRequest(**data)

        assert reconstructed.identifiers == original.identifiers
        assert reconstructed.species == original.species
        assert reconstructed.echo_query == original.echo_query

    def test_response_model_json_roundtrip(self):
        """Test response models can roundtrip through JSON."""
        original = NetworkInteraction(
            string_id_a="9606.ENSP00000269305",
            string_id_b="9606.ENSP00000344843",
            preferred_name_a="TP53",
            preferred_name_b="MDM2",
            ncbi_taxon_id=9606,
            score=999,
            nscore=0,
            fscore=0,
            pscore=0,
            ascore=203,
            escore=938,
            dscore=999,
            tscore=995,
        )

        # Convert to JSON and back
        json_data = original.model_dump_json()
        reconstructed = NetworkInteraction.model_validate_json(json_data)

        assert reconstructed.string_id_a == original.string_id_a
        assert reconstructed.string_id_b == original.string_id_b
        assert reconstructed.score == original.score

    def test_model_aliases_work(self):
        """Test that model field aliases work correctly."""
        # Test input with aliases
        data = {
            "queryItem": "p53",
            "queryIndex": 0,
            "stringId": "9606.ENSP00000269305",
            "ncbiTaxonId": 9606,
            "taxonName": "Homo sapiens",
            "preferredName": "TP53",
            "annotation": "cellular tumor antigen p53",
        }

        mapping = StringIdMapping(**data)
        assert mapping.query_item == "p53"
        assert mapping.string_id == "9606.ENSP00000269305"
        assert mapping.ncbi_taxon_id == 9606


class TestModelValidationEdgeCases:
    """Test model validation edge cases."""

    def test_species_validation_edge_cases(self):
        """Test species validation with edge cases."""
        # Test with various valid species
        valid_species = [9606, 10090, 4932, 83333, 227321]

        for species in valid_species:
            request = IdentifierRequest(identifiers=["test"], species=species)
            assert request.species == species

    def test_score_validation_boundaries(self):
        """Test score validation at boundaries."""
        # Test all score fields at boundaries
        score_fields = {
            "score": 0.500,
            "nscore": 0.0,
            "fscore": 1.0,
            "pscore": 0.250,
            "ascore": 0.750,
            "escore": 0.333,
            "dscore": 0.666,
            "tscore": 0.999,
        }

        interaction = NetworkInteraction(
            string_id_a="9606.ENSP00000269305",
            string_id_b="9606.ENSP00000344843",
            preferred_name_a="TP53",
            preferred_name_b="MDM2",
            ncbi_taxon_id=9606,
            **score_fields,
        )

        for field, expected_value in score_fields.items():
            assert getattr(interaction, field) == expected_value

    def test_probability_validation_boundaries(self):
        """Test probability field validation at boundaries."""
        # Test p_value and fdr at boundaries
        term = EnrichmentTerm(
            category="Process",
            term="GO:0006915",
            number_of_genes=1,
            number_of_genes_in_background=1000,
            ncbi_taxon_id=9606,
            input_genes=["TP53"],
            preferred_names=["TP53"],
            p_value=0.0,  # Minimum
            fdr=1.0,  # Maximum
            description="test process",
        )
        assert term.p_value == 0.0
        assert term.fdr == 1.0

    def test_string_field_edge_cases(self):
        """Test string field edge cases."""
        # Test with very long strings
        long_annotation = "A" * 1000
        mapping = StringIdMapping(
            query_item="test",
            query_index=0,
            string_id="9606.ENSP00000269305",
            ncbi_taxon_id=9606,
            taxon_name="Homo sapiens",
            preferred_name="TEST",
            annotation=long_annotation,
        )
        assert len(mapping.annotation) == 1000

        # Test with empty strings where allowed
        mapping = StringIdMapping(
            query_item="",
            query_index=0,
            string_id="9606.ENSP00000269305",
            ncbi_taxon_id=9606,
            taxon_name="",
            preferred_name="",
            annotation="",
        )
        assert mapping.query_item == ""
        assert mapping.taxon_name == ""
