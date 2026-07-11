# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [4.0.2] - 2026-07-11

### Security

- Guard the FastMCP-core not-found reflection surface (Response-Envelope
  Standard v1.1 §Error-message sanitation fast-follow). FastMCP core echoed the
  caller's own requested tool name / resource URI / prompt name (and any
  control/zero-width/bidi/NUL code points) back to the caller and to logs before
  backend middleware ran. A new `stringdb_link/mcp/notfound_guard.py` closes it
  with fixed, input-free messages built from constants: a tool-name preflight
  (unknown tool -> fixed `not_found` envelope, `isError=True`, no `_meta.tool`
  echo), an `on_read_resource` boundary, a protocol-handler backstop covering the
  unknown-tool return path and the unknown-prompt caller echo, and a
  validation-log scrub filter on the FastMCP/MCP-SDK loggers and their
  non-propagating handlers. Caller self-reflection surface; research use only.

## [4.0.1] - 2026-07-11

### Security

- Defense in depth: the MCP error-passthrough no longer echoes upstream/response
  error-body text (fixed status-keyed messages), caller-visible messages are
  sanitized of control/zero-width/bidi/NUL code points, and the client no longer
  reads/retains non-success response bodies. Research use only.

## [4.0.0] - 2026-07-11

### Security

- Adopt Response-Envelope Standard v1.1 untrusted-content fencing. Every
  externally sourced free-text field emitted by the MCP tool surface now
  arrives as the typed `untrusted_text` object (`kind`/`text`/`provenance`/
  `raw_sha256`) instead of a bare string, so hosts and the router treat
  upstream STRING prose as opaque data rather than instructions
  (`stringdb_link/mcp/untrusted_content.py`, `stringdb_link/mcp/envelope.py`).

### Changed (BREAKING)

- `resolve_protein_identifiers` (`/mappings/*/annotation`),
  `compute_functional_enrichment` (`/terms/*/description`), and
  `get_functional_annotations` (`/annotations/*/description`) now return the
  typed `untrusted_text` object for those fields instead of a plain string, at
  the MCP `structuredContent` boundary. Interaction and homology scores are
  unaffected (still numeric). The REST/OpenAPI surface
  (`stringdb_link/models/responses.py`) is unchanged — this reshape applies
  only to the MCP tool output, matching this repo's existing MCP-only
  envelope architecture.

## [3.0.0] - 2026-07-10

### Security

- Enforce exact configurable Host and Origin allowlists across every HTTP
  route, with safe loopback defaults, wildcard rejection, explicit production
  proxy hosts, and native FastMCP protection in depth. FastMCP is upgraded to
  3.4.4 while preserving REST-only and stdio behavior.

### Changed (BREAKING)

- Host and Origin admission is now default-deny outside the configured
  loopback values. Non-loopback and reverse-proxy deployments must list their
  exact public names in `ALLOWED_HOSTS` and browser origins, when used, in
  `ALLOWED_ORIGINS`.

## [2.0.3] - 2026-07-07

### Changed

- Release-version disambiguation. `origin/main` independently released a
  `2.0.2` (healthcheck fix, #19) while this security-remediation release also
  used `2.0.2`; the two were merged into a single superset commit. This `2.0.3`
  supersedes both so the tip release version is unambiguous. No functional
  change beyond the merged `2.0.2` contents (security logging redaction + CORS
  credentials-off + loopback compose + healthcheck `/api/health`).

## [2.0.2] - 2026-07-07

### Security

- **No caller identifiers/URLs/tracebacks in logs.** STRING identifiers are
  caller-supplied gene/protein lists that may be patient-derived (GDPR Art. 9).
  Several log call sites emitted them raw, along with the generated STRING URL
  (which embeds them in its query string) and full exception strings/tracebacks
  that interpolate the same free-text. Added a central `redact_sensitive_processor`
  (structlog) that digests a denylist of event-dict keys to a non-reversible
  `sha256:` prefix and drops structlog-rendered exception frames, plus a stdlib
  `RedactingFilter` that nulls `exc_info`/`stack_info` on every record (because
  `Logger.exception()` re-attaches the traceback after the processor chain runs).
  The network-link success log and link-route exception handlers now emit
  counts/`error_type` only. Regression guard: `tests/unit/test_logging_redaction.py`.
- **CORS credentials off by default + fail-closed guard.** `allow_credentials`
  now defaults to `False` (this backend is unauthenticated); the app factory
  raises at startup if credentials are ever combined with a wildcard origin.
- **Loopback-bound base compose.** The dev/local `docker-compose.yml` now
  publishes the host port on `127.0.0.1` so copying it to a server never exposes
  the unauthenticated backend on the public IP; production overlays keep
  `ports: !reset []` (expose-only behind the reverse proxy).

### Fixed

- **Container healthcheck false-red.** The Docker `HEALTHCHECK` curled
  `http://localhost:8000/api/health/` (trailing slash). The health route is
  registered as `/api/health` (no slash), and because the app is served as a
  FastMCP sub-app (`FastMCP.from_fastapi`), Starlette's trailing-slash redirect
  no longer fires — so `/api/health/` returns 404 (was 307). With `curl -f`
  (no `-L`) the 404 exited 22 and the container flapped to `unhealthy` despite
  the app and MCP endpoint serving fine. Point the healthcheck at the canonical
  `/api/health` across the `Dockerfile`, all three compose files, and the
  README. Fixes #18.

## [2.0.1] - 2026-07-03

### Fixed

- **Single-source versioning.** `__version__` now derives from installed package
  metadata (`importlib.metadata.version("stringdb-link")`) instead of a
  hardcoded string, so the version lives only in `pyproject.toml`
  `[project].version`.
- **MCP `serverInfo.version`.** The FastMCP server (`create_mcp_app`) now
  advertises the package version via `FastMCP.from_fastapi(..., version=__version__)`,
  which forwards to the underlying `FastMCP(version=...)`. Previously
  `initialize` leaked the FastMCP framework version (`3.3.1`) in
  `serverInfo.version`; `/health` was already correct. Added
  `tests/unit/test_version_single_source.py` as a regression guard.

## [2.0.0] - 2026-07-03

### Changed (BREAKING) — GeneFoundry Response-Envelope Standard v1

Adopted the [GeneFoundry Response-Envelope Standard v1](https://github.com/berntpopp/stringdb-link/issues).
Every MCP tool now returns the fleet-wide flat banner as `structuredContent`;
the **REST/FastAPI surface is unchanged**. This is a breaking change for MCP
consumers that parsed the previous bare payloads.

- **Success frame.** Collection tools (`resolve_protein_identifiers`,
  `search_protein_interactions`, `get_interaction_partners`,
  `compute_functional_enrichment`, `get_functional_annotations`,
  `get_protein_homology_scores`, `get_protein_homology_best_hits`) now return
  `{"success": true, "results": [...], "_meta": {...}}` — the former list key
  (`mappings`/`interactions`/`partners`/`terms`/`annotations`/`scores`) is
  promoted to top-level `results`, with `total_count` riding beside it.
  Single-item tools (`compute_ppi_enrichment`, `get_network_link`,
  `get_network_image`) nest their payload under `result`.
- **Error frame.** Route `HTTPException`s are converted at the MCP boundary into
  a flat, in-band error envelope `{"success": false, "error_code", "message",
  "retryable", "recovery_action", "_meta": {...}}` (closed error-code enum;
  status-driven classification — 400→`invalid_input`, 429→`rate_limited`,
  500→`internal_error`, 502/503/504→`upstream_unavailable`) instead of an opaque
  `ToolError` text blob. (FastMCP 3.3.1 offers no supported way to set wire-level
  `isError:true` alongside populated `structuredContent`, so — like the rest of
  the fleet — the in-band `success` flag is authoritative.)
- **Per-call disclaimer.** Every response (success *and* error) carries
  `_meta.unsafe_for_clinical_use: true` plus `tool`/`request_id`/`elapsed_ms`/
  `source`/`capabilities_version` provenance.
- **Annotations.** Every tool now declares `READ_ONLY_OPEN_WORLD` MCP
  annotations (read-only, non-destructive, idempotent, open-world).
- New `stringdb_link.mcp` package (`envelope.py`, `error_passthrough.py`,
  `annotations.py`); wired via `FastMCP.from_fastapi(..., mcp_component_fn=...)`.

### Security

- Bumped the transitive `joserfc` pin `1.6.7 → 1.7.2` (CVE-2026-49852 hygiene).

### Security (Container & Deployment Hardening Standard v1)

- Ported the router/gtex hardening wholesale into the prod and npm Compose
  overlays (`read_only` rootfs + tmpfs scratch, `cap_drop: ALL`,
  `no-new-privileges`, `init`, pids/mem/cpu limits; prod is now expose-only via
  `ports: !reset []`).
- Set `mask_error_details=True` on the FastMCP `from_fastapi` construction so
  internal exception text is not returned to MCP callers.
- Fixed the unsafe CORS default (`allow_origins=["*"]` with
  `allow_credentials=True`); the default is now an explicit localhost origin
  list, with production origins injected at runtime.
- Pinned the `python:3.12-slim` base image by digest, added a root
  `.dockerignore`, and added a `container-security` CI workflow (Trivy + SBOM).

## [1.0.0] - 2026-06-15

### Changed (BREAKING) — GeneFoundry Tool-Naming Standard v1

Adopted the [GeneFoundry Tool-Naming Standard v1](https://github.com/berntpopp/stringdb-link/issues/1).
MCP tool names are now `verb_noun` snake_case with a canonical verb
(`get`/`search`/`list`/`resolve`/`find`/`compare`/`compute`), unprefixed, and
`<= 50` chars. The `genefoundry-router` gateway adds the `stringdb` namespace at
mount time, so tools surface as `stringdb_<tool>`.

Tool names are now generated verbatim from each route's `operation_id` (set in
the route decorators). The previously broken `mcp_names` override map — whose
keys never matched the auto-generated FastAPI `operationId`s, so only
`resolve_protein_identifiers` ever applied — has been removed.

**Tool renames (old MCP name → new MCP name):**

| Old (auto-generated / intended) | New |
| --- | --- |
| `get_network_interactions_api_networks_interactions_post` | `search_protein_interactions` |
| `get_interaction_partners_api_networks_partners_post` | `get_interaction_partners` |
| `get_network_link_api_networks_link_post` | `get_network_link` |
| `get_functional_enrichment_api_enrichment_functional_post` (intended `analyze_functional_enrichment`) | `compute_functional_enrichment` |
| `get_ppi_enrichment_api_enrichment_ppi_post` (intended `analyze_ppi_enrichment`) | `compute_ppi_enrichment` |
| `get_functional_annotations_api_annotations_functional_post` | `get_functional_annotations` |
| `get_homology_scores_api_homology_scores_post` | `get_protein_homology_scores` |
| `get_homology_best_hits_api_homology_best_hits_post` | `get_protein_homology_best_hits` |
| `get_network_image_api_images_network_post` (intended `generate_network_visualization`) | `get_network_image` |
| `resolve_protein_identifiers` | `resolve_protein_identifiers` (unchanged) |

`analyze_*` and `generate_*` verbs are not in the canonical set; the statistical
tests map to `compute`, and the image fetch maps to `get`.

**Removed from the MCP surface (still available as REST endpoints):**

- `GET /api/identifiers/resolve/{identifier}` (single-identifier convenience,
  duplicates `resolve_protein_identifiers`)
- `GET /api/networks/interactions/{identifier}` (duplicates `search_protein_interactions`)
- `GET /api/networks/partners/{identifier}` (duplicates `get_interaction_partners`)
- `POST /api/homology/scores/download` (raw bulk export; `download` is not a
  canonical verb)
- `POST /api/homology/best-hits/download` (raw bulk export)

This brings the MCP surface to the 10 documented, curated tools (previously 15
routes leaked through `FastMCP.from_fastapi`).

**Removed the dead `get_enrichment_image` override** (referenced a route that
does not exist) and the latent singular `get_functional_annotation` key.

### Added

- Domain `tags` on every tool (`protein`, `network`, `enrichment`,
  `annotation`, `homology`, `visualization`) so the gateway can filter/curate.
- CI guard `tests/unit/test_tool_names.py`: asserts every registered tool name
  matches `^[a-z0-9_]{1,50}$`, starts with a canonical verb, and does not
  self-prefix the `stringdb` namespace token.
- README section documenting the canonical gateway namespace token (`stringdb`)
  and the explicit `serverInfo.name` (`StringDB-Link Server`).

### Notes

- No deprecation aliases are provided (project decision): old tool names are
  removed immediately. Update any client that referenced the previous names.

## [0.1.0]

- Initial release.
