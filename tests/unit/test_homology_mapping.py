"""Unit tests for the STRING homology record transform.

These tests cover the previously-untested success path: mapping raw STRING
camelCase homology rows onto the snake_case ``HomologyScore`` model. STRING's
``/api/.../homology`` and ``/homology_best`` endpoints return camelCase keys
(``ncbiTaxonId_A`` / ``stringId_A`` / ``ncbiTaxonId_B`` / ``stringId_B`` /
``bitscore``) while the model uses snake_case fields with no aliases, so the raw
row must be reshaped before construction.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from stringdb_link.api.routes.homology import (
    STRING_HOMOLOGY_FIELD_MAP,
    map_homology_record,
)
from stringdb_link.models.responses import HomologyScore

# A realistic STRING /api/json/homology row (bitscore is a string here).
STRING_HOMOLOGY_ROW = {
    "ncbiTaxonId_A": 9606,
    "stringId_A": "9606.ENSP00000269305",
    "ncbiTaxonId_B": 9606,
    "stringId_B": "9606.ENSP00000269305",
    "bitscore": "815.8",
}

# A realistic STRING /api/json/homology_best row (cross-species, numeric bitscore).
STRING_HOMOLOGY_BEST_ROW = {
    "ncbiTaxonId_A": 9606,
    "stringId_A": "9606.ENSP00000269305",
    "ncbiTaxonId_B": 10090,
    "stringId_B": "10090.ENSMUSP00000104298",
    "bitscore": 598.2,
}


def test_map_homology_record_maps_camelcase_to_model():
    """The transform reshapes camelCase keys onto snake_case model fields."""
    score = map_homology_record(STRING_HOMOLOGY_ROW)

    assert isinstance(score, HomologyScore)
    assert score.ncbi_taxon_id_a == 9606
    assert score.string_id_a == "9606.ENSP00000269305"
    assert score.ncbi_taxon_id_b == 9606
    assert score.string_id_b == "9606.ENSP00000269305"
    # bitscore string is coerced to float by the model.
    assert score.bitscore == pytest.approx(815.8)


def test_map_homology_record_cross_species_best_hit():
    """The transform preserves the _A/_B suffix convention across species."""
    score = map_homology_record(STRING_HOMOLOGY_BEST_ROW)

    assert score.ncbi_taxon_id_a == 9606
    assert score.ncbi_taxon_id_b == 10090
    assert score.string_id_a == "9606.ENSP00000269305"
    assert score.string_id_b == "10090.ENSMUSP00000104298"
    assert score.bitscore == pytest.approx(598.2)


def test_field_map_covers_every_model_field():
    """Every required HomologyScore field has exactly one STRING source key."""
    model_fields = set(HomologyScore.model_fields)
    mapped_fields = set(STRING_HOMOLOGY_FIELD_MAP.values())
    assert model_fields == mapped_fields


def test_raw_camelcase_row_fails_without_transform():
    """Document the bug: the raw STRING row cannot build the model directly."""
    with pytest.raises(ValidationError):
        HomologyScore(**STRING_HOMOLOGY_ROW)
