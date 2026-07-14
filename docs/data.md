# Data & provenance

Upstream source, freshness model, licensing and citation for the data this server serves.
Research use only; not clinical decision support.

## Upstream

All data are fetched live from the [STRING](https://string-db.org/) REST API. There is **no
local data bundle, no ingest step and no build step** — `stringdb-link` is a typed, cached,
rate-limited proxy in front of STRING, so it serves immediately after install.

The base URL is **pinned to STRING v12.0**:

```env
STRINGDB_API__BASE_URL=https://version-12-0.string-db.org/api
```

The pin is deliberate and load-bearing. STRING's own API guidance is explicit about it:

> When developing your tool use default STRING address (`https://string-db.org`), but when
> your code is ready, you should link to a specific STRING version (for example
> `https://version-12-0.string-db.org`), which will ensure that for the same query you will
> always get the same API response, even after STRING or API gets updated.

Repointing the base URL at the unversioned host makes results non-reproducible across STRING
releases. Bump the pin deliberately, as a reviewed change, when adopting a new STRING release.

A verbatim copy of STRING's API reference is vendored at [`rest-api.md`](rest-api.md).

## Upstream endpoints used

The client maps each tool onto one STRING API endpoint
(`stringdb_link/config_models.py`, `StringDBAPIConfigModel.endpoints`):

| Purpose | STRING endpoint |
|---------|-----------------|
| Identifier resolution | `json/get_string_ids` |
| Interaction network | `json/network` |
| Interaction partners | `json/interaction_partners` |
| Functional enrichment | `json/enrichment` |
| Functional annotation | `json/functional_annotation` |
| PPI enrichment | `json/ppi_enrichment` |
| Homology scores | `json/homology` |
| Best homology hits | `json/homology_best` |
| Network image | `image/network` |
| Enrichment figure | `image/enrichment` |

Enrichment covers Gene Ontology, KEGG pathways, UniProt keywords, PubMed publications, and
Pfam / InterPro / SMART domains.

## Freshness & caching

Freshness follows STRING: a given pinned version is a static release, and the server holds
results only for the TTL of its in-process cache. The TTLs are tiered by how stable each
result class is — identifier mappings change far more slowly than networks or enrichment:

| Result class | Variable | Default |
|--------------|----------|---------|
| Identifier mappings | `CACHE__IDENTIFIER_TTL` | `86400` (24 h) |
| Networks & partners | `CACHE__NETWORK_TTL` | `43200` (12 h) |
| Enrichment | `CACHE__ENRICHMENT_TTL` | `21600` (6 h) |
| Images | `CACHE__IMAGE_TTL` | `7200` (2 h) |
| Anything else | `CACHE__DEFAULT_TTL` | `3600` (1 h) |

See [`configuration.md`](configuration.md) for the full cache and rate-limit settings.

## Rate-limit etiquette

STRING asks callers to *"be considerate and wait one second between each call, so that our
server won't get overloaded"*. The client therefore throttles to **1 request/second** by
default (`STRINGDB_API__RATE_LIMIT_PER_SECOND=1.0`).

**Do not bypass or raise this throttle** to work around slowness — it is the courtesy
contract with a free public service, and `AGENTS.md` forbids it ("Respect STRING API rate
limits; do not bypass the existing client throttling").

STRING also asks callers to identify themselves via the `caller_identity` parameter; the
client sends it on every request (`STRINGDB_API__CALLER_IDENTITY`).

## Identifier semantics

STRING keys everything on STRING protein IDs (e.g. `9606.ENSP00000269305`), not on gene
symbols. `resolve_protein_identifiers` is the front door: it maps symbols, synonyms and
UniProt accessions onto STRING IDs so every other tool has a stable key. `species` is an
**NCBI taxon ID** (`9606` = human).

## Licence

STRING data are released under **[Creative Commons BY 4.0](https://creativecommons.org/licenses/by/4.0/)**:

> All data and download files in STRING are freely available under a "Creative Commons BY
> 4.0" license.

When using the data, provide appropriate credit and state any changes or additions you made.
This is separate from the licence on *this server's code*, which is MIT (see
[`../LICENSE`](../LICENSE)).

## Citation

Cite STRING when you publish results derived from it:

> Szklarczyk D, Kirsch R, Koutrouli M, et al. The STRING database in 2023: protein–protein
> association networks and functional enrichment analyses for any sequenced genome of
> interest. *Nucleic Acids Res.* 2023;51(D1):D638–D646. doi:10.1093/nar/gkac1000
