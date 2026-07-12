"""Outbound-URL guard + response byte cap for the StringDB HTTP client (F-17).

The STRING API is reached over ``follow_redirects=True`` because the generic
``string-db.org`` host issues a stable-address redirect to the pinned versioned
host (``version-12-0.string-db.org``) and STRING is a **POST** API — keeping
httpx's redirect machinery is the only way the form body is method/body-handled
correctly across that hop (a hand-rolled loop would drop it). This module adds
the two guardrails that a raw ``follow_redirects=True`` lacks:

* a request **event-hook** that validates *every* outgoing hop (including
  auto-followed redirects): ``https`` scheme, host in an EXACT allowlist derived
  from the configured base URL, and no ``user:pass@`` userinfo; and
* a streaming reader that **fails closed** past a byte ceiling — a truncated
  JSON/TSV/XML/PNG body is unparseable or corrupt, so the cap raises rather than
  silently returning a short read.

Both guard exceptions are deliberately plain ``Exception`` subclasses so they do
NOT match the client's retryable ``httpx.TimeoutException`` / ``httpx.RequestError``
handlers — a disallowed URL or oversized body is non-retryable.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit

import httpx

# Fail-closed successful-response ceiling. Sized ABOVE the 8 MiB untrusted-text
# fence and STRING's multi-MB network images (spec §4 Recipe B table: 32 MiB).
MAX_RESPONSE_BYTES = 32 * 1024 * 1024

# Bound the redirect chain; STRING's generic->versioned hop is a single redirect.
MAX_REDIRECTS = 5

# STRING's generic host issues a documented stable-address redirect to the pinned
# versioned host; both must be allowlisted so that redirect is permitted.
GENERIC_STRING_HOST = "string-db.org"


class DisallowedURLError(Exception):
    """An outbound request/redirect targets a non-allowlisted URL. NON-RETRYABLE."""


class ResponseTooLargeError(Exception):
    """A successful response exceeded the byte ceiling before parsing. NON-RETRYABLE."""


def build_host_allowlist(*base_urls: str) -> frozenset[str]:
    """Derive an exact-host allowlist from configured base URL(s).

    Hosts are never hardcoded: a STRING version bump changes the versioned host
    (``version-N-N.string-db.org``) and the base URL is operator-overridable, so
    the allowlist is seeded from the configured URL(s) at client-build time.
    """
    hosts: set[str] = set()
    for url in base_urls:
        host = urlsplit(url).hostname
        if host:
            hosts.add(host.lower())
    return frozenset(hosts)


def stringdb_allowed_hosts(base_url: str) -> frozenset[str]:
    """Allowlist for the STRING client: the configured (versioned) host + generic.

    Production pins ``version-12-0.string-db.org`` (derived from ``base_url`` so a
    version bump follows the config), plus the generic ``string-db.org`` host that
    stable-address-redirects to it. Both are permitted; every other host is not.
    """
    return build_host_allowlist(base_url, f"https://{GENERIC_STRING_HOST}")


def make_url_guard(
    allowed_hosts: frozenset[str],
) -> Callable[[httpx.Request], Awaitable[None]]:
    """Build an httpx request event-hook that validates every outgoing hop."""

    async def _guard(request: httpx.Request) -> None:
        url = request.url
        if url.scheme != "https":
            raise DisallowedURLError(f"non-https scheme: {url.scheme}")
        if url.username or url.password:
            raise DisallowedURLError("userinfo not permitted in outbound URL")
        host = (url.host or "").lower()
        if host not in allowed_hosts:
            raise DisallowedURLError(f"host not allowlisted: {host}")

    return _guard


async def read_capped(response: httpx.Response, max_bytes: int) -> bytes:
    """Stream a response body, raising past ``max_bytes`` (fail closed).

    Must be called inside an open ``client.stream(...)`` context. Accumulation is
    the authoritative check (``Content-Length`` is unreliable under chunked/gzip);
    the body is never truncated — exceeding the cap raises ``ResponseTooLargeError``.
    """
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > max_bytes:
            raise ResponseTooLargeError(f"response exceeded {max_bytes} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


async def stream_capped(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_bytes: int,
    **kwargs: Any,
) -> tuple[httpx.Response, bytes | None]:
    """Send a request and return ``(response, body)``.

    ``body`` is the byte-capped payload for a ``200`` response, else ``None`` (a
    non-2xx body is caller-influenceable and is never read/retained). The request
    event-hook validates every redirect hop before this returns.
    """
    async with client.stream(method, url, **kwargs) as response:
        body = (
            await read_capped(response, max_bytes)
            if response.status_code == httpx.codes.OK
            else None
        )
    return response, body
