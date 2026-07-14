# Architecture

`stringdb-link` is one FastAPI application with two faces: a REST API and an MCP server. The
MCP surface is **generated from the REST routes**, which is why the two never drift apart.

## Layout

```
stringdb_link/
├── api/
│   ├── client.py          # STRING HTTP client: throttling, retries, caching, redirect guard
│   ├── url_guard.py       # Host allowlist for upstream URLs and redirects
│   ├── http_errors.py     # Upstream error → typed exception mapping
│   └── routes/            # FastAPI routes (identifiers, networks, enrichment,
│                          #   annotations, homology, images, health)
├── services/              # Business logic between routes and the client
├── models/                # Pydantic request/response models + STRING enums
├── mcp/                   # MCP-only concerns (see below)
├── config.py              # Settings facade
├── config_models.py       # Nested Pydantic settings models
├── exceptions.py          # Exception taxonomy
└── logging_config.py      # Structured logging (structlog)
```

Built on FastAPI, FastMCP, Pydantic v2 and httpx. Per `AGENTS.md`, Python modules are capped
at 600 lines; the four grandfathered files are listed in `.loc-allowlist` and may shrink but
not grow.

## REST → MCP generation

`create_mcp_app()` (`app.py`) builds the MCP server with `FastMCP.from_fastapi(...)`. Tool
names are taken **verbatim from each route's `operation_id`** — so a route's `operation_id`
*is* its MCP tool name, and adding a route can silently add a tool. Two guards exist:

- `tests/unit/test_tool_names.py` — every registered tool must be unprefixed snake_case,
  ≤ 50 chars, and start with a canonical verb (Tool-Naming Standard v1.1).
- `tests/unit/test_readme_tools.py` — the README's Tools table must equal the registered
  tool set exactly.

Not every route becomes a tool. `RouteMap` exclusions in `create_mcp_app()` keep the MCP
surface curated:

| Excluded | Why |
|----------|-----|
| `/health`, `/api/health*`, `/api/version`, `/`, `/docs`, `/redoc`, `/openapi.json` | Operational, not domain surface. |
| Single-identifier GET convenience routes (`/api/identifiers/resolve/{id}`, `/api/networks/interactions/{id}`, `/api/networks/partners/{id}`) | Duplicate the list-based POST tools. |
| Raw bulk-download routes (`/api/homology/*/download`) | Non-canonical verb, poor MCP ergonomics, redundant with the JSON tools. |

`mask_error_details=True` keeps internal exception text out of MCP error responses.

## MCP hardening layers (`stringdb_link/mcp/`)

| Module | Responsibility |
|--------|----------------|
| `envelope.py` | Response-Envelope Standard v1 — flat success banner / flat in-band error frame. |
| `error_passthrough.py` | Wraps every generated OpenAPI tool so its output is an envelope; reshapes the MCP surface only, never REST. |
| `untrusted_content.py` | Fences upstream free text so retrieved content reads as evidence, not instructions. |
| `notfound_guard.py` | Stops FastMCP-core from reflecting a caller's unknown tool name / resource URI back into responses and logs. |
| `annotations.py` | Tool annotations (read-only, open-world). |

## Federation contract

- `serverInfo.name` is **`stringdb-link`** — asserted by the conformance gate
  (`.github/workflows/conformance.yml`) and by the router's registry.
- `serverInfo.version` is single-sourced from installed package metadata.
- Leaf tool names are deliberately **unprefixed** (`get_interaction_partners`, not
  `stringdb_get_interaction_partners`). The canonical gateway namespace token is
  **`stringdb`**; `genefoundry-router` applies it at mount time, so tools surface as
  `stringdb_<tool>`. Self-prefixing would double-prefix at the gateway — the tool-name guard
  test rejects it.
- Transport is Streamable HTTP at `/mcp` (stateless JSON); stdio is available locally.

## HTTP REST surface

The REST API is a first-class surface, not a by-product. Interactive docs, once the server
is running:

- Swagger UI — `http://localhost:8000/docs`
- ReDoc — `http://localhost:8000/redoc`
- OpenAPI JSON — `http://localhost:8000/openapi.json`

Resolve identifiers:

```bash
curl -X POST "http://localhost:8000/api/identifiers/resolve" \
  -H "Content-Type: application/json" \
  -d '{"identifiers": ["p53", "BRCA1", "cdk2"], "species": 9606, "echo_query": true}'
```

Get interactions:

```bash
curl -X POST "http://localhost:8000/api/networks/interactions" \
  -H "Content-Type: application/json" \
  -d '{"identifiers": ["TP53", "MDM2", "ATM"], "species": 9606,
       "required_score": 0.4, "network_type": "functional"}'
```

`required_score` is a **normalized confidence in `0.0`–`1.0`** (default `0.4` = STRING's
"medium" threshold), not STRING's raw 0–1000 integer; the client rescales it upstream.

Functional enrichment:

```bash
curl -X POST "http://localhost:8000/api/enrichment/functional" \
  -H "Content-Type: application/json" \
  -d '{"identifiers": ["TP53", "MDM2", "ATM", "CHEK2", "BRCA1"], "species": 9606}'
```

## Domain vocabulary

| Concept | Values |
|---------|--------|
| `species` | NCBI taxon ID (`9606` = human). |
| `network_type` | `functional`, `physical`. |
| Image format | PNG (`image`), high-resolution PNG (`highres_image`), `svg`. |
| Output format | `json`, `tsv`, `tsv-no-header`, `xml`, `psi-mi`, `psi-mi-tab`. |

Upstream endpoints, caching TTLs and rate-limit etiquette: [`data.md`](data.md).
