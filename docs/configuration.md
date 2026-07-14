# Configuration

Every setting is an environment variable, read from the process environment or a `.env` file
in the working directory. [`../.env.example`](../.env.example) is the copy-pasteable
template; this page explains what the values mean.

Settings are Pydantic models with the **nested delimiter `__`**: a variable addresses a
section and a field, e.g. `CACHE__IDENTIFIER_TTL` sets `cache.identifier_ttl`. Server-level
settings are flat (`HOST`, `PORT`, `TRANSPORT`). Unknown variables are ignored, so a
misspelled name fails silently — copy the names below exactly.

List-valued variables (`ALLOWED_HOSTS`, `ALLOWED_ORIGINS`, the `CORS__*` lists) are parsed as
**JSON arrays**: `ALLOWED_HOSTS=["localhost","127.0.0.1","::1"]`.

The tables below are **exhaustive and machine-checked**: `tests/unit/test_config_docs_contract.py`
walks the live settings model (`stringdb_link/config.py`) and fails if this page omits a
variable or states a default the code does not set. A row here is a fact, not a description.

## Server

| Variable | Default | Notes |
|----------|---------|-------|
| `HOST` | `127.0.0.1` | Bind address. Keep loopback behind a reverse proxy. |
| `PORT` | `8000` | Bind port. |
| `TRANSPORT` | `unified` | `unified` (REST + MCP), `http` (REST only), or `stdio`. See [deployment.md](deployment.md). |
| `RELOAD` | `false` | Auto-reload; development only. |
| `DEBUG` / `DEVELOPMENT_MODE` | `false` | Either one puts the app in development mode. |

## Request guards (Host / Origin)

Every HTTP route is gated by **exact** allowlists. These are request-admission guards, and
they are independent of the CORS *response* policy below.

| Variable | Default | Notes |
|----------|---------|-------|
| `ALLOWED_HOSTS` | `["localhost","127.0.0.1","::1"]` | Exact `Host` header values. **Wildcard patterns (`*`, `?`, `[]`) are rejected** — the config raises rather than accept an ambiguous boundary. |
| `ALLOWED_ORIGINS` | `[]` | Exact browser `Origin` values. Empty still admits requests that carry **no** `Origin` header (i.e. non-browser clients). |

When deploying behind a reverse proxy, **add the public hostname to `ALLOWED_HOSTS`** — e.g.
`["stringdb-link.genefoundry.org","localhost","127.0.0.1","::1"]`. Forgetting this is the
usual cause of a proxied deployment returning errors while `curl localhost` works.

## CORS (browser response policy)

| Variable | Default | Notes |
|----------|---------|-------|
| `CORS__ALLOW_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000"]` | Origins echoed in CORS response headers. The dev defaults are inert in production: the `ALLOWED_ORIGINS` request guard above rejects a browser request carrying either origin **before** CORS applies. Inject real origins via env. |
| `CORS__ALLOW_CREDENTIALS` | `false` | Off by design: this backend is unauthenticated and holds no cookies or sessions. |
| `CORS__ALLOW_METHODS` | `["GET","POST","PUT","DELETE","OPTIONS"]` | |
| `CORS__ALLOW_HEADERS` | `["*"]` | |

`CORS__ALLOW_CREDENTIALS=true` combined with a wildcard origin **fails startup**: the CORS
spec forbids the combination and browsers reject it, so it can only ever be a footgun.

## STRING API client

| Variable | Default | Notes |
|----------|---------|-------|
| `STRINGDB_API__BASE_URL` | `https://version-12-0.string-db.org/api` | **Pinned to STRING v12.0** for reproducibility — see [data.md](data.md). |
| `STRINGDB_API__RATE_LIMIT_PER_SECOND` | `1.0` | STRING asks callers to wait one second between calls. Do not raise it. |
| `STRINGDB_API__TIMEOUT` | `30` | Seconds. |
| `STRINGDB_API__MAX_RETRIES` | `3` | Retries use exponential backoff. |
| `STRINGDB_API__RETRY_DELAY` | `1.0` | Base backoff delay, seconds. |
| `STRINGDB_API__CALLER_IDENTITY` | `StringDB-Link/0.1.0` | Sent to STRING on every call, as STRING requests. |
| `STRINGDB_API__USER_AGENT` | `StringDB-Link/0.1.0` | `User-Agent` header on every STRING call. |
| `STRINGDB_API__REDIRECT_BASE_URL` | `https://string-db.org` | The only STRING origin redirects are allowed to target. |
| `STRINGDB_API__ENDPOINTS` | *(map, see below)* | STRING paths keyed by operation: `resolve`, `network`, `interactions`, `enrichment`, `annotations`, `images`, `homology`, `homology_best`, `ppi_enrichment`, `enrichment_image`. Settable as a JSON object, but the defaults track the pinned STRING v12.0 API — overriding them is unsupported. |

## Caching

| Variable | Default | Notes |
|----------|---------|-------|
| `CACHE__ENABLED` | `true` | |
| `CACHE__DEFAULT_TTL` | `3600` | Seconds. |
| `CACHE__IDENTIFIER_TTL` | `86400` | 24 h — identifier mappings are stable. |
| `CACHE__NETWORK_TTL` | `43200` | 12 h. |
| `CACHE__ENRICHMENT_TTL` | `21600` | 6 h. |
| `CACHE__IMAGE_TTL` | `7200` | 2 h. |
| `CACHE__MAX_SIZE` | `1000` | Entries. |

The tiering is deliberate: see [data.md](data.md#freshness--caching).

## Performance

| Variable | Default |
|----------|---------|
| `PERFORMANCE__MAX_CONCURRENT_REQUESTS` | `100` |
| `PERFORMANCE__CONNECTION_POOL_SIZE` | `20` |
| `PERFORMANCE__CONNECTION_POOL_MAX_SIZE` | `100` |
| `PERFORMANCE__KEEPALIVE_TIMEOUT` | `5` |

## Security

| Variable | Default | Notes |
|----------|---------|-------|
| `SECURITY__API_KEY_REQUIRED` | `false` | Optional API-key gate on the REST surface. |
| `SECURITY__API_KEY_HEADER` | `X-API-Key` | |
| `SECURITY__RATE_LIMIT_ENABLED` | `true` | Inbound (caller-facing) rate limiting. |
| `SECURITY__RATE_LIMIT_REQUESTS` | `100` | Requests per window. |
| `SECURITY__RATE_LIMIT_WINDOW` | `60` | Window, seconds. |

This backend is **unauthenticated by design** — the `genefoundry-router` / reverse proxy owns
edge auth at the trust boundary. It must never be published directly. See
[`../SECURITY.md`](../SECURITY.md).

## Health check

| Variable | Default | Notes |
|----------|---------|-------|
| `HEALTH_CHECK__ENABLED` | `true` | Serve `GET /health`. |
| `HEALTH_CHECK__INTERVAL` | `30` | Seconds; the interval the container healthcheck is expected to poll on. |
| `HEALTH_CHECK__TIMEOUT` | `10` | Seconds. |

## Logging

| Variable | Default | Notes |
|----------|---------|-------|
| `LOGGING__LEVEL` | `INFO` | `DEBUG` … `CRITICAL`. |
| `LOGGING__FORMAT` | `json` | `json` or `text`. JSON is the default so logs are machine-parseable in a container. |
| `LOGGING__FILE_ENABLED` | `false` | Log to a file in addition to stdout. |
| `LOGGING__FILE_PATH` | `./logs/stringdb-link.log` | Only used when `FILE_ENABLED` is true. |
| `LOGGING__FILE_MAX_SIZE` | `10485760` | Bytes before rotation (10 MiB). |
| `LOGGING__FILE_BACKUP_COUNT` | `5` | Rotated files kept. |

Logging is structured (structlog). A redaction processor
(`stringdb_link/logging_config.py`, `redact_sensitive_processor`) strips sensitive values
from every event, so secrets do not reach the logs; it is guarded by
`tests/unit/test_logging_redaction.py`.

## MCP

| Variable | Default | Notes |
|----------|---------|-------|
| `MCP__PATH` | `/mcp` | Streamable-HTTP endpoint path. |
| `MCP__SERVER_NAME` | `stringdb-link` | Advertised as `serverInfo.name` on `initialize`. |

> [!WARNING]
> `MCP__SERVER_NAME` is a **federation identity contract**, not cosmetics. The conformance
> gate (`.github/workflows/conformance.yml`, `CONFORMANCE_NAME: stringdb-link`) and the
> router's registry both assert `serverInfo.name == stringdb-link`. Overriding it breaks
> discovery behind the gateway. The env templates therefore ship the ratified value, and
> `tests/unit/test_config_docs_contract.py` fails if one of them drifts away from it.

`serverInfo.version` is single-sourced from the installed package metadata
(`stringdb_link.__version__`), guarded by `tests/unit/test_version_single_source.py`.

## Checking a configuration

```bash
uv run stringdb-link config             # print the resolved settings
uv run stringdb-link validate-config    # validate and exit non-zero on error
```
