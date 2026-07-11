"""Structural untrusted-text fencing contracts."""

from __future__ import annotations

import hashlib

import pytest

from stringdb_link.mcp.untrusted_content import (
    UntrustedTextLimitError,
    enforce_untrusted_text_limits,
    fence_untrusted_text,
)


def test_fence_normalizes_and_removes_forbidden_controls() -> None:
    raw = "Café\x00\u200d\u202e\nBRCA1"
    fenced = fence_untrusted_text(raw, source="stringdb", record_id="9606.ENSP00000269305")
    assert fenced.kind == "untrusted_text"
    assert fenced.text == "Café\nBRCA1"
    assert fenced.raw_sha256 == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert fenced.provenance.source == "stringdb"
    assert fenced.provenance.record_id == "9606.ENSP00000269305"


def test_fence_preserves_tabs_newlines_and_scientific_symbols() -> None:
    raw = "p.Gly12Asp\t\u0394G = \u22121.2 kcal/mol\r\n"
    assert fence_untrusted_text(raw, source="stringdb", record_id="GO:0006915").text == raw


def test_limits_reject_oversized_object() -> None:
    big = fence_untrusted_text("x" * 10, source="stringdb", record_id="GO:0006915")
    with pytest.raises(UntrustedTextLimitError):
        enforce_untrusted_text_limits([big], max_text_bytes=5)
