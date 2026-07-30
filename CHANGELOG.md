# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [4.1.2] - 2026-07-30

### Changed

- **CI tests the interpreter that actually ships.** The `quality` job now runs
  on a `["3.12", "3.14"]` matrix instead of 3.12 only. `docker/Dockerfile` ships
  `python:3.14-slim`, so until now the test suite was never exercised on the
  interpreter that reaches production — only the image itself was, via
  `container-ci`/`conformance`. A 3.14-only stdlib or typing regression would
  have shipped uncaught. 3.12 stays in the matrix because it is the declared
  `requires-python` floor; dropping it would make that floor a false claim. The
  coverage gate still runs once (on 3.14, push to `main`). `requires-python`,
  ruff `target-version` and mypy `python_version` are deliberately unchanged at
  3.12.
- **The matrix is forced with `UV_PYTHON`, not just `setup-python`.** `uv`
  resolves its interpreter from `.python-version` (pinned to 3.12 for local dev)
  *before* it consults `PATH`, so `actions/setup-python` alone does not move it:
  both legs would have built a 3.12 environment and the "3.14" leg would have
  tested the floor twice — green, and meaningless. The job now exports
  `UV_PYTHON: ${{ matrix.python-version }}`, which outranks `.python-version`
  and applies to every `uv run` inside `make ci-local`.
- **New guard `tests/unit/test_ci_python_matrix.py`.** Pins the matrix against
  `pyproject.toml`'s floor and the Dockerfile's `FROM python:<x.y>-slim`, so a
  base-image bump that is not mirrored into CI fails instead of silently
  re-opening the blind spot.

## [4.1.1] - 2026-07-30

Dependabot onboarding plus the accumulated dependency sweep it had been hiding.
This repository had **no `.github/dependabot.yml` at all**, so its "zero open
Dependabot PRs" reported the absence of a watcher rather than health: Python
dependencies, GitHub Actions and the container base image had never been
auto-bumped. No runtime behaviour change.

### Added

- **Dependabot coverage** (`.github/dependabot.yml`), fleet-standard four
  ecosystems: `uv` at `/`, `github-actions` at `/`, `docker` and
  `docker-compose` at `/docker`. Weekly Monday, Europe/Berlin, staggered
  04:00/04:15/04:30/04:45, limit 5, `deps`/`ci` commit prefixes.
- Release-audit regressions for the repaired `4.1.0` MCP surface: decodable nonempty
  network images, the functional-annotation REST/MCP route, honest filtered enrichment
  pagination, generated usable network-link formats, and fenced non-retryable STRING
  background-identifier errors. This release publishes the already-merged repair rather
  than changing its public version.

### Changed

- Re-vendored the behaviour conformance gate from genefoundry-router `56db958`
  (`docs/conformance/behaviour.py` blob `c69801687`) so live MCP contract checks
  treat not-found example probes as inconclusive and keep empty auxiliary objects from hiding counted rows.
- **Dependencies swept** (43 locked packages moved). Direct: `fastapi`
  0.136.3 → 0.141.1, `uvicorn` 0.48.0 → 0.52.0, `mcp` 1.28.1 → 1.29.0,
  `fastmcp` 3.4.4 → 3.4.5, `typer` 0.25.1 → 0.27.0, `prometheus-client`
  0.25.0 → 0.26.0, `python-multipart` 0.0.31 → 0.0.32, `ruff` 0.15.14 →
  0.16.0, `mypy` 2.1.0 → 2.3.0, `pytest` 9.0.3 → 9.1.1, `pytest-asyncio`
  1.3.0 → 1.4.0, `pre-commit` 4.6.0 → 4.6.1. Notable transitives:
  `cryptography` 48.0.1 → 49.0.0, `certifi` 2026.5.20 → 2026.7.22,
  `websockets` 16.0 → 17.0, `anyio` 4.13.0 → 4.14.2.
- **`mcp[cli]` floor raised `>=1.27.0` → `>=1.28.1`.** The lock already pinned a
  fixed version, but the constraint still *permitted* a resolve vulnerable to
  GHSA-vj7q-gjh5-988w (WebSocket transport missing Host/Origin validation),
  GHSA-jpw9-pfvf-9f58 (HTTP transports serving session requests without
  verifying the authenticated principal) and GHSA-hvrp-rf83-w775 (experimental
  task handlers reachable across clients). The floor now makes that resolve
  impossible.
- Ruff's lint rule set is now declared with `select` instead of
  `extend-select`. ruff 0.16.0 grew its *default* rule set from 59 to 413
  rules; `extend-select` would have silently adopted all of them. The listed
  rules are a superset of the pre-0.16 default, so the effective rule set is
  unchanged.
- Pinned GitHub Actions: `actions/checkout` 7.0.0 → 7.0.1 (and 6.0.3 → 7.0.1 in
  `container-security.yml`, which had drifted a major version behind the other
  workflows), `actions/setup-python` v6 → 7.0.0, `astral-sh/setup-uv` 8.2.0 →
  9.0.0.
- Container base image moved from `python:3.12-slim` (digest `423ed6a`) to the
  fleet-standard `python:3.14-slim` (digest `cea0e60`). Verified locally: image
  builds, the SUID/hardlink hardening guards still pass, and the container
  serves REST `/api/health` plus MCP `initialize` on Python 3.14.6 with all 11
  transport + behaviour conformance probes green.

### Fixed

- `test_functional_annotation_operation_is_registered` now asserts against the
  advertised OpenAPI schema instead of walking `app.routes`. FastAPI >=0.141
  keeps sub-routers as opaque `_IncludedRouter` entries rather than flattening
  their `APIRoute`s into `app.routes`, so the private-attribute walk stopped
  seeing included routes. The route itself is unchanged and still served.

## [4.1.0] - 2026-07-15

GeneFoundry fleet MCP contract-hardening sweep. Vendors the behaviour gate
(`docs/conformance/behaviour.py`, byte-identical from `genefoundry-router@791363c`)
and closes every contract defect it — and the live MCP audit (#33) — surfaced.
Behaviour gate: 20 fail / 10 UNGATED → **0 fail / 0 UNGATED (CONFORMANT)**.
Surface: 4,625t → **4,083t**, `outputSchema` 24% → **0%**, `doc%` 100%, 0 → 26 examples.

### Fixed

- **`isError` is now set on every error envelope — for BOTH the raised and the
  returned-dict paths.** The MCP error carrier returned `ToolResult(structured_content=...)`
  without `is_error=True`, so a client branching on the protocol `isError` bit saw every
  failed call as a success. Verified against fastmcp 3.4.4 that the return path keeps
  `structuredContent` while carrying `is_error=True`; errors now route through
  `ToolResult(..., is_error=True)`. A payload a tool *returns* as `{"success": false}`
  (rather than raising) is likewise normalized to an error frame with `isError:true`,
  never re-wrapped as a success.
- **`error_code` is closed to the six-value canonical enum** (`invalid_input`,
  `not_found`, `ambiguous_query`, `upstream_unavailable`, `rate_limited`, `internal`):
  `internal_error` → `internal`.
- **Validation errors now name the offending parameter.** The error frame carries
  `field`/`field_errors`, derived ONLY from the request-validation `loc` path (this
  server's own schema parameter names, never caller/upstream prose), so an LLM can
  self-correct.
- **`get_network_link`: `output_format` no longer silently returns an empty result.**
  8 of its 9 declared enum values returned `{"success": true, "result": {}}`. The four
  formats STRING actually serves for a link (`json`, `tsv`, `tsv-no-header`, `xml`) are
  kept and each is shaped into a structured result — `json` fills `url`; the text
  formats fill `formatted` (STRING's raw serialization) with the URL also extracted
  into `url`. STRING's `psi-mi`/`image`/`svg` link formats (which carry no link
  payload) are dropped from the enum. (Silent-empty filter, without capability loss.)
- **`compute_functional_enrichment` / `compute_ppi_enrichment`: ANY STRING in-band
  error is now `invalid_input` naming a field, not a false `upstream_unavailable`.**
  STRING returns HTTP 200 with `[{"error": "...", ...}]` for a bad request; this was
  mis-mapped to a retryable "upstream unavailable". The general class is now handled —
  `background_error` names `background_string_identifiers`, and any other in-band error
  names `identifiers` — as a non-retryable `invalid_input` (upstream prose never
  echoed), so a new STRING error type can never regress to a field-less error or a
  false retryable outage.
- **`get_functional_annotations` works again.** Sending `allow_pubmed`/`only_pubmed`
  (even `=0`) made STRING attach PMID annotations and balloon the response past the
  byte cap, so the tool always failed. The flags are now sent only when opted in.
- **`get_network_image` returns an image again — on the MCP surface only.** STRING's
  binary body cannot ride inside a structured MCP envelope, so the tool returned an
  internal error or an empty result. The MCP tool now returns a base64-encoded
  `NetworkImageResult` (format, content-type, size, `image_base64`) via a dedicated
  `POST /api/images/network/json` route; the REST `POST /api/images/network` endpoint
  keeps its raw-binary contract (renamed operation `download_network_image`, excluded
  from MCP). An empty upstream image body is now a `upstream_unavailable` error, never
  a `success` with zero bytes.
- **`get_interaction_partners` reports an honest, limit-invariant `total_count` and
  paginates PER PROTEIN.** It reported `total_count = len(returned page)` and
  head-sliced the flattened partner list — which for a multi-protein query returned
  only the first protein's partners and omitted every later protein. It now fetches the
  full partner set (so the total is the true count, invariant of `limit`), applies
  `limit` per query protein so every queried protein is represented, and sets
  `truncated`.

### Added

- **`compute_functional_enrichment` gains `limit` and `category`.** An unfiltered
  30-gene panel returned ~992 terms (~421k tokens). `limit` (1–1000, default 100)
  returns the most-significant terms first; `category` (a closed `EnrichmentCategory`
  enum) filters to one STRING category. `total_count` still reports the full number of
  matching terms and `truncated` signals more exist, so a smaller `limit` never hides
  how many there are.
- **Tool-Schema Documentation Standard v1**: every required and array parameter now
  carries `examples`; closed vocabularies are declared as enums matching the runtime.
- Vendored behaviour gate (`tests/conformance/behaviour.py`,
  `tests/conformance/test_behaviour_v1.py`) wired into `mcp-conformance` CI alongside
  the transport probe.

### Changed

- **Tool-Surface Budget Standard v1**: `outputSchema` is suppressed on every tool
  (optional in MCP, unread by models, 24% of the surface) and
  `FastMCP(dereference_schemas=False)`. `structuredContent` is unaffected (every tool
  returns a dict envelope) and untrusted-text fencing still happens on the wire
  (Response-Envelope Standard v1.1a).

## [4.0.6] - 2026-07-14

### Changed

- **The NPM deployment pulls the released image instead of building from source.**
  `docker/docker-compose.npm.yml` is a pure overlay on `docker-compose.yml`, which
  defines `build:` — so the deployed chain (`docker-compose.yml -f
  docker-compose.npm.yml`) inherited it and the server rebuilt the image on every
  deploy, even though CI had already published an attested, digest-addressable image
  to GHCR. The overlay now does `build: !reset null` and requires `STRINGDB_LINK_IMAGE`
  pinned to a digest, failing closed when it is unset. Nothing else changed:
  `container_name` (`stringdb_link_server`, which NPM forwards to), the Compose project
  name, the healthcheck, the hardening block, networks and `command` are all preserved.

## [4.0.5] - 2026-07-13

### Fixed

- Re-pin the reusable container CI and container release callers to the corrected
  GeneFoundry container release standard, which fixes latent defects in the shared
  release pipeline (notably GHCR authentication before the version alias is
  pushed). No runtime behaviour change. Research use only.

## [4.0.4] - 2026-07-13

### Added

- Adopt the GeneFoundry container release standard with SHA-pinned reusable
  container CI/release callers, release metadata, digest-only production Compose,
  and complete OCI image labels. Research use only.

## [4.0.3] - 2026-07-12

### Security

- Adopted the canonical outbound HTTP Policy v1 for the configured STRING
  origins, including the supported generic-to-versioned redirect. Redirect hops
  are checked against the configured origins, decoded response bodies are
  bounded, and policy failures use fixed, identifier-free errors. The
  production client is bound to the shared conformance suite. Research use
  only.

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
