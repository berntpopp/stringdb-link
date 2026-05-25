# Modernize Python Stack And Agent Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize StringDB-Link's Python stack, uv workflow, local checks, and agent instructions to match PubTator-Link and GeneReview-Link conventions without changing runtime behavior.

**Architecture:** Keep the existing `stringdb_link/` application structure intact. Replace project tooling around it: Hatchling packaging, uv dependency groups and lockfile, Makefile commands, pre-commit hooks, agent docs, and line-budget enforcement with grandfathered oversized modules.

**Tech Stack:** Python 3.12+, Hatchling, uv, FastAPI, MCP/FastMCP, Ruff, mypy, pytest, pytest-xdist, pre-commit.

---

## File Structure

- Modify `pyproject.toml`: switch from setuptools to Hatchling, raise Python target, align runtime and dev dependency declarations, and update Ruff/mypy/pytest settings.
- Create `.python-version`: pin local development to Python 3.12.
- Create or update `uv.lock`: lock dependencies through `uv lock`.
- Create `Makefile`: provide the shared command surface used by sibling repos.
- Modify `.pre-commit-config.yaml`: update hook revisions and use local `uv run` checks.
- Create `AGENTS.md`: shared instructions for Claude Code, Codex, and other LLM coding agents.
- Create `CLAUDE.md`: minimal Claude Code entrypoint that imports `AGENTS.md`.
- Create `scripts/check_file_size.py`: enforce the runtime Python module line budget.
- Create `.loc-allowlist`: grandfather current oversized modules at current line counts.
- Optionally create `docs/superpowers/README.md`: explain where specs and plans live if the directory has no README.

## Task 1: Record Baseline And Guard Dirty Worktree

**Files:**
- Inspect only: repository root

- [ ] **Step 1: Check git status**

Run:

```bash
git status --short
```

Expected: either no output or only unrelated user changes. If unrelated user
changes exist, do not edit those files unless this plan explicitly requires it.

- [ ] **Step 2: Capture current oversized module counts**

Run:

```bash
wc -l stringdb_link/api/client.py stringdb_link/services/stringdb_service.py stringdb_link/models/requests.py stringdb_link/models/responses.py
```

Expected current approximate counts:

```text
796 stringdb_link/api/client.py
771 stringdb_link/services/stringdb_service.py
682 stringdb_link/models/requests.py
634 stringdb_link/models/responses.py
```

Use the actual command output when writing `.loc-allowlist`.

## Task 2: Modernize `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace the build backend**

Set:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Update project metadata and Python target**

Keep the existing package name, description, README, MIT license, authors,
keywords, URLs, and scripts. Change:

```toml
requires-python = ">=3.12"
```

Replace Python classifiers with:

```toml
"Programming Language :: Python :: 3.12",
"Programming Language :: Python :: 3.13",
```

- [ ] **Step 3: Replace runtime dependency bounds**

Use this dependency list unless a lock resolution error requires the closest
compatible sibling-repo version:

```toml
dependencies = [
    "fastapi>=0.115.0,<1.0.0",
    "uvicorn[standard]>=0.46.0,<1.0.0",
    "pydantic>=2.11.0,<3.0.0",
    "pydantic-settings>=2.6.0,<3.0.0",
    "httpx>=0.28.0,<1.0.0",
    "async-lru>=2.0.4,<3.0.0",
    "mcp[cli]>=1.27.0,<2.0.0",
    "fastmcp>=3.2.0,<4.0.0",
    "structlog>=24.4.0,<26.0.0",
    "orjson>=3.10.0,<4.0.0",
    "typer>=0.25.1,<1.0.0",
    "rich>=15.0.0,<16.0.0",
    "python-multipart>=0.0.9",
    "gunicorn>=25.3.0,<27.0.0",
    "asgi-correlation-id>=4.3.0,<5.0.0",
    "prometheus-client>=0.21.0,<1.0.0",
]
```

- [ ] **Step 4: Replace optional dev dependencies with uv dependency group**

Remove `[project.optional-dependencies].dev`, `production`, and `all`. Add:

```toml
[dependency-groups]
dev = [
    "pytest>=9.0.3,<10.0.0",
    "pytest-asyncio>=1.3.0,<2.0.0",
    "pytest-cov>=6.0.0,<8.0.0",
    "pytest-mock>=3.14.0,<4.0.0",
    "pytest-xdist>=3.6.0,<4.0.0",
    "respx>=0.22.0,<1.0.0",
    "ruff>=0.8.0,<1.0.0",
    "mypy>=1.14.0,<3.0.0",
    "pre-commit>=4.0.0,<5.0.0",
]
```

- [ ] **Step 5: Replace setuptools config with Hatch config**

Remove `[tool.setuptools]`, `[tool.setuptools.packages.find]`, and
`[tool.setuptools.package-data]`. Add:

```toml
[tool.hatch.build.targets.wheel]
packages = ["stringdb_link"]
```

- [ ] **Step 6: Align Ruff with sibling repos**

Set:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
extend-select = [
    "E",
    "W",
    "F",
    "I",
    "N",
    "UP",
    "B",
    "C4",
    "S",
    "T20",
    "SIM",
    "RUF",
]
ignore = [
    "S101",
    "E501",
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"

[tool.ruff.lint.per-file-ignores]
"tests/**/*" = ["S101", "T20"]
```

Remove the older huge `select` list unless an existing ignore is still needed
for current code to lint. Prefer recording existing debt over expanding ignores.

- [ ] **Step 7: Align mypy settings**

Set:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
exclude = [
    ".*site-packages.*",
    ".*/miniforge3/.*",
    ".*/venv/.*",
    ".*/.venv/.*",
    "htmlcov/.*",
]
```

Keep or update the existing missing-import override to include:

```toml
[[tool.mypy.overrides]]
module = [
    "uvicorn.*",
    "fastmcp.*",
    "mcp.*",
    "async_lru.*",
    "orjson.*",
    "structlog.*",
    "rich.*",
    "typer.*",
    "asgi_correlation_id.*",
    "prometheus_client.*",
]
ignore_missing_imports = true
```

- [ ] **Step 8: Align pytest and coverage**

Keep existing useful markers. Change pytest addopts to avoid making coverage
mandatory for every quick test run:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
addopts = [
    "--strict-markers",
    "-ra",
]
```

Set coverage floor to the current realistic target after a baseline run. If the
existing suite already clears 80%, use:

```toml
[tool.coverage.report]
fail_under = 80
show_missing = true
skip_empty = true
```

If it does not, use the current measured integer floor and document the gap in
the final handoff.

- [ ] **Step 9: Validate TOML**

Run:

```bash
uvx taplo fmt --check pyproject.toml
```

Expected: success. If `taplo` is unavailable, run:

```bash
python -m tomllib pyproject.toml
```

Expected: no parse error.

- [ ] **Step 10: Commit pyproject modernization**

Run:

```bash
git add pyproject.toml
git commit -m "build: modernize Python project metadata"
```

## Task 3: Add uv Runtime Files

**Files:**
- Create: `.python-version`
- Create: `uv.lock`

- [ ] **Step 1: Add `.python-version`**

Create `.python-version` with:

```text
3.12
```

- [ ] **Step 2: Generate the lockfile**

Run:

```bash
uv lock
```

Expected: `uv.lock` is created or updated successfully.

- [ ] **Step 3: Sync development environment**

Run:

```bash
uv sync --group dev
```

Expected: project and dev tools install successfully.

- [ ] **Step 4: Commit uv files**

Run:

```bash
git add .python-version uv.lock
git commit -m "build: add uv lockfile"
```

## Task 4: Add Makefile Command Surface

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Create `Makefile`**

Add:

```makefile
.PHONY: help install lock upgrade sync format format-check lint lint-ci lint-fix lint-loc typecheck typecheck-fast typecheck-stop typecheck-fresh test test-fast test-unit test-integration test-cov test-all check ci-local precommit clean dev mcp-serve mcp-serve-http docker-build docker-up docker-down docker-logs

DOCKER_COMPOSE := $(shell if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then echo "docker compose"; elif command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

.DEFAULT_GOAL := help

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Install project and development dependencies with uv
	uv sync --group dev

sync: install ## Alias for install

lock: ## Resolve and update uv.lock
	uv lock

upgrade: ## Upgrade locked dependencies
	uv lock --upgrade

format: ## Format Python code
	uv run ruff format stringdb_link tests server.py mcp_server.py

format-check: ## Check formatting without writing
	uv run ruff format --check stringdb_link tests server.py mcp_server.py

lint: ## Lint Python code
	uv run ruff check stringdb_link tests server.py mcp_server.py

lint-ci: ## Lint Python code without modifying files
	uv run ruff check stringdb_link tests server.py mcp_server.py --output-format=github

lint-fix: ## Lint and apply safe fixes
	uv run ruff check stringdb_link tests server.py mcp_server.py --fix

lint-loc: ## Enforce per-file line budget (see AGENTS.md "File Size Discipline")
	uv run python scripts/check_file_size.py

typecheck: ## Type check package
	uv run mypy stringdb_link server.py mcp_server.py

typecheck-fast: ## Type check with mypy daemon and fallback
	@tmp_log=$$(mktemp); \
	if uv run dmypy run -- stringdb_link server.py mcp_server.py >$$tmp_log 2>&1; then \
		cat $$tmp_log; \
	elif grep -Eq "Daemon crashed!|INTERNAL ERROR" $$tmp_log; then \
		echo "dmypy crashed; retrying with a fresh daemon..."; \
		uv run dmypy stop >/dev/null 2>&1 || true; \
		if uv run dmypy run -- stringdb_link server.py mcp_server.py >$$tmp_log 2>&1; then \
			cat $$tmp_log; \
		else \
			cat $$tmp_log; \
			echo "Falling back to plain mypy..."; \
			uv run dmypy stop >/dev/null 2>&1 || true; \
			uv run mypy stringdb_link server.py mcp_server.py; \
		fi; \
	else \
		cat $$tmp_log; \
		rm -f $$tmp_log; \
		exit 1; \
	fi; \
	rm -f $$tmp_log

typecheck-stop: ## Stop mypy daemon
	uv run dmypy stop

typecheck-fresh: ## Clear mypy cache and run typecheck
	rm -rf .mypy_cache
	uv run mypy stringdb_link server.py mcp_server.py

test: ## Run tests quickly
	uv run pytest tests -q

test-fast: ## Run tests in parallel with pytest-xdist
	uv run pytest tests -q -n auto

test-unit: ## Run unit tests in parallel
	uv run pytest tests -q -n auto -m "not integration and not slow"

test-integration: ## Run integration tests serially
	uv run pytest tests -q -m "integration"

test-cov: ## Run tests with coverage
	uv run pytest tests --cov=stringdb_link --cov-report=term-missing --cov-report=html --cov-report=xml

test-all: test-cov ## Alias for full test run with coverage

check: format lint ## Format and lint

ci-local: format-check lint-ci lint-loc typecheck-fast test-fast ## Run fast local CI-equivalent checks

precommit: ci-local ## Run checks expected before commit

clean: ## Remove local caches and generated reports
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage coverage.xml

dev: ## Start REST plus MCP development server
	uv run python server.py --transport unified --host 127.0.0.1 --port 8000

mcp-serve: ## Start local stdio MCP server
	uv run python mcp_server.py

mcp-serve-http: ## Start hosted MCP endpoint with REST API
	uv run python server.py --transport unified --host 0.0.0.0 --port 8000

docker-build: ## Build Docker image
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml build

docker-up: ## Start Docker services
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml up -d

docker-down: ## Stop Docker services
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml down

docker-logs: ## Tail Docker service logs
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml logs -f
```

- [ ] **Step 2: Smoke the Makefile**

Run:

```bash
make help
```

Expected: a list of available targets.

- [ ] **Step 3: Commit Makefile**

Run:

```bash
git add Makefile
git commit -m "build: add local development Makefile"
```

## Task 5: Add File Size Budget Enforcement

**Files:**
- Create: `scripts/check_file_size.py`
- Create: `.loc-allowlist`

- [ ] **Step 1: Create script directory**

Run:

```bash
mkdir -p scripts
```

- [ ] **Step 2: Add `scripts/check_file_size.py`**

Create:

```python
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MAX_LINES = 600
ALLOWLIST = ROOT / ".loc-allowlist"
CHECK_ROOTS = [ROOT / "stringdb_link", ROOT / "server.py", ROOT / "mcp_server.py"]


def load_allowlist() -> dict[str, int]:
    entries: dict[str, int] = {}
    if not ALLOWLIST.exists():
        return entries

    for line_number, raw_line in enumerate(ALLOWLIST.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        path, separator, ceiling = line.partition(":")
        if not separator:
            raise ValueError(
                f"{ALLOWLIST}:{line_number}: expected repo-relative path and LOC ceiling"
            )
        entries[path] = int(ceiling)
    return entries


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in CHECK_ROOTS:
        if root.is_file() and root.suffix == ".py":
            files.append(root)
        elif root.is_dir():
            files.extend(path for path in root.rglob("*.py") if "tests" not in path.parts)
    return sorted(files)


def line_count(path: Path) -> int:
    return len(path.read_text().splitlines())


def main() -> int:
    allowlist = load_allowlist()
    failures: list[str] = []

    for path in iter_python_files():
        relative = path.relative_to(ROOT).as_posix()
        count = line_count(path)
        ceiling = allowlist.get(relative, MAX_LINES)
        if count > ceiling:
            failures.append(f"{relative}: {count} lines exceeds ceiling {ceiling}")

    if failures:
        print("File size budget failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Add `.loc-allowlist`**

Use actual counts from Task 1:

```text
# Grandfathered Python modules exceeding the 600-LOC budget.
#
# Format: repo-relative path, colon, ceiling LOC
# - Ceiling is the file's current line count at allowlist time.
# - Files may shrink freely; growing past the ceiling fails CI.
# - Removing an entry after a successful split is the goal.
#
# Decomposition backlog: docs/superpowers/specs/2026-05-25-modernize-python-stack-and-agent-workflow-design.md

stringdb_link/api/client.py:796
stringdb_link/services/stringdb_service.py:771
stringdb_link/models/requests.py:682
stringdb_link/models/responses.py:634
```

- [ ] **Step 4: Run line-budget check**

Run:

```bash
uv run python scripts/check_file_size.py
```

Expected: no output and exit code 0.

- [ ] **Step 5: Commit line-budget tooling**

Run:

```bash
git add scripts/check_file_size.py .loc-allowlist
git commit -m "chore: add agent-friendly file size budget"
```

## Task 6: Add Agent Instruction Files

**Files:**
- Create: `AGENTS.md`
- Create: `CLAUDE.md`

- [ ] **Step 1: Create `AGENTS.md`**

Add:

```markdown
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

Useful focused commands:

- `make install`
- `make lock`
- `make format`
- `make lint`
- `make lint-fix`
- `make lint-loc`
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
```

- [ ] **Step 2: Create `CLAUDE.md`**

Add:

```markdown
# CLAUDE.md

@AGENTS.md

Claude Code entrypoint only:

- Use `AGENTS.md` for shared repository instructions.
- Keep Claude-specific additions here short and tool-specific.
- Prefer `make ci-local` before final handoff. It runs `lint-loc`, which
  enforces the 600-LOC per-file budget.
- When planning an edit that would push a `stringdb_link/` module past
  ~500 lines, propose a split first rather than growing the file.
- When a split is required, prefer cohesive sub-modules under a package
  directory; keep existing public facades stable so call sites do not churn.
```

- [ ] **Step 3: Commit agent docs**

Run:

```bash
git add AGENTS.md CLAUDE.md
git commit -m "docs: add shared agent instructions"
```

## Task 7: Update Pre-commit Hooks

**Files:**
- Modify: `.pre-commit-config.yaml`

- [ ] **Step 1: Replace pre-commit config**

Use:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy stringdb_link server.py mcp_server.py
        language: system
        pass_filenames: false

      - id: file-size-budget
        name: per-file line budget (see AGENTS.md "File Size Discipline")
        entry: uv run python scripts/check_file_size.py
        language: system
        pass_filenames: false
        files: ^(stringdb_link/|server\.py$|mcp_server\.py$|\.loc-allowlist$)
```

- [ ] **Step 2: Validate pre-commit config**

Run:

```bash
uv run pre-commit run --all-files
```

Expected: hooks run. Formatting hooks may modify files; inspect and include
those changes if they are only mechanical formatting.

- [ ] **Step 3: Commit pre-commit modernization**

Run:

```bash
git add .pre-commit-config.yaml
git commit -m "chore: modernize pre-commit hooks"
```

## Task 8: Add Superpowers Directory README

**Files:**
- Create: `docs/superpowers/README.md`

- [ ] **Step 1: Create README**

Add:

```markdown
# Superpowers

This directory stores design specs and implementation plans for agentic work.

- `specs/` contains reviewed design documents.
- `plans/` contains task-by-task implementation plans.

Plans are written so Claude Code, Codex, and other LLM coding agents can
execute them incrementally with verification checkpoints.
```

- [ ] **Step 2: Commit README**

Run:

```bash
git add docs/superpowers/README.md
git commit -m "docs: describe agentic planning docs"
```

## Task 9: Run Verification

**Files:**
- Inspect generated changes only

- [ ] **Step 1: Format**

Run:

```bash
make format
```

Expected: Ruff formats Python files. Inspect formatting changes before commit.

- [ ] **Step 2: Run focused checks**

Run:

```bash
make lint-loc
make test
```

Expected: both pass.

- [ ] **Step 3: Run local CI**

Run:

```bash
make ci-local
```

Expected: pass. If strict lint or typecheck reveals existing debt, capture the
exact failing command and top failures in the handoff. Do not silently weaken
the target configuration.

- [ ] **Step 4: Commit final mechanical changes**

If `make format` or pre-commit changed files, run:

```bash
git add stringdb_link tests server.py mcp_server.py pyproject.toml .pre-commit-config.yaml
git commit -m "style: apply modern formatter output"
```

Skip this commit if there are no additional changes.

## Task 10: Final Handoff

**Files:**
- Inspect: `git status --short`

- [ ] **Step 1: Check final status**

Run:

```bash
git status --short
```

Expected: clean worktree or only intentionally uncommitted user changes.

- [ ] **Step 2: Summarize verification**

Report:

```text
Modernization complete.

Changed:
- Hatchling + Python 3.12+ project metadata
- uv lockfile and dependency groups
- Makefile command surface
- agent docs for Claude Code/Codex/LLM workers
- pre-commit modernization
- file-size budget enforcement with grandfathered oversized modules

- uv lock completed successfully.
- uv sync --group dev completed successfully.
- make lint-loc completed successfully.
- make test completed successfully.
- make ci-local completed successfully.
```

If a command fails because of existing code debt exposed by the stricter stack,
replace the corresponding success sentence with the exact command, exit status,
and the first actionable error group.
