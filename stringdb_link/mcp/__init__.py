"""MCP-surface adapters for stringdb-link.

Everything in this package operates *only* on the MCP tool boundary (the
FastMCP OpenAPI provider that ``FastMCP.from_fastapi`` builds from the FastAPI
app). The REST/FastAPI surface is never touched here — these modules reshape
what MCP callers see (the GeneFoundry Response-Envelope Standard v1 flat banner)
without changing any route behaviour.
"""

from __future__ import annotations
