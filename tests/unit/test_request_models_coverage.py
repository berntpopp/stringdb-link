"""Tests to improve coverage of request models."""

from pydantic import ValidationError
import pytest

from stringdb_link.models.requests import (
    AnnotationRequest,
    EnrichmentRequest,
    HomologyRequest,
    IdentifierRequest,
    ImageRequest,
    InteractionPartnersRequest,
    LinkRequest,
    NetworkRequest,
    PPIEnrichmentRequest,
)
from stringdb_link.models.stringdb import ImageFormat, NetworkFlavor, NetworkType


class TestRequestModelValidation:
    """Test request model validation logic."""

    def test_identifier_request_validation(self):
        """Test identifier request validation."""
        # Valid request
        request = IdentifierRequest(identifiers=["p53", "BRCA1"])
        assert len(request.identifiers) == 2
        assert request.species is None
        assert request.echo_query is False

    def test_identifier_request_empty_identifiers(self):
        """Test identifier request with empty identifiers fails."""
        with pytest.raises(ValidationError):
            IdentifierRequest(identifiers=[])

    def test_identifier_request_duplicate_removal(self):
        """Test duplicate identifier removal."""
        request = IdentifierRequest(identifiers=["p53", "p53", "BRCA1"])
        # Should remove duplicates
        assert len(set(request.identifiers)) == len(request.identifiers)

    def test_network_request_validation(self):
        """Test network request validation."""
        request = NetworkRequest(
            identifiers=["9606.ENSP00000269305"],
            required_score=700,
            network_type=NetworkType.FUNCTIONAL,
            add_nodes=10,
        )
        assert request.required_score == 700
        assert request.network_type == NetworkType.FUNCTIONAL
        assert request.add_nodes == 10

    def test_network_request_score_bounds(self):
        """Test network request score validation."""
        # Valid scores
        NetworkRequest(identifiers=["test"], required_score=0)
        NetworkRequest(identifiers=["test"], required_score=1000)

        # Invalid scores should fail
        with pytest.raises(ValidationError):
            NetworkRequest(identifiers=["test"], required_score=-1)

        with pytest.raises(ValidationError):
            NetworkRequest(identifiers=["test"], required_score=1001)

    def test_enrichment_request_validation(self):
        """Test enrichment request validation."""
        request = EnrichmentRequest(identifiers=["9606.ENSP00000269305"], species=9606)
        assert request.species == 9606
        assert request.background_string_identifiers is None

    def test_enrichment_request_with_background(self):
        """Test enrichment request with background identifiers."""
        background = ["9606.ENSP00000269305", "9606.ENSP00000348554"]
        request = EnrichmentRequest(
            identifiers=["9606.ENSP00000269305"], background_string_identifiers=background
        )
        assert request.background_string_identifiers == background

    def test_annotation_request_validation(self):
        """Test annotation request validation."""
        request = AnnotationRequest(identifiers=["9606.ENSP00000269305"])
        assert len(request.identifiers) == 1

    def test_image_request_validation(self):
        """Test image request validation."""
        request = ImageRequest(
            identifiers=["9606.ENSP00000269305"],
            network_flavor=NetworkFlavor.EVIDENCE,
            image_format=ImageFormat.PNG,
        )
        assert request.network_flavor == NetworkFlavor.EVIDENCE
        assert request.image_format == ImageFormat.PNG

    def test_image_request_defaults(self):
        """Test image request default values."""
        request = ImageRequest(identifiers=["test"])
        assert request.image_format == ImageFormat.PNG
        assert request.network_flavor == NetworkFlavor.EVIDENCE

    def test_homology_request_validation(self):
        """Test homology request validation."""
        request = HomologyRequest(identifiers=["9606.ENSP00000269305"], species=9606)
        assert request.species == 9606

    def test_link_request_validation(self):
        """Test link request validation."""
        request = LinkRequest(
            identifiers=["9606.ENSP00000269305", "9606.ENSP00000348554"],
            network_type=NetworkType.PHYSICAL,
        )
        assert request.network_type == NetworkType.PHYSICAL

    def test_interaction_partners_request_validation(self):
        """Test interaction partners request validation."""
        request = InteractionPartnersRequest(identifiers=["9606.ENSP00000269305"], limit=100)
        assert request.limit == 100

    def test_ppi_enrichment_request_validation(self):
        """Test PPI enrichment request validation."""
        request = PPIEnrichmentRequest(
            identifiers=["9606.ENSP00000269305", "9606.ENSP00000348554"], required_score=500
        )
        assert request.required_score == 500
        assert len(request.identifiers) == 2

    def test_request_string_representation(self):
        """Test request string representations."""
        request = IdentifierRequest(identifiers=["p53"])
        str_repr = str(request)
        assert "p53" in str_repr
        # Pydantic models don't include class name in __str__ by default
        assert "identifiers" in str_repr

    def test_request_model_copy(self):
        """Test request model copying."""
        original = NetworkRequest(identifiers=["test"], required_score=600)
        copied = original.model_copy()

        assert copied.identifiers == original.identifiers
        assert copied.required_score == original.required_score
        assert copied is not original

    def test_request_model_dict_export(self):
        """Test request model dictionary export."""
        request = IdentifierRequest(identifiers=["p53"], species=9606)
        data = request.model_dump()

        assert data["identifiers"] == ["p53"]
        assert data["species"] == 9606
        assert "echo_query" in data

    def test_network_type_enum_values(self):
        """Test NetworkType enum values."""
        assert NetworkType.FUNCTIONAL.value == "functional"
        assert NetworkType.PHYSICAL.value == "physical"

    def test_network_flavor_enum_values(self):
        """Test NetworkFlavor enum values."""
        assert NetworkFlavor.EVIDENCE.value == "evidence"
        assert NetworkFlavor.CONFIDENCE.value == "confidence"
        assert NetworkFlavor.ACTIONS.value == "actions"

    def test_image_format_enum_values(self):
        """Test ImageFormat enum values."""
        assert ImageFormat.PNG.value == "image"
        assert ImageFormat.SVG.value == "svg"

    def test_identifier_whitespace_handling(self):
        """Test identifier whitespace handling."""
        request = IdentifierRequest(identifiers=[" p53 ", "  BRCA1  "])
        # Should be trimmed
        assert all(not id.startswith(" ") and not id.endswith(" ") for id in request.identifiers)

    def test_species_validation(self):
        """Test species validation."""
        # Valid species
        IdentifierRequest(identifiers=["test"], species=9606)

        # Invalid species should fail
        with pytest.raises(ValidationError):
            IdentifierRequest(identifiers=["test"], species=-1)

    def test_limit_validation(self):
        """Test limit parameter validation."""
        # Valid limit
        InteractionPartnersRequest(identifiers=["test"], limit=50)

        # Invalid limits
        with pytest.raises(ValidationError):
            InteractionPartnersRequest(identifiers=["test"], limit=0)

        with pytest.raises(ValidationError):
            InteractionPartnersRequest(identifiers=["test"], limit=10001)

    def test_max_identifiers_validation(self):
        """Test maximum identifiers validation."""
        # Create list that exceeds maximum
        too_many_identifiers = [f"id_{i}" for i in range(101)]  # Assuming max is 100

        with pytest.raises(ValidationError):
            IdentifierRequest(identifiers=too_many_identifiers)

    def test_add_nodes_validation(self):
        """Test add_nodes parameter validation."""
        # Valid values
        NetworkRequest(identifiers=["test"], add_nodes=0)
        NetworkRequest(identifiers=["test"], add_nodes=50)

        # Invalid values
        with pytest.raises(ValidationError):
            NetworkRequest(identifiers=["test"], add_nodes=-1)

        with pytest.raises(ValidationError):
            NetworkRequest(identifiers=["test"], add_nodes=51)

    def test_background_identifiers_empty_list_becomes_none(self):
        """Test that empty background list becomes None."""
        request = EnrichmentRequest(identifiers=["test"], background_string_identifiers=[])
        # Empty list should be converted to None by validator
        assert request.background_string_identifiers is None
