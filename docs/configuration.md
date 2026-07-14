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
| `CORS__ALLOW_ORIGINS` | `[]` | Origins echoed in CORS response headers. |
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
| `STRINGDB_API__CALLER_IDENTITY` | `StringDB-Link/…` | Sent to STRING on every call, as STRING requests. |
| `STRINGDB_API__REDIRECT_BASE_URL` | `https://string-db.org` | The only STRING origin redirects are allowed to target. |

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

## Logging

| Variable | Default | Notes |
|----------|---------|-------|
| `LOGGING__LEVEL` | `INFO` | `DEBUG` … `CRITICAL`. |
| `LOGGING__FORMAT` | `text` | `text` or `json`. |
| `LOGGING__FILE_ENABLED` | `false` | Plus `FILE_PATH`, `FILE_MAX_SIZE`, `FILE_BACKUP_COUNT`. |

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
> discovery behind the gateway. Note that `.env.example` currently ships a different value
> (`StringDB-Link Server`); the code default `stringdb-link` is the ratified one.

`serverInfo.version` is single-sourced from the installed package metadata
(`stringdb_link.__version__`), guarded by `tests/unit/test_version_single_source.py`.

## Checking a configuration

```bash
uv run stringdb-link config             # print the resolved settings
uv run stringdb-link validate-config    # validate and exit non-zero on error
```
