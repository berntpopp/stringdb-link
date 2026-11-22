"""Upstream STRING faults keep their class through the service layer (#130).

A STRING outage, timeout or rate limit must reach the MCP envelope as
``upstream_unavailable`` / ``rate_limited`` (retryable), not the flattened
``internal`` a bare ``StringDBServiceError`` used to default to. Only a genuine
local bug stays 500 -> ``internal``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import structlog
from fastmcp import Client

from stringdb_link.api.url_guard import (
    DisallowedURLError,
    RedirectBodyLossError,
    ResponseTooLargeError,
    build_host_allowlist,
    make_url_guard,
)
from stringdb_link.exceptions import (
    NetworkError,
    StringDBAPIError,
    StringDBRateLimitError,
    StringDBServiceError,
    StringDBTimeoutError,
)
from stringdb_link.models.requests import (
    AnnotationRequest,
    EnrichmentRequest,
    IdentifierRequest,
    ImageRequest,
    InteractionPartnersRequest,
    LinkRequest,
    NetworkRequest,
    PPIEnrichmentRequest,
)
from stringdb_link.services.stringdb_service import StringDBService
from stringdb_link.utils.caching import cache_manager

_IDS = ["9606.ENSP00000130130", "9606.ENSP00000130131"]

# (service method, client method it delegates to, call args)
_METHODS: list[tuple[str, str, tuple[Any, ...]]] = [
    ("resolve_identifiers", "get_string_ids", (IdentifierRequest(identifiers=_IDS, species=9606),)),
    (
        "get_network_interactions",
        "get_network_interactions",
        (NetworkRequest(identifiers=_IDS, species=9606),),
    ),
    (
        "get_interaction_partners",
        "get_interaction_partners",
        (InteractionPartnersRequest(identifiers=_IDS, species=9606),),
    ),
    (
        "get_functional_enrichment",
        "get_functional_enrichment",
        (EnrichmentRequest(identifiers=_IDS, species=9606),),
    ),
    (
        "get_functional_annotation",
        "get_functional_annotation",
        (AnnotationRequest(identifiers=_IDS, species=9606),),
    ),
    ("get_network_image", "get_network_image", (ImageRequest(identifiers=_IDS, species=9606),)),
    ("get_homology_scores", "get_homology_scores", (_IDS, 9606)),
    ("get_homology_best_hits", "get_homology_best_hits", (_IDS, 9606, [10090])),
    (
        "get_ppi_enrichment",
        "get_ppi_enrichment",
        (PPIEnrichmentRequest(identifiers=_IDS, species=9606),),
    ),
    ("get_network_link", "get_link", (LinkRequest(identifiers=_IDS, species=9606),)),
]

_FAULTS: list[tuple[Exception, int]] = [
    (StringDBAPIError("StringDB server error: 500", status_code=500), 502),
    (StringDBAPIError("StringDB server error: 503", status_code=503), 502),
    (StringDBAPIError("Unexpected error accessing x"), 502),
    (StringDBAPIError("StringDB API error: 404", status_code=404), 502),
    (StringDBAPIError("StringDB API error: 400", status_code=400), 400),
    (StringDBTimeoutError(timeout=30.0), 504),
    (NetworkError("connection refused", original_error=httpx.ConnectError("x")), 502),
    (StringDBRateLimitError(retry_after=5), 429),
    (RuntimeError("local bug"), 500),
    # Outbound HTTP-policy rejections (#132): each its own status, never 500.
    (DisallowedURLError("outbound request blocked by HTTP policy"), 508),
    (ResponseTooLargeError("upstream response exceeds HTTP policy byte limit"), 507),
    (RedirectBodyLossError("redirect dropped the POST body"), 510),
]


@pytest.fixture(autouse=True)
async def _clear_caches() -> None:
    await cache_manager.clear_all_caches()


@pytest.mark.parametrize(
    ("method", "client_method", "args"), _METHODS, ids=[m[0] for m in _METHODS]
)
@pytest.mark.parametrize(
    ("fault", "status"), _FAULTS, ids=[f"{type(f[0]).__name__}-{f[1]}" for f in _FAULTS]
)
async def test_service_method_keeps_upstream_status(
    method: str, client_method: str, args: tuple[Any, ...], fault: Exception, status: int
) -> None:
    client = AsyncMock()
    getattr(client, client_method).side_effect = fault
    service = StringDBService(client=client, logger=MagicMock())

    with pytest.raises(StringDBServiceError) as exc_info:
        await getattr(service, method)(*args)

    assert exc_info.value.status_code == status
    assert exc_info.value.original_error is fault


@pytest.mark.parametrize(
    ("fault", "error_code", "retryable"),
    [
        (
            StringDBAPIError("StringDB server error: 500", status_code=500),
            "upstream_unavailable",
            True,
        ),
        (StringDBTimeoutError(timeout=30.0), "upstream_unavailable", True),
        (StringDBRateLimitError(retry_after=5), "rate_limited", True),
        (RuntimeError("local bug"), "internal", False),
    ],
)
async def test_mcp_partners_upstream_fault_envelope(
    facade: Any, fault: Exception, error_code: str, retryable: bool
) -> None:
    with patch(
        "stringdb_link.api.client.StringDBClient.get_interaction_partners",
        new_callable=AsyncMock,
        side_effect=fault,
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_interaction_partners",
                {"identifiers": ["UPSTREAM130"], "species": 9606},
                raise_on_error=False,
            )

    body = result.structured_content
    assert body is not None
    assert body["error_code"] == error_code
    assert body["retryable"] is retryable


async def test_cache_wrapper_does_not_log_upstream_fault_as_cache_error() -> None:
    """A fault raised BY the wrapped call is not a cache fault (no "Cache error")."""
    logger = MagicMock()
    manager = type(cache_manager)(logger=logger, enabled=True)

    @manager.cached(maxsize=10, ttl=60, cache_name="upstream_fault_test")
    async def fetch(arg: str) -> str:
        raise StringDBAPIError("StringDB server error: 500", status_code=500)

    with pytest.raises(StringDBAPIError):
        await fetch("x")

    messages = [c.args[0] for c in logger.exception.call_args_list + logger.error.call_args_list]
    assert "Cache error" not in messages


async def test_cache_wrapper_still_logs_real_cache_fault() -> None:
    """A failure of the cache itself (unhashable key) is still a "Cache error"."""
    logger = MagicMock()
    manager = type(cache_manager)(logger=logger, enabled=True)

    @manager.cached(maxsize=10, ttl=60, cache_name="cache_fault_test")
    async def fetch(arg: list[str]) -> str:
        return "ok"

    with pytest.raises(TypeError):
        await fetch(["unhashable"])

    assert [c.args[0] for c in logger.exception.call_args_list] == ["Cache error"]


async def test_mcp_network_link_upstream_fault_is_not_internal(facade: Any) -> None:
    with patch(
        "stringdb_link.api.client.StringDBClient.get_link",
        new_callable=AsyncMock,
        side_effect=StringDBTimeoutError(timeout=30.0),
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_network_link",
                {"identifiers": ["UPSTREAM130"], "species": 9606},
                raise_on_error=False,
            )

    body = result.structured_content
    assert body is not None
    assert body["error_code"] == "upstream_unavailable"


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        (DisallowedURLError("x"), "blocked"),
        (ResponseTooLargeError("x"), "byte limit"),
        (RedirectBodyLossError("x"), "POST body"),
    ],
)
async def test_mcp_partners_policy_fault_envelope(
    facade: Any, fault: Exception, reason: str
) -> None:
    """An HTTP-policy rejection is a deterministic upstream fault, not ``internal`` (#132)."""
    with patch(
        "stringdb_link.api.client.StringDBClient.get_interaction_partners",
        new_callable=AsyncMock,
        side_effect=fault,
    ):
        async with Client(facade) as client:
            result = await client.call_tool(
                "get_interaction_partners",
                {"identifiers": ["POLICY132"], "species": 9606},
                raise_on_error=False,
            )

    body = result.structured_content
    assert body is not None
    assert body["error_code"] == "upstream_unavailable"
    assert body["error_subtype"] == "upstream_policy"
    assert body["retryable"] is False
    assert reason in body["message"]


async def test_guard_logs_reason_scheme_port_without_host_or_path() -> None:
    """A blocked hop logs WHY at WARNING; never the host (F-17) nor the path/query."""
    guard = make_url_guard(build_host_allowlist("https://version-12-5.string-db.org/api"))
    with structlog.testing.capture_logs() as logs, pytest.raises(DisallowedURLError):
        await guard(httpx.Request("GET", "http://evil.example:8080/secret?ids=TP53"))

    assert logs == [
        {
            "event": "outbound_url_blocked",
            "log_level": "warning",
            "reason": "non-https scheme",
            "scheme": "http",
            "port": 8080,
        }
    ]
