# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
