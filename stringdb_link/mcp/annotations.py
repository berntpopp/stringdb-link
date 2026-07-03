"""Shared MCP tool annotations for stringdb-link.

Every stringdb-link tool is a read-only lookup/compute against the STRING
protein-protein interaction database (an externally-evolving, open-world data
source) — none mutate state — so ``READ_ONLY_OPEN_WORLD`` applies uniformly
across the tool surface. Mirrors the fleet exemplar (genereviews-link /
clingen-link ``mcp/annotations.py``).
"""

from __future__ import annotations

from mcp.types import ToolAnnotations

READ_ONLY_OPEN_WORLD = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
