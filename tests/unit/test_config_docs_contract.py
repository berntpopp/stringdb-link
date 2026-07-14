"""The configuration docs and env templates are a contract, not prose.

README.md promises that ``docs/configuration.md`` documents *every* environment
variable, and ``docs/configuration.md`` states a default for each one. A
hand-typed table rots the moment a setting is added or a default changes, and a
README that lies is worse than no README — so these facts are pinned to the live
settings model here rather than trusted.

The env templates are pinned too: ``extra="ignore"`` means a misspelled key in
``.env`` is silently dropped, and ``MCP__SERVER_NAME`` is the federation identity
the router's registry and the conformance gate both assert.

Research use only; not clinical decision support."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from stringdb_link.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DOC = REPO_ROOT / "docs" / "configuration.md"
ENV_TEMPLATES = (
    REPO_ROOT / ".env.example",
    REPO_ROOT / ".env.docker.example",
    REPO_ROOT / ".env.npm.example",
)

# Ratified by .github/workflows/conformance.yml (CONFORMANCE_NAME) and by the
# genefoundry-router registry, which carries no server_name override for us.
RATIFIED_SERVER_NAME = "stringdb-link"

# The only setting whose default is a structured map. The doc names its keys
# instead of reproducing the JSON object, so its default cell is not compared —
# but the variable must still be documented like every other one.
STRUCTURED_DEFAULTS = frozenset({"STRINGDB_API__ENDPOINTS"})

_ENV_NAME = re.compile(r"[A-Z][A-Z0-9_]*")
_TABLE_ROW = re.compile(r"^\|(?P<name>[^|]+)\|(?P<default>[^|]*)\|")
_BACKTICKED = re.compile(r"`([^`]+)`")
_COMPOSE_INTERPOLATION = re.compile(r"\$\{([A-Z][A-Z0-9_]*)")


def _compose_interpolated_vars() -> set[str]:
    """Names the docker/ compose files interpolate (e.g. ${PUBLIC_DOMAIN}).

    The container templates legitimately carry these alongside app settings:
    they are consumed by compose, not by ``Settings``.
    """
    names: set[str] = set()
    for compose in (REPO_ROOT / "docker").glob("*.yml"):
        names.update(_COMPOSE_INTERPOLATION.findall(compose.read_text(encoding="utf-8")))
    return names


def _render_default(value: Any) -> str:
    """Render a settings default the way docs/configuration.md writes it."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def _live_settings(model: type[BaseModel], prefix: str = "") -> dict[str, str]:
    """Env var name -> rendered default, walked from the live settings model."""
    resolved: dict[str, str] = {}
    for name, field in model.model_fields.items():
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            resolved.update(_live_settings(annotation, f"{prefix}{name.upper()}__"))
        else:
            default = field.get_default(call_default_factory=True)
            resolved[f"{prefix}{name.upper()}"] = _render_default(default)
    return resolved


def _documented_settings() -> dict[str, str]:
    """Env var name -> documented default, parsed from configuration.md tables."""
    documented: dict[str, str] = {}
    for line in CONFIG_DOC.read_text(encoding="utf-8").splitlines():
        row = _TABLE_ROW.match(line)
        if row is None:
            continue
        names = [token for token in _BACKTICKED.findall(row["name"]) if _ENV_NAME.fullmatch(token)]
        defaults = _BACKTICKED.findall(row["default"])
        for name in names:
            documented[name] = defaults[0] if defaults else ""
    return documented


def _env_template_keys(path: Path) -> dict[str, str]:
    """KEY -> value for the assignments in an env template."""
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        entries[key.strip()] = value.strip()
    return entries


def test_configuration_md_documents_every_setting() -> None:
    """README's "every environment variable" claim is true, or CI fails."""
    live = set(_live_settings(Settings))
    documented = set(_documented_settings())

    undocumented = live - documented
    assert not undocumented, (
        "docs/configuration.md omits settable variables, so README's "
        f"'every environment variable' claim is false: {sorted(undocumented)}"
    )

    invented = documented - live
    assert not invented, (
        "docs/configuration.md documents variables the settings model does not "
        f"read (extra='ignore' makes them silent no-ops): {sorted(invented)}"
    )


def test_documented_defaults_match_the_settings_model() -> None:
    """Every documented default is the default the code actually sets."""
    live = _live_settings(Settings)
    documented = _documented_settings()

    wrong = {
        name: (documented[name], expected)
        for name, expected in live.items()
        if name not in STRUCTURED_DEFAULTS and documented.get(name) != expected
    }
    assert not wrong, f"documented default != code default (documented, actual): {wrong}"


def test_structured_default_is_still_documented() -> None:
    """The one map-valued setting is named in the docs, even if not rendered."""
    documented = _documented_settings()
    for name in STRUCTURED_DEFAULTS:
        assert name in documented


@pytest.mark.parametrize("template", ENV_TEMPLATES, ids=lambda p: p.name)
def test_env_template_keys_are_real_settings(template: Path) -> None:
    """A typo in a template is silently ignored at runtime — catch it here."""
    known = set(_live_settings(Settings)) | _compose_interpolated_vars()
    unknown = set(_env_template_keys(template)) - known
    assert not unknown, (
        f"{template.name} sets keys that neither the settings model reads "
        f"(extra='ignore' drops them silently) nor a compose file interpolates: "
        f"{sorted(unknown)}"
    )


@pytest.mark.parametrize("template", ENV_TEMPLATES, ids=lambda p: p.name)
def test_env_template_preserves_the_federation_identity(template: Path) -> None:
    """Copying a template must not rename the server out of the fleet registry."""
    server_name = _env_template_keys(template).get("MCP__SERVER_NAME")
    assert server_name in (None, RATIFIED_SERVER_NAME), (
        f"{template.name} would override serverInfo.name to {server_name!r}; "
        f"the router registry and conformance gate require {RATIFIED_SERVER_NAME!r}"
    )


@pytest.mark.parametrize("template", ENV_TEMPLATES, ids=lambda p: p.name)
def test_env_template_keeps_cors_credentials_off(template: Path) -> None:
    """The backend is unauthenticated: credentialed CORS is never correct."""
    credentials = _env_template_keys(template).get("CORS__ALLOW_CREDENTIALS", "false")
    assert credentials.lower() == "false", (
        f"{template.name} turns on credentialed CORS for an unauthenticated backend"
    )


def test_nested_list_variable_is_parsed_as_a_json_array(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The documented `SECTION__FIELD` + JSON-array env contract really holds."""
    monkeypatch.setenv("CORS__ALLOW_ORIGINS", '["https://example.org"]')
    settings = Settings(_env_file=None)
    assert settings.cors.allow_origins == ["https://example.org"]
