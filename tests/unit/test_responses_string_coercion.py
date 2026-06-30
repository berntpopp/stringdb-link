"""Coercion + bound-relaxation regressions for STRING response models."""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from stringdb_link.api.client import StringDBClient
from stringdb_link.models.responses import (
    EnrichmentTerm,
    FunctionalAnnotation,
    InteractionPartner,
    NetworkInteraction,
)


def _enrichment_record(input_genes, preferred_names):
    return {
        "category": "Process",
        "term": "GO:0000162",
        "number_of_genes": 5,
        "number_of_genes_in_background": 9,
        "ncbiTaxonId": 511145,
        "inputGenes": input_genes,
        "preferredNames": preferred_names,
        "p_value": 1.97e-13,
        "fdr": 6.18e-10,
        "description": "Tryptophan biosynthetic process",
    }


def test_enrichment_term_splits_comma_separated_strings():
    # STRING (non-v12 mirrors / older API) returns these as comma-separated strings.
    term = EnrichmentTerm(**_enrichment_record("trpA,trpB,trpC", "trpA,trpB,trpC"))
    assert term.input_genes == ["trpA", "trpB", "trpC"]
    assert term.preferred_names == ["trpA", "trpB", "trpC"]


def test_enrichment_term_passes_arrays_through():
    # Current public v12 API returns arrays; these must still parse unchanged.
    term = EnrichmentTerm(**_enrichment_record(["trpGD", "trpE"], ["trpD", "trpE"]))
    assert term.input_genes == ["trpGD", "trpE"]
    assert term.preferred_names == ["trpD", "trpE"]


def test_functional_annotation_splits_comma_separated_strings():
    annotation = FunctionalAnnotation(
        category="Process",
        term="GO:0006915",
        number_of_genes=1,
        ratio_in_set=0.5,
        ncbiTaxonId=9606,
        inputGenes="TP53,MDM2",
        preferredNames="TP53,MDM2",
        description="apoptotic process",
    )
    assert annotation.input_genes == ["TP53", "MDM2"]
    assert annotation.preferred_names == ["TP53", "MDM2"]


def test_enrichment_term_rejects_non_string_non_list():
    with pytest.raises(ValidationError):
        EnrichmentTerm(**_enrichment_record(123, ["x"]))


def _network_record(score):
    return {
        "stringId_A": "9606.ENSP00000269305",
        "stringId_B": "9606.ENSP00000275493",
        "preferredName_A": "TP53",
        "preferredName_B": "EGFR",
        "ncbiTaxonId": "9606",  # STRING returns this as a string; must coerce
        "score": score,
        "nscore": 0.0,
        "fscore": 0.0,
        "pscore": 0.0,
        "ascore": 0.0,
        "escore": 0.329,
        "dscore": 0.0,
        "tscore": 0.919,
    }


def test_network_interaction_accepts_score_above_one():
    interaction = NetworkInteraction(**_network_record(1.02))
    assert interaction.score == pytest.approx(1.02)
    assert interaction.ncbi_taxon_id == 9606


def test_interaction_partner_accepts_score_above_one():
    record = _network_record(1.05)
    partner = InteractionPartner(**record)
    assert partner.score == pytest.approx(1.05)


@pytest.mark.parametrize(
    "method_name",
    [
        "get_network_interactions",
        "get_interaction_partners",
        "get_network_image",
        "get_ppi_enrichment",
    ],
)
def test_required_score_docstring_uses_0_1000_scale(method_name):
    doc = inspect.getdoc(getattr(StringDBClient, method_name)) or ""
    assert "0-1000" in doc, f"{method_name} docstring should state the 0-1000 scale"
    assert "(0.0-1.0)" not in doc, f"{method_name} docstring still claims 0.0-1.0"
