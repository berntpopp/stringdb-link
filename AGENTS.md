# AGENTS.md

Shared repository instructions for agentic coding tools working in StringDB-Link.

## Project

StringDB-Link is a Python FastAPI and MCP server for the STRING protein-protein
interaction database.

Primary areas:

- `stringdb_link/` - Python package, FastAPI routes, services, client, models,
  configuration, and MCP-facing code
- `tests/` - unit, API, and integration tests
- `docker/` - Dockerfile and Compose deployment files
- `docs/superpowers/plans/` - implementation plans for agentic workers
- `docs/superpowers/specs/` - design specs for agentic workers

## Source Of Truth

- Use this file for shared repo-wide agent guidance.
- Keep `CLAUDE.md` lean and Claude-specific; it should reference this file.
- Prefer `Makefile` targets over ad hoc commands.
- Use `uv.lock` as the dependency lock source of truth.

## Working Rules

- Do not revert or overwrite changes you did not make unless explicitly asked.
- Keep edits scoped to the task and avoid unrelated refactors.
- Prefer existing code patterns over new abstractions.
- Put tests under `tests/`; do not create alternate test roots.
- Use ASCII unless a file already requires non-ASCII content.
- Respect STRING API rate limits; do not bypass the existing client throttling.
- For MCP work, keep public hosted tools research-use scoped and avoid exposing
  destructive cache operations.

## Commands

Required checks before claiming completion:

- `make ci-local`

One-time local setup: `make install`, then `uv run pre-commit install` to install the
git hooks (Ruff, mypy, and the per-file line budget).

Useful focused commands:

- `make install`
- `make lock`
- `make format`
- `make lint`
- `make lint-fix`
- `make lint-loc`
- `make lint-readme`
- `make typecheck`
- `make typecheck-fast`
- `make test`
- `make test-fast`
- `make test-unit`
- `make test-integration`
- `make test-cov`
- `make precommit`
- `make dev`
- `make mcp-serve`
- `make mcp-serve-http`
- `make docker-build`
- `make docker-up`
- `make docker-down`

## Coding Standards

- Use `uv` for dependency management; do not use direct `pip` installs.
- Use modern Python typing: `list[str]`, `dict[str, int]`, `str | None`.
- Format and lint Python with Ruff.
- Type check with mypy strict targeting Python 3.12.
- Keep FastAPI route behavior covered by route tests and service behavior
  covered by unit tests.

## Documentation Discipline

`README.md` follows the **GeneFoundry README Standard v1** and is machine-checked by
`make lint-readme` (`scripts/check_readme.py`, copied verbatim across the fleet). It is
the front door, not the manual: fixed section order, a 200-line hard ceiling, no
hand-typed counts or scores. Reference docs live in `docs/`:

- `docs/configuration.md` - environment variables and request guards
- `docs/deployment.md` - transports, entry points, Docker, reverse proxy
- `docs/architecture.md` - module layout, REST-to-MCP generation, REST examples
- `docs/data.md` - STRING sources, caching, licence, citation

Add a tool, update the README's `## Tools` table: `tests/unit/test_readme_tools.py`
asserts the table equals the registered tool surface exactly, and CI fails otherwise.
Do not move operator or reference detail back into the README; extend `docs/` instead.

## File Size Discipline

Hard cap: **600 lines per Python module** in `stringdb_link/`, `server.py`, and
`mcp_server.py`. Enforced by `make lint-loc` and pre-commit. Tests are exempt.

Why: large modules concentrate complexity, slow type checking, and degrade
LLM-assisted refactors because one edit risks unrelated behavior.

How:

- New files MUST stay under 600 lines.
- Existing oversized files are grandfathered in `.loc-allowlist` with their
  current line count as the ceiling. They may shrink but not grow.
- Prefer cohesive splits: one module per responsibility, not random partitioning.
- Keep public facades stable across splits so call sites do not churn.
- If an allowlisted file must grow, update `.loc-allowlist` explicitly and link
  the decomposition plan in the commit message.

## Testing Notes

- `make test` is the fast default.
- `make test-cov` runs coverage reports.
- `make ci-local` runs formatting, linting, line-budget checks, type checking,
  and tests.
- Treat failing checks as real issues unless you have clear evidence otherwise.
