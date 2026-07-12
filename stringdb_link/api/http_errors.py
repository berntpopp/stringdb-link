"""HTTP status -> typed-exception mapping for the StringDB client.

These helpers key the raised error on the HTTP status only. The upstream
response BODY is deliberately never read or retained: it is caller-influenceable
(a caller-supplied query can make STRING reflect hostile prose / control code
points into it) and must never enter the exception cause graph, a log record, or
-- via the MCP boundary -- a caller-visible message.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from stringdb_link.exceptions import StringDBAPIError, StringDBRateLimitError

if TYPE_CHECKING:
    import httpx


def raise_rate_limit_error(endpoint: str, response: httpx.Response) -> NoReturn:
    """Raise a rate-limit error, honouring the ``Retry-After`` header."""
    retry_after = int(response.headers.get("Retry-After", 60))
    msg = f"Rate limit exceeded for endpoint {endpoint}"
    raise StringDBRateLimitError(msg, retry_after=retry_after, endpoint=endpoint)


def raise_server_error(endpoint: str, response: httpx.Response) -> NoReturn:
    """Raise a server (5xx) error keyed only by status."""
    msg = f"StringDB server error: {response.status_code}"
    raise StringDBAPIError(msg, status_code=response.status_code, endpoint=endpoint)


def raise_client_error(endpoint: str, response: httpx.Response) -> NoReturn:
    """Raise a client (4xx) error keyed only by status (body never read)."""
    msg = f"StringDB API error: {response.status_code}"
    raise StringDBAPIError(msg, status_code=response.status_code, endpoint=endpoint)
