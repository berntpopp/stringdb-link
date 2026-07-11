"""Unit contract for the caller-visible error-message sanitize primitive.

``sanitize_message`` strips the fence's forbidden control/zero-width/bidi/NUL
code points from every caller-visible message/error string and length-caps it,
so a hostile upstream (or a caller-influenced 4xx/5xx body) can never smuggle
those code points into an MCP error frame.
"""

from __future__ import annotations

from stringdb_link.mcp.untrusted_content import (
    MAX_MESSAGE_CHARS,
    sanitize_message,
)


def test_sanitize_removes_forbidden_code_points() -> None:
    dirty = "boom\x00‍﻿‮ end"
    clean = sanitize_message(dirty)
    assert "\x00" not in clean  # NUL
    assert "‍" not in clean  # zero-width joiner
    assert "﻿" not in clean  # BOM
    assert "‮" not in clean  # RTL override
    assert clean == "boom end"


def test_sanitize_preserves_ordinary_prose() -> None:
    prose = "STRING API error: 400 (invalid species)"
    assert sanitize_message(prose) == prose


def test_sanitize_preserves_tabs_newlines_scientific_symbols() -> None:
    # The fence keeps tabs, newlines and scientific symbols (they are not in the
    # forbidden set); sanitize_message shares that code-point set.
    text = "line1\n\tcol\u0394G = \u22121.2"
    assert sanitize_message(text) == text


def test_sanitize_length_caps() -> None:
    capped = sanitize_message("x" * 1000)
    assert len(capped) == MAX_MESSAGE_CHARS
    assert MAX_MESSAGE_CHARS == 280
