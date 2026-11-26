"""The vendored Response-Envelope v1.2 JSON Schema (berntpopp/genefoundry-envelope v1.2.0)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_FILE = Path(__file__).parent / "envelope-v1.2.schema.json"
SCHEMA = json.loads(SCHEMA_FILE.read_text())
PROVENANCE = ("source", "data_version", "retrieved_at")


def assert_data_envelope(envelope: dict[str, Any]) -> None:
    """A successful data result: schema-valid, with the three provenance fields non-empty."""
    assert envelope["success"] is True, envelope.get("message")
    jsonschema.validate(envelope, SCHEMA)
    for field in PROVENANCE:
        value = envelope["_meta"].get(field)
        assert isinstance(value, str) and value.strip(), f"_meta.{field}"
