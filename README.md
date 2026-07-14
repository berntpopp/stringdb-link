# stringdb-link

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/berntpopp/stringdb-link/actions/workflows/ci.yml/badge.svg)](https://github.com/berntpopp/stringdb-link/actions/workflows/ci.yml)
[![Conformance](https://github.com/berntpopp/stringdb-link/actions/workflows/conformance.yml/badge.svg)](https://github.com/berntpopp/stringdb-link/actions/workflows/conformance.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

An **MCP server over [STRING](https://string-db.org/)**, the protein–protein association
network and functional-enrichment database. It serves STRING v12.0 as typed MCP tools over
Streamable HTTP, with the same surface available as a FastAPI REST API.

> [!IMPORTANT]
> Research use only. Not clinical decision support. Do not use for diagnosis,
> treatment, triage, or patient management.

## Why

STRING has a public HTTP API, but it is built for scripts pasted into a browser, not for
agents. Four concrete frictions:

- **Nothing is keyed on gene symbols.** Every useful call wants a STRING protein ID
  (`9606.ENSP00000269305`); getting one is a separate resolution step.
- **Multi-protein queries are string-encoded.** Identifiers are joined with a literal
  carriage return (`%0d`) inside a query parameter — easy to get silently wrong.
- **Results are untyped rows** with terse column names (`stringId_A`, `escore`, `fscore`),
  with no schema to validate against.
- **The default host is a moving target.** STRING tells integrators to pin a versioned host
  (`version-12-0.string-db.org`) so the same query keeps returning the same answer across
  releases — and asks callers to wait one second between calls and to identify themselves.

This server absorbs all four: it pins STRING v12.0, resolves identifiers, validates every
parameter with Pydantic, returns typed envelopes, throttles to STRING's courtesy rate, and
caches by result class. No data bundle, no ingest, no build step — it proxies STRING live.

## Quick start

Hosted — no install:

```bash
claude mcp add --transport http stringdb https://stringdb-link.genefoundry.org/mcp
```

Local (Python 3.12+, [uv](https://github.com/astral-sh/uv)):

```bash
uv sync --group dev
make dev                                     # REST + MCP on http://127.0.0.1:8000/mcp
curl -s localhost:8000/health
claude mcp add --transport http stringdb http://127.0.0.1:8000/mcp
```

> [!NOTE]
> MCP clients need the `unified` transport (what `make dev` runs). `--transport http` serves
> the REST API **without** `/mcp`. See [deployment.md](docs/deployment.md#transports).

## Tools

| Tool | Purpose |
|------|---------|
| `resolve_protein_identifiers` | Map gene symbols, synonyms or UniProt accessions to STRING protein IDs |
| `search_protein_interactions` | Retrieve the interaction network among a set of proteins |
| `get_interaction_partners` | List a protein's STRING interaction partners |
| `compute_functional_enrichment` | Enrichment over GO, KEGG, UniProt keywords, PubMed, Pfam, InterPro and SMART |
| `compute_ppi_enrichment` | Test whether a protein set has more interactions than expected by chance |
| `get_functional_annotations` | Retrieve the functional annotations attached to each protein |
| `get_protein_homology_scores` | Pairwise protein similarity (bit-scores) among the input proteins |
| `get_protein_homology_best_hits` | Best similarity hit per species for the input proteins |
| `get_network_link` | Build a shareable link to the network on the STRING website |
| `get_network_image` | Render the network as an image (PNG, high-res PNG, or SVG) |

Leaf names are **unprefixed**, per Tool-Naming Standard v1. Behind
[`genefoundry-router`](https://github.com/berntpopp/genefoundry-router) the server is mounted
under the `stringdb` namespace, so tools surface as `stringdb_<tool>` — e.g.
`stringdb_get_interaction_partners`. Do not self-prefix tool names; the gateway adds the
namespace (a CI guard enforces this).

## Data & provenance

Data come live from the STRING REST API, pinned to **STRING v12.0**
(`https://version-12-0.string-db.org/api`) so a query keeps its answer across STRING
releases. There is no local mirror; freshness is STRING's, minus a per-result-class cache
TTL (24 h for identifier mappings, 12 h for networks, 6 h for enrichment).

STRING asks callers to wait one second between requests; the client throttles to 1 req/s by
default and identifies itself with `caller_identity`. **Do not bypass the throttle.**

STRING data are licensed **[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**.
Cite STRING when publishing results derived from it:

> Szklarczyk D, Kirsch R, Koutrouli M, et al. The STRING database in 2023: protein–protein
> association networks and functional enrichment analyses for any sequenced genome of
> interest. *Nucleic Acids Res.* 2023;51(D1):D638–D646. doi:10.1093/nar/gkac1000

Full detail — endpoint map, TTL rationale, identifier semantics: [data.md](docs/data.md).

## Documentation

- [Configuration](docs/configuration.md) — every environment variable (the tables are
  machine-checked against the live settings model), the Host/Origin request guards, CORS,
  cache TTLs and the MCP identity contract.
- [Deployment](docs/deployment.md) — transports, entry points, Docker, running behind a
  reverse proxy, and Claude Desktop wiring.
- [Architecture](docs/architecture.md) — how the MCP surface is generated from the REST
  routes, the MCP hardening layers, and the REST API with examples.
- [Data & provenance](docs/data.md) — STRING sources, the v12.0 pin, caching, licence and
  citation.
- [STRING API reference](docs/rest-api.md) — the upstream API docs, vendored.
- [SECURITY.md](SECURITY.md) — vulnerability reporting and required repository settings.
- [AGENTS.md](AGENTS.md) — repository conventions for humans and coding agents.

## Contributing

See [AGENTS.md](AGENTS.md) for engineering conventions (uv, Ruff, mypy strict, the 600-line
module budget, test layout). `make ci-local` is the definition-of-done gate: format, lint,
line budget, README standard, typecheck, and tests. It must be green before handoff.

## License

Code: [MIT](LICENSE) © Bernt Popp. STRING data: **CC BY 4.0** © the STRING Consortium —
attribution required, and any changes or additions you make must be stated.
