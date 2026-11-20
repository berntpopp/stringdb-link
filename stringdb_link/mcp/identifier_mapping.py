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
"""

from __future__ import annotations

from typing import Any

from stringdb_link.api.client import StringDBClient
from stringdb_link.config import get_settings
from stringdb_link.logging_config import get_logger
from stringdb_link.models.requests import IdentifierRequest
from stringdb_link.services.stringdb_service import StringDBService

# ponytail: 4 upstream calls at most; a 5th input naming one protein is reported
# as undetermined. Raise if real requests repeat one protein that often.
_MAX_ROUNDS = 4
_UNMAPPED = "STRING's identifier mapping found no protein for this input in the queried species"
_UNDETERMINED = "not determined: several inputs name the same protein; resolve this one on its own"


async def map_identifiers(
    service: StringDBService, identifiers: list[str], species: int | None
) -> dict[str, list[dict[str, str]]]:
    """Ask STRING which protein each input names. Returns ``{"mapped", "unmapped"}``."""
    remaining = list(dict.fromkeys(i.strip() for i in identifiers if i.strip()))
    mapped: dict[str, dict[str, str]] = {}
    reason = _UNDETERMINED
    for _ in range(_MAX_ROUNDS):
        if not remaining:
            break
        response = await service.resolve_identifiers(
            IdentifierRequest(identifiers=remaining, species=species, echo_query=True)
        )
        found: dict[str, dict[str, str]] = {}
        for row in response.mappings:  # best match first: keep the first row per input
            if 0 <= row.query_index < len(remaining):
                found.setdefault(
                    remaining[row.query_index],
                    {"string_id": row.string_id, "preferred_name": row.preferred_name},
                )
        if not found:
            reason = _UNMAPPED
            break
        mapped.update(found)
        remaining = [i for i in remaining if i not in found]
    return {
        "mapped": [{"input": i, **protein} for i, protein in mapped.items()],
        "unmapped": [{"input": i, "reason": reason} for i in remaining],
    }


async def mapping_for_arguments(arguments: dict[str, Any]) -> dict[str, Any] | None:
    """The mapping block for one tool call, or None when it takes no identifiers.

    Never fails the tool: if the mapper cannot be reached the block says so
    instead of leaving the caller to assume every input was used.
    """
    identifiers = arguments.get("identifiers")
    if not isinstance(identifiers, list) or not all(isinstance(i, str) for i in identifiers):
        return None
    species = arguments.get("species")
    client = StringDBClient(caller_identity=get_settings().stringdb_api.caller_identity)
    try:
        service = StringDBService(client=client, logger=get_logger("stringdb_mcp"))
        return dict(
            await map_identifiers(
                service, identifiers, species if isinstance(species, int) else None
            )
        )
    except Exception:  # the mapping is an annotation; the tool's own answer stands
        return {"identifier_mapping": "unavailable: could not ask STRING which inputs mapped"}
    finally:
        await client.close()
