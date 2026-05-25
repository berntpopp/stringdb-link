# Modernize Python Stack And Agent Workflow Design

## Purpose

Bring StringDB-Link in line with the current PubTator-Link and GeneReview-Link
project conventions so humans, Claude Code, Codex, and other LLM coding agents
can work from one clear repository contract.

This pass modernizes the project skeleton, Python packaging stack, dependency
management, local quality gates, and agent-facing instructions. It does not
split the larger runtime modules yet; those files are grandfathered into a
line-budget allowlist and documented as follow-up structural work.

## Current State

StringDB-Link is a Python FastAPI and MCP server for the STRING protein
interaction API. It already has useful FastAPI route, service, model, CLI,
Docker, and test coverage structure.

The repository lags behind the comparison projects in these areas:

- Packaging uses `setuptools` and Python `>=3.9`.
- Dependencies live in `project.optional-dependencies.dev` instead of uv
  dependency groups.
- There is no `uv.lock` dependency lockfile.
- There is no `Makefile` command surface.
- There is no `CLAUDE.md` or `AGENTS.md`.
- Pre-commit hooks use older revisions and install mypy through the mirror
  hook instead of running the project environment through `uv`.
- There is no line-budget enforcement for large Python modules.

Current modules over the 600-line agentic editing budget:

- `stringdb_link/api/client.py`
- `stringdb_link/services/stringdb_service.py`
- `stringdb_link/models/requests.py`
- `stringdb_link/models/responses.py`

## Target State

StringDB-Link should match the shared conventions used by `../pubtator-link`
and `../genereviews-link`:

- Python requirement: `>=3.12`.
- Build backend: Hatchling.
- Dependency manager: uv with `uv.lock` as the source of truth.
- Dependency grouping: `[dependency-groups].dev` for development tools.
- Runtime dependencies pinned with compatible upper bounds where sibling repos
  already do so.
- Quality tooling: Ruff formatting/linting, strict mypy, pytest, coverage, and
  pre-commit.
- Repository command interface: `Makefile` targets for install, lock, format,
  lint, typecheck, test, local CI, development server, MCP server, and Docker.
- Agent instructions: minimal `CLAUDE.md` that imports `AGENTS.md`; shared
  `AGENTS.md` for Claude Code, Codex, and other LLM workers.
- File-size discipline: 600-line hard cap for new Python modules, with current
  oversized files listed in `.loc-allowlist`.

## Modern Python Stack

The target `pyproject.toml` keeps StringDB-specific dependencies only where
needed and follows the sibling project baseline:

- `hatchling` build backend.
- `requires-python = ">=3.12"`.
- Classifiers for Python 3.12 and 3.13.
- `fastapi>=0.115.0,<1.0.0`.
- `uvicorn[standard]>=0.46.0,<1.0.0`.
- `pydantic>=2.11.0,<3.0.0`.
- `pydantic-settings>=2.6.0,<3.0.0`.
- `httpx>=0.28.0,<1.0.0`.
- `async-lru>=2.0.4,<3.0.0`.
- `structlog>=24.4.0,<26.0.0`.
- `orjson>=3.10.0,<4.0.0`.
- `rich>=15.0.0,<16.0.0`.
- `typer>=0.25.1,<1.0.0`.
- `mcp[cli]>=1.27.0,<2.0.0`.
- `fastmcp>=3.2.0,<4.0.0`.
- `gunicorn>=25.3.0,<27.0.0`.
- `asgi-correlation-id>=4.3.0,<5.0.0`.
- `prometheus-client>=0.21.0,<1.0.0`.
- `python-multipart>=0.0.9`.

Development dependencies move to `[dependency-groups].dev`:

- `pytest>=9.0.3,<10.0.0`.
- `pytest-asyncio>=1.3.0,<2.0.0`.
- `pytest-cov>=6.0.0,<8.0.0`.
- `pytest-mock>=3.14.0,<4.0.0`.
- `pytest-xdist>=3.6.0,<4.0.0`.
- `respx>=0.22.0,<1.0.0`.
- `ruff>=0.8.0,<1.0.0`.
- `mypy>=1.14.0,<3.0.0`.
- `pre-commit>=4.0.0,<5.0.0`.

## Agentic Development Contract

`AGENTS.md` is the repo-wide source of truth for all agentic coding tools. It
documents:

- The project purpose and primary directories.
- uv as the dependency manager.
- `Makefile` as the command interface.
- Required completion check: `make ci-local`.
- Scope discipline for edits.
- MCP-specific safety guidance for research-use tools.
- Modern Python typing conventions.
- File-size discipline for future LLM-friendly development.

`CLAUDE.md` stays intentionally small:

- It imports `AGENTS.md`.
- It only contains Claude Code-specific notes.
- It reminds Claude workers to prefer `make ci-local` before handoff.
- It warns against growing modules past the line-budget threshold.

## File Size Discipline

Add `scripts/check_file_size.py` and `.loc-allowlist`.

The checker enforces a 600-line budget for:

- `stringdb_link/**/*.py`
- `server.py`
- `mcp_server.py`

Tests are excluded. Current oversized runtime files are allowlisted at their
current line counts. They may shrink, but cannot grow beyond the recorded
ceiling without an explicit allowlist update.

This turns structural debt into visible, enforceable debt without mixing
packaging modernization with risky behavioral refactors.

## Makefile Contract

Add a `Makefile` with targets aligned to the sibling repos:

- `make install`
- `make sync`
- `make lock`
- `make upgrade`
- `make format`
- `make format-check`
- `make lint`
- `make lint-ci`
- `make lint-fix`
- `make lint-loc`
- `make typecheck`
- `make typecheck-fast`
- `make typecheck-stop`
- `make typecheck-fresh`
- `make test`
- `make test-fast`
- `make test-unit`
- `make test-integration`
- `make test-cov`
- `make test-all`
- `make check`
- `make ci-local`
- `make precommit`
- `make clean`
- `make dev`
- `make mcp-serve`
- `make mcp-serve-http`
- `make docker-build`
- `make docker-up`
- `make docker-down`
- `make docker-logs`

`ci-local` should run format check, Ruff lint in CI output mode, line-budget
linting, mypy, and fast tests.

## Testing And Verification

The implementation should be verified in layers:

1. `uv lock` succeeds and writes `uv.lock`.
2. `uv sync --group dev` succeeds.
3. `make format-check` passes or reports only intentional formatting changes.
4. `make lint-loc` passes with the grandfathered allowlist.
5. `make test` passes.
6. `make ci-local` is attempted before final handoff.

If strict mypy or full lint fails because the existing code predates the newer
tooling, record the exact failures and keep the modernization changes scoped.
Do not weaken the modern target just to hide existing debt.

## Out Of Scope

- Splitting `api/client.py`, `services/stringdb_service.py`, or large model
  modules.
- Changing the public REST or MCP tool behavior.
- Reworking Docker runtime behavior beyond keeping Makefile targets pointed at
  existing Compose files.
- Adding database, embedding, or benchmark subsystems from the comparison repos.

## Acceptance Criteria

- `pyproject.toml` uses Hatchling, Python 3.12+, uv dependency groups, and
  dependency versions aligned with the comparison repos where applicable.
- `uv.lock` exists.
- `Makefile` exists and provides the shared command surface.
- `CLAUDE.md` and `AGENTS.md` exist with minimal, useful agent instructions.
- `.pre-commit-config.yaml` uses the newer hook pattern and local `uv run`
  checks.
- `scripts/check_file_size.py` and `.loc-allowlist` exist.
- Existing tests remain in `tests/`.
- No runtime module behavior is intentionally changed.
