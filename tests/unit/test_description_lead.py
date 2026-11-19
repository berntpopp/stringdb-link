"""D1 description lead (Tool-Schema Documentation Standard v1.1, rule 7).

A tool description's first sentence must say what the tool returns, before usage advice.
ponytail: copied from genefoundry-router scripts/surface.py (lead_states_return); re-vendor
byte-identically if this repo ever vendors surface.py.
"""

from __future__ import annotations

import re
from typing import Any

LEAD_CHARS = 300
_LEAD_VERBS = [
    "get",
    "fetch",
    "retrieve",
    "list",
    "look",
    "lookup",
    "search",
    "find",
    "resolve",
    "report",
    "read",
    "predict",
    "annotate",
    "compute",
    "calculate",
    "count",
    "summarize",
    "summarise",
    "map",
    "translate",
    "convert",
    "describe",
    "show",
    "check",
    "validate",
    "classify",
    "score",
    "rank",
    "query",
    "browse",
    "discover",
    "explain",
    "compare",
    "diff",
    "normalize",
    "normalise",
    "expand",
    "evaluate",
    "assess",
    "enumerate",
    "identify",
    "locate",
    "export",
    "download",
    "match",
    "suggest",
    "recommend",
    "inspect",
    "generate",
    "render",
    "estimate",
]
_VERB_LEAD = re.compile(
    rf"^(?:use this (?:tool )?to )?(?:{'|'.join(_LEAD_VERBS)})(?:s|es|ies)?\b", re.IGNORECASE
)
_RETURNS = re.compile(
    r"(?<!not )(?<!n't )(?<!n\u2019t )(?<!never )\breturn(?:s|ed|ing)?\b(?!\s*[~<\d])|\u2192|->",
    re.IGNORECASE,
)
_FIELD_LIST = re.compile(r"\w+\W+\w+[^:]*:\s+[^.;:]+,")
_SENTENCE_END = re.compile(r"(?<!e\.g\.)(?<!i\.e\.)(?<=[.!?])\s+")


def lead_states_return(description: str | None) -> bool:
    text = " ".join((description or "").split())
    lead = _SENTENCE_END.split(text, maxsplit=1)[0][:LEAD_CHARS]
    return bool(_VERB_LEAD.match(lead) or _RETURNS.search(lead) or _FIELD_LIST.search(lead))


async def test_every_tool_description_leads_with_what_it_returns(facade: Any) -> None:
    tools = await facade.list_tools()
    assert tools
    failing = sorted(t.name for t in tools if not lead_states_return(t.description))
    assert not failing, f"D1: first sentence must state what is returned: {failing}"


async def test_pinned_partner_lead_names_fields_that_are_returned(facade: Any) -> None:
    """Contract truth: every field the pinned tool's lead promises is in the response."""
    from unittest.mock import AsyncMock, patch

    from fastmcp import Client

    from stringdb_link.models.responses import InteractionPartnerListResponse
    from tests.unit.test_response_envelope_v1 import _PARTNER

    with patch(
        "stringdb_link.services.stringdb_service.StringDBService.get_interaction_partners",
        new_callable=AsyncMock,
        return_value=InteractionPartnerListResponse(partners=[_PARTNER], total_count=1),
    ):
        async with Client(facade) as client:
            result = await client.call_tool("get_interaction_partners", {"identifiers": ["TP53"]})
    body = result.structured_content
    assert {"preferredName_B", "stringId_B", "score"} <= body["results"][0].keys()
    assert {"total_count", "truncated"} <= body.keys()
