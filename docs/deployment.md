# Deployment

How to run `stringdb-link` — locally, in Docker, and behind a reverse proxy — plus the MCP
client wiring. Configuration values referenced here are defined in
[`configuration.md`](configuration.md).

## Entry points

Two console scripts ship with the package (`pyproject.toml` → `[project.scripts]`):

| Script | Module | Purpose |
|--------|--------|---------|
| `stringdb-link` | `stringdb_link.cli:main` | The CLI: `server`, `mcp`, `config`, `validate-config`, `health`, `version`. |
| `stringdb-mcp` | `mcp_server:main` | Direct **stdio** MCP entry point (Claude Desktop and other stdio hosts). |

## Transports

This server is tri-modal — it can serve REST only, MCP only, or both from one process.

| Mode | Command | Serves |
|------|---------|--------|
| `unified` (default) | `stringdb-link server --transport unified --port 8000` | FastAPI REST **and** MCP over Streamable HTTP at `/mcp` |
| `http` | `stringdb-link server --transport http --port 8000` | FastAPI REST only |
| `stdio` | `stringdb-link mcp` (or `python mcp_server.py`) | MCP over stdio |

> [!IMPORTANT]
> MCP clients need **`unified`**. `--transport http` does not expose `/mcp`. This is the
> usual cause of a "server added but no tools" symptom behind the router.

Make targets wrap the common cases:

```bash
make dev              # unified, 127.0.0.1:8000, --reload
make mcp-serve-http   # unified, 0.0.0.0:8000  (container / proxied form)
make mcp-serve        # stdio
```

## Health

| Path | Purpose |
|------|---------|
| `GET /health` | Root-level probe. Required by the MCP Transport Standard v1 conformance probe and used by the Docker health check. |
| `GET /api/health` | Detailed health, including upstream STRING reachability. |
| `GET /api/version` | Version metadata. |

`stringdb-link health` performs the check from the CLI.

## Docker

Compose files live in [`../docker/`](../docker); see [`../docker/README.md`](../docker/README.md)
for the image internals and file-by-file breakdown.

```bash
make docker-build     # docker compose -f docker/docker-compose.yml build
make docker-up        # start
make docker-logs      # tail
make docker-down      # stop
```

| File | Use |
|------|-----|
| `docker/docker-compose.yml` | Base / development stack. |
| `docker/docker-compose.dev.yml` | Hot-reload overlay. |
| `docker/docker-compose.prod.yml` | Production: Gunicorn, digest-pinned image, resource limits, no published ports. |
| `docker/docker-compose.npm.yml` | Production behind an external Nginx Proxy Manager network. |

Environment templates: [`../.env.example`](../.env.example) (local),
[`../.env.docker.example`](../.env.docker.example) (container),
[`../.env.npm.example`](../.env.npm.example) (proxied production).

The container follows the fleet's Container & Deployment Hardening Standard v1: non-root,
read-only root filesystem, all capabilities dropped, `no-new-privileges`, resource limits,
digest-pinned base image, and CI image scanning. Release metadata is pinned in
[`../container-release.json`](../container-release.json).

## Fleet deploy contract

The GeneFoundry fleet controller (`strato_v6_docker_npm`) deploys and validates
`docker/docker-compose.npm.yml` and requires every service there to declare a numeric,
non-root `user: "<uid>:<gid>"` — its runtime observer proves the effective uid from
`/proc`. `stringdb-link`'s value (`999:999`) comes from `docker/Dockerfile`
(`groupadd --system app`, `useradd --system --gid app`), not from a sibling `-link`
repo. `user` must **not** appear in the Compose files listed in
`container-release.json` (`docker-compose.yml`, `docker-compose.prod.yml`); the shared
release gate forbids it there. The overlay also declares `expose: ["8000"]` even
though `ports: !reset []` publishes nothing, because the controller's
`validate-deployed-overlay` gate refuses a rendered model with no `expose` entry
naming the image's container port. `container-release.json`'s `deployed_compose_files`
lists exactly `docker-compose.yml` + `docker-compose.npm.yml` — the set Strato deploys
— so that gate checks the file set actually deployed; `container-release.yml` and
`container-ci.yml` both pin their shared workflow at `genefoundry-router` `v0.8.5`
(`31ea81cee5475fc3655c047c63a89739948f99a9`) and must move together, since both
validate `container-release.json` against the same schema. `tests/unit/test_deploy_overlay_user.py`
guards all of the above. Self-check the merged render before shipping an overlay change:

```bash
export STRINGDB_LINK_IMAGE="ghcr.io/berntpopp/stringdb-link@sha256:<any 64-hex digest>"
docker compose -f docker/docker-compose.yml -f docker/docker-compose.npm.yml \
  config --format json > /tmp/stringdb-link-rendered.json
cd /path/to/strato_v6_docker_npm && uv run python -c "
import sys, json; sys.path.insert(0, 'scripts')
from utils.deployment_preflight import canonical_projection
p = canonical_projection(json.load(open('/tmp/stringdb-link-rendered.json')), project='stringdb-link')
for n, s in p['services'].items(): print(n, 'user=', s.get('user'))
print('PROJECTION OK')"
```

## Behind a reverse proxy

The backend is **unauthenticated by design**. The `genefoundry-router` (or your own reverse
proxy) is the trust boundary and owns edge auth. Two consequences:

1. **Never publish the container port directly.** In production, bind loopback or expose the
   port only on the proxy's internal network (`docker-compose.prod.yml` publishes nothing).
2. **Add the public hostname to `ALLOWED_HOSTS`**, e.g.
   `ALLOWED_HOSTS=["stringdb-link.genefoundry.org","localhost","127.0.0.1","::1"]`.
   The Host guard takes exact values; wildcards are rejected. A proxied deployment that
   works on `localhost` but fails through the proxy is nearly always this.

TLS terminates at the proxy. Set `ALLOWED_ORIGINS` only if a browser origin must reach the
server directly; it is empty by default, which still admits non-browser clients (no `Origin`
header).

## MCP client wiring

Hosted (Streamable HTTP):

```bash
claude mcp add --transport http stringdb https://stringdb-link.genefoundry.org/mcp
```

Local (Streamable HTTP), after `make dev`:

```bash
claude mcp add --transport http stringdb http://127.0.0.1:8000/mcp
```

Claude Desktop (stdio) — `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "stringdb-link": {
      "command": "stringdb-link",
      "args": ["mcp"],
      "env": {
        "STRINGDB_API__RATE_LIMIT_PER_SECOND": "1.0"
      }
    }
  }
}
```

Behind `genefoundry-router` the server is mounted under the `stringdb` namespace and its
tools surface as `stringdb_<tool>` — see [`architecture.md`](architecture.md#federation-contract).

## Operator follow-ups

[`../SECURITY.md`](../SECURITY.md) documents the vulnerability-reporting process **and one
outstanding operator action**: GitHub secret scanning and push protection are repository
settings, not workflow files, so they cannot be enabled from a pull request. An admin must
enable them with `gh api -X PATCH repos/berntpopp/stringdb-link …` (exact command in
`SECURITY.md`). Code scanning (CodeQL) is already wired via
`.github/workflows/security.yml`.
