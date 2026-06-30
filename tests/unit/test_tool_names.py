"""Tool-name compliance with the GeneFoundry Tool-Naming Standard v1.1.

Every registered tool must be unprefixed, snake_case, <= 50 chars, and start with
a canonical verb so it composes cleanly behind the ``genefoundry-router`` gateway,
which mounts this server under the ``stringdb`` namespace (tools surface as
``stringdb_<tool>``). Guards against future drift — tool names here are generated
by ``FastMCP.from_fastapi`` from each route's ``operation_id``, so a new route can
silently introduce a non-compliant tool. See issue berntpopp/stringdb-link#1.

**Ratified verb canon (v1.1):**

  Tier-1 (universal read/query): get, search, list, resolve, find, compare,
  compute, map
  Tier-2 (sanctioned action/compute): predict, annotate, recode, liftover,
  analyze, score, submit, export, generate, download

Ops/meta tools (tagged ``ops``/``meta``) are exempt from the verb rule but must
still pass charset, length, and no-self-prefix checks.
"""

from __future__ import annotations

import re
from typing import Any

_NAME_RE = re.compile(r"^[a-z0-9_]{1,50}$")
# Tier-1: universal read/query canon (Tool-Naming Standard v1.1, ratified 2026-06-30)
_CANONICAL_VERBS = frozenset(
    {"get", "search", "list", "resolve", "find", "compare", "compute", "map"}
)
# Tier-2: sanctioned domain action/compute verbs (v1.1)
_TIER2_VERBS = frozenset(
    {
        "predict",
        "annotate",
        "recode",
        "liftover",
        "analyze",
        "score",
        "submit",
        "export",
        "generate",
        "download",
    }
)
_NAMESPACE = "stringdb"


async def test_tool_names_conform_to_standard_v1(facade: Any) -> None:
    names = sorted(t.name for t in await facade.list_tools())
    assert names, "no tools registered on the facade"
    _all_verbs = _CANONICAL_VERBS | _TIER2_VERBS
    for name in names:
        assert _NAME_RE.match(name), f"{name!r} must match ^[a-z0-9_]{{1,50}}$"
        assert name.split("_", 1)[0] in _all_verbs, (
            f"{name!r} must start with a Tier-1 or Tier-2 canonical verb {sorted(_all_verbs)}"
        )
        assert not name.startswith(f"{_NAMESPACE}_"), (
            f"{name!r} must not self-prefix the '{_NAMESPACE}' namespace "
            "token -- the gateway adds it"
        )
