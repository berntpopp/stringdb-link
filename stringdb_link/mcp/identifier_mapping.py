"""Per-input identifier mapping for every tool that takes ``identifiers``.

genefoundry-router #343: STRING's network, enrichment and annotation endpoints map
each input internally and never say which inputs they used, so an input STRING
could not read vanished without a trace. This asks STRING's own mapper
(``get_string_ids``) about the same inputs and species and reports each one as
``mapped`` or ``unmapped``. STRING decides what resolves; nothing is mapped here.

``get_string_ids`` returns ONE row per protein: when several inputs name the same
protein (``ENSG00000133703``, ``HGNC:6407`` and ``3845`` are all KRAS) only one of
them gets a row. The inputs without a row are therefore asked again, so "named a
protein another input already named" is never mistaken for "unmapped".

The lookup is an annotation on the tool's answer, so it must never slow or fail it:
it runs beside the main call as a task, is bounded by
``STRINGDB_API__IDENTIFIER_MAPPING_TIMEOUT``, is cached per (inputs, species) and
uses ONE client, so STRING's rate limit holds across tool calls.
"""

from __future__ import annotations

import asyncio
from typing import Any

from stringdb_link.api.client import StringDBClient
from stringdb_link.config import get_settings, settings
from stringdb_link.mcp.untrusted_content import sanitize_message
from stringdb_link.utils.caching import cache_manager

# ponytail: 4 upstream calls at most per tool call; raise if real requests name one
# protein more often than that.
_MAX_ROUNDS = 4
_MAX_ECHO_CHARS = 64
_ERROR_GRACE_SECONDS = 1.0
_UNMAPPED = "STRING's identifier mapping found no protein for this input in the queried species"
_UNDETERMINED = f"not determined within {_MAX_ROUNDS} lookups"
UNAVAILABLE = {"identifier_mapping": "unavailable: could not ask STRING which inputs mapped"}

_client: StringDBClient | None = None


def _shared_client() -> StringDBClient:
    """One client for every mapping lookup, so its rate limiter spans tool calls."""
    global _client
    if _client is None:
        _client = StringDBClient(caller_identity=get_settings().stringdb_api.caller_identity)
    return _client


@cache_manager.cached(
    maxsize=1000, ttl=settings.cache_identifier_ttl, cache_name="identifier_mapping"
)
async def _ask_string(identifiers: tuple[str, ...], species: int | None) -> list[dict[str, Any]]:
    """One ``get_string_ids`` call; cached like the repo's other identifier lookups."""
    rows = await _shared_client().get_string_ids(list(identifiers), species, echo_query=True)
    return rows if isinstance(rows, list) else []


def _echo(text: object) -> str:
    """Caller and upstream text as it may be echoed: no control/bidi chars, capped."""
    return sanitize_message(str(text))[:_MAX_ECHO_CHARS]


async def map_identifiers(
    identifiers: list[str],
    species: int | None,
    first_rows: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Ask STRING which protein each input names. Returns ``{"mapped", "unmapped"}``.

    ``first_rows`` are ``get_string_ids`` rows the caller already holds for the full
    list (``resolve_protein_identifiers``), so that list is not asked twice.
    """
    remaining = list(dict.fromkeys(i.strip() for i in identifiers if i.strip()))
    mapped: dict[str, dict[str, str]] = {}
    reason = _UNDETERMINED
    for round_number in range(_MAX_ROUNDS):
        if not remaining:
            break
        if round_number == 0 and first_rows is not None:
            rows = first_rows
        else:
            rows = await _ask_string(tuple(remaining), species)
        found: dict[str, dict[str, str]] = {}
        for row in rows:  # best match first: keep the first row per input
            index = row.get("queryIndex")
            if isinstance(index, int) and 0 <= index < len(remaining):
                found.setdefault(
                    remaining[index],
                    {
                        "string_id": _echo(row.get("stringId", "")),
                        "preferred_name": _echo(row.get("preferredName", "")),
                    },
                )
        if not found:
            reason = _UNMAPPED
            break
        taxa = {row.get("ncbiTaxonId") for row in rows}
        if species is None and len(taxa) == 1 and isinstance(next(iter(taxa)), int):
            # No species given: STRING guessed one for the full list. Pin it, so a
            # shorter re-ask list cannot be guessed into a different species.
            species = next(iter(taxa))
        mapped.update(found)
        remaining = [i for i in remaining if i not in found]
    return {
        "mapped": [{"input": _echo(i), **protein} for i, protein in mapped.items()],
        "unmapped": [{"input": _echo(i), "reason": reason} for i in remaining],
    }


def start(
    arguments: dict[str, Any], first_rows: list[dict[str, Any]] | None = None
) -> asyncio.Task[dict[str, Any]] | None:
    """Start the lookup for one tool call; None when the tool takes no identifiers."""
    identifiers = arguments.get("identifiers")
    if not isinstance(identifiers, list) or not all(isinstance(i, str) for i in identifiers):
        return None
    species = arguments.get("species")
    return asyncio.create_task(
        map_identifiers(identifiers, species if isinstance(species, int) else None, first_rows)
    )


def discard(task: asyncio.Task[dict[str, Any]] | None) -> None:
    """Drop a lookup nobody will read: cancel it, or collect its error if it has one."""
    if task is None:
        return
    if not task.done():
        task.cancel()
    elif not task.cancelled():
        task.exception()


async def finish(
    task: asyncio.Task[dict[str, Any]] | None, *, after_error: bool = False
) -> dict[str, Any] | None:
    """The mapping block, waiting at most the configured time. Never raises.

    A lookup that is late or failed yields the "unavailable" note, so the caller is
    not left to assume every input was used. ``wait_for`` cancels a late task.
    After a failed main call the wait is at most one second: if STRING answered the
    main call the lookup is back by then, and if STRING is down nothing waits on it.
    """
    if task is None:
        return None
    timeout = get_settings().stringdb_api.identifier_mapping_timeout
    if after_error:
        timeout = min(timeout, _ERROR_GRACE_SECONDS)
    try:
        return dict(await asyncio.wait_for(task, timeout))
    except Exception:  # timeout, upstream or parsing: the tool's own answer stands
        return dict(UNAVAILABLE)
