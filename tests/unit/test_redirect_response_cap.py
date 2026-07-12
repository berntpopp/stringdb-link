"""F-17: outbound redirect hops and successful-response sizes are bounded.

STRING is a POST API served from a *versioned* host (production pins
``version-12-0.string-db.org``); the generic ``string-db.org`` host issues a
stable-address redirect to the versioned host. The hardening therefore keeps
httpx's redirect machinery (``follow_redirects=True``) so the POST form body is
handled correctly, and layers a request event-hook that validates *every* hop
(scheme == https, host in an EXACT allowlist derived from the configured base
URL, no userinfo) plus a fail-closed 32 MiB response byte cap.

A manual disable-and-loop would silently drop the POST form body on the
generic->versioned redirect; these tests pin the event-hook behaviour instead.
"""

from __future__ import annotations

import logging

import httpx
import pytest

from stringdb_link.api.client import StringDBClient
from stringdb_link.api.url_guard import (
    GENERIC_STRING_HOST,
    DisallowedURLError,
    RedirectBodyLossError,
    ResponseTooLargeError,
    build_host_allowlist,
    check_no_redirect_method_change,
    make_url_guard,
)

VERSIONED_BASE = "https://version-12-0.string-db.org/api"
GENERIC_BASE = "https://string-db.org/api"


def _versioned_url(path: str = "/api/json/network") -> str:
    return f"https://version-12-0.string-db.org{path}"


# --------------------------------------------------------------------------- #
# build_host_allowlist / make_url_guard (pure unit)                           #
# --------------------------------------------------------------------------- #


def test_build_host_allowlist_derives_from_base_url() -> None:
    allow = build_host_allowlist(VERSIONED_BASE, f"https://{GENERIC_STRING_HOST}")
    assert allow == frozenset({("version-12-0.string-db.org", 443), ("string-db.org", 443)})


@pytest.mark.asyncio
async def test_guard_allows_both_allowlisted_hosts() -> None:
    guard = make_url_guard(build_host_allowlist(VERSIONED_BASE, f"https://{GENERIC_STRING_HOST}"))
    # Neither of the two documented STRING hosts may be rejected.
    await guard(httpx.Request("POST", _versioned_url()))
    await guard(httpx.Request("POST", "https://string-db.org/api/json/network"))


@pytest.mark.asyncio
async def test_guard_rejects_cross_host() -> None:
    guard = make_url_guard(build_host_allowlist(VERSIONED_BASE, f"https://{GENERIC_STRING_HOST}"))
    with pytest.raises(DisallowedURLError):
        await guard(httpx.Request("POST", "https://evil.example.com/api/json/network"))


@pytest.mark.asyncio
async def test_guard_rejects_non_https() -> None:
    guard = make_url_guard(build_host_allowlist(VERSIONED_BASE))
    with pytest.raises(DisallowedURLError):
        await guard(httpx.Request("POST", "http://version-12-0.string-db.org/api/json/network"))


@pytest.mark.asyncio
async def test_guard_rejects_userinfo() -> None:
    guard = make_url_guard(build_host_allowlist(VERSIONED_BASE))
    with pytest.raises(DisallowedURLError):
        await guard(httpx.Request("POST", "https://user:pass@version-12-0.string-db.org/api/x"))


@pytest.mark.asyncio
async def test_guard_rejects_empty_userinfo() -> None:
    """Syntactic *empty* userinfo (``:@`` form) on an allowlisted host is rejected.

    httpx reports ``url.username == url.password == ""`` for ``https://:@host/…``,
    so a ``username or password`` gate MISSES it -- but ``url.userinfo`` is the raw
    ``b":"`` (truthy). The recipe permits NO userinfo at all, so the raw
    ``url.userinfo`` must be the authoritative gate.
    """
    guard = make_url_guard(build_host_allowlist(VERSIONED_BASE))
    with pytest.raises(DisallowedURLError):
        await guard(httpx.Request("POST", "https://:@version-12-0.string-db.org/api/x"))


@pytest.mark.asyncio
async def test_guard_rejects_username_only_userinfo() -> None:
    """Username-only userinfo (``user@`` form) on an allowlisted host is rejected."""
    guard = make_url_guard(build_host_allowlist(VERSIONED_BASE))
    with pytest.raises(DisallowedURLError):
        await guard(httpx.Request("POST", "https://user@version-12-0.string-db.org/api/x"))


@pytest.mark.asyncio
async def test_guard_allows_clean_host_no_userinfo() -> None:
    """The clean allowlisted origin with NO userinfo still passes the gate."""
    guard = make_url_guard(build_host_allowlist(VERSIONED_BASE))
    await guard(httpx.Request("POST", "https://version-12-0.string-db.org/api/x"))


# --------------------------------------------------------------------------- #
# Wiring: _ensure_client installs the guard + bounds redirects                #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_ensure_client_wires_guard_and_bounds_redirects() -> None:
    # Default/production base URL is the versioned host; allowlist must carry
    # BOTH the versioned host (derived) and the generic stable-address host.
    client = StringDBClient(base_url=VERSIONED_BASE)
    try:
        await client._ensure_client()
        inner = client._client
        assert inner is not None
        assert inner.follow_redirects is True
        assert inner.max_redirects <= 5
        assert inner.event_hooks["request"], "request event-hook must be installed"
        assert client._allowed_hosts == frozenset(
            {("version-12-0.string-db.org", 443), ("string-db.org", 443)},
        )
    finally:
        await client.close()


def _guarded_client(
    handler: httpx.MockTransport,
    base_url: str,
    allowed_hosts: frozenset[tuple[str, int]] | None = None,
) -> StringDBClient:
    """A StringDBClient whose transport is mocked but whose real guard is wired."""
    client = StringDBClient(base_url=base_url)
    if allowed_hosts is not None:
        client._allowed_hosts = allowed_hosts
    client._client = httpx.AsyncClient(
        transport=handler,
        event_hooks={"request": [make_url_guard(client._allowed_hosts)]},
        follow_redirects=True,
        max_redirects=5,
    )
    return client


# --------------------------------------------------------------------------- #
# End-to-end through _make_request (redirect following + cap + POST body)     #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_cross_host_redirect_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "version-12-0.string-db.org":
            return httpx.Response(302, headers={"location": "https://evil.example.com/steal"})
        raise AssertionError("guard must block the cross-host hop")

    client = _guarded_client(httpx.MockTransport(handler), VERSIONED_BASE)
    try:
        with pytest.raises(DisallowedURLError):
            await client._make_request("network", {"identifiers": "TP53"})
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_non_https_redirect_downgrade_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.scheme == "https":
            return httpx.Response(
                307,
                headers={"location": "http://version-12-0.string-db.org/api/json/network"},
            )
        raise AssertionError("guard must block the http downgrade hop")

    client = _guarded_client(httpx.MockTransport(handler), VERSIONED_BASE)
    try:
        with pytest.raises(DisallowedURLError):
            await client._make_request("network", {"identifiers": "TP53"})
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_generic_to_versioned_redirect_preserves_post_body() -> None:
    """A 307 generic->versioned redirect must be allowed AND keep the POST body.

    The production allowlist (default versioned base URL + the generic host)
    contains BOTH hosts, so STRING's documented generic->versioned stable-address
    redirect is permitted. 307/308 are the redirect classes that preserve
    method + body under httpx; a manual disable-and-loop is exactly where the
    form body would be silently dropped.
    """
    # Production allowlist: both the versioned host and the generic host.
    production_allowlist = build_host_allowlist(VERSIONED_BASE, GENERIC_BASE)
    assert production_allowlist == frozenset(
        {("version-12-0.string-db.org", 443), ("string-db.org", 443)},
    )

    seen_bodies: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies[request.url.host or ""] = request.content
        if request.url.host == "string-db.org":
            return httpx.Response(
                307,
                headers={"location": "https://version-12-0.string-db.org/api/json/network"},
            )
        return httpx.Response(200, json=[{"stringId_A": "9606.ENSP1"}])

    # base_url=generic so the initial hop targets string-db.org; allowlist carries
    # both hosts (the production set).
    client = _guarded_client(
        httpx.MockTransport(handler),
        GENERIC_BASE,
        allowed_hosts=production_allowlist,
    )
    try:
        result = await client._make_request("network", {"identifiers": "TP53\rMDM2"})
    finally:
        await client.close()

    assert result == [{"stringId_A": "9606.ENSP1"}]
    # The final (versioned) hop received the intact POST form body.
    versioned_body = seen_bodies["version-12-0.string-db.org"]
    assert b"identifiers=TP53" in versioned_body
    assert versioned_body == seen_bodies["string-db.org"]


@pytest.mark.asyncio
async def test_happy_path_versioned_no_redirect_unchanged() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "version-12-0.string-db.org"
        return httpx.Response(200, json=[{"stringId_A": "9606.ENSP1"}])

    client = _guarded_client(httpx.MockTransport(handler), VERSIONED_BASE)
    try:
        result = await client._make_request("network", {"identifiers": "TP53"})
    finally:
        await client.close()

    assert result == [{"stringId_A": "9606.ENSP1"}]


@pytest.mark.asyncio
async def test_response_over_cap_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("stringdb_link.api.client.MAX_RESPONSE_BYTES", 16)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 4096)

    client = _guarded_client(httpx.MockTransport(handler), VERSIONED_BASE)
    try:
        with pytest.raises(ResponseTooLargeError):
            await client._make_request("network", {"identifiers": "TP53"})
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_network_image_over_cap_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("stringdb_link.api.client.MAX_RESPONSE_BYTES", 16)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"\x89PNG" + b"\x00" * 4096)

    client = _guarded_client(httpx.MockTransport(handler), VERSIONED_BASE)
    try:
        with pytest.raises(ResponseTooLargeError):
            await client.get_network_image(["TP53"])
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_network_image_happy_path_returns_bytes() -> None:
    payload = b"\x89PNG\r\n\x1a\n" + b"imagedata"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "version-12-0.string-db.org"
        return httpx.Response(200, content=payload)

    client = _guarded_client(httpx.MockTransport(handler), VERSIONED_BASE)
    try:
        result = await client.get_network_image(["TP53"])
    finally:
        await client.close()

    assert result == payload


# --------------------------------------------------------------------------- #
# F-17 gate fix 1: full-origin (port) validation, not host-only                #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_guard_rejects_alternate_port() -> None:
    """An allowlisted host on a NON-default port is a distinct origin: rejected.

    A host-only check would let ``version-12-0.string-db.org:8080`` through; the
    guard must validate the full origin (scheme=https, exact host, AND port=443).
    """
    guard = make_url_guard(build_host_allowlist(VERSIONED_BASE))
    with pytest.raises(DisallowedURLError):
        await guard(
            httpx.Request("POST", "https://version-12-0.string-db.org:8080/api/json/network"),
        )


@pytest.mark.asyncio
async def test_guard_allows_explicit_default_port() -> None:
    """The explicit default HTTPS port (:443) is the production origin: allowed."""
    guard = make_url_guard(build_host_allowlist(VERSIONED_BASE))
    await guard(
        httpx.Request("POST", "https://version-12-0.string-db.org:443/api/json/network"),
    )


@pytest.mark.asyncio
async def test_alternate_port_redirect_rejected() -> None:
    """A 307 redirect to an allowlisted host on an alternate port fails closed.

    307 preserves method+body, so ONLY the origin/port check can reject this hop:
    it proves the guard is not fooled by an off-origin explicit port.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.port in (None, 443):
            return httpx.Response(
                307,
                headers={"location": "https://version-12-0.string-db.org:8080/api/json/network"},
            )
        raise AssertionError("guard must block the alternate-port hop")

    client = _guarded_client(httpx.MockTransport(handler), VERSIONED_BASE)
    try:
        with pytest.raises(DisallowedURLError):
            await client._make_request("network", {"identifiers": "TP53"})
    finally:
        await client.close()


# --------------------------------------------------------------------------- #
# F-17 gate fix 2: fail closed when a redirect changes method / drops the body #
# --------------------------------------------------------------------------- #


def test_check_no_redirect_method_change_flags_post_to_get() -> None:
    """A 302 that rewrote POST->GET (dropping the body) must be flagged."""
    original = httpx.Request("POST", "https://string-db.org/api/json/network")
    redirect_resp = httpx.Response(302, request=original)
    final_req = httpx.Request("GET", "https://version-12-0.string-db.org/api/json/network")
    final_resp = httpx.Response(200, request=final_req, history=[redirect_resp])
    with pytest.raises(RedirectBodyLossError):
        check_no_redirect_method_change(final_resp)


def test_check_no_redirect_method_change_allows_no_redirect() -> None:
    """A direct (no-history) response never trips the method-change guard."""
    req = httpx.Request("POST", "https://version-12-0.string-db.org/api/json/network")
    check_no_redirect_method_change(httpx.Response(200, request=req))


def test_check_no_redirect_method_change_allows_preserved_method() -> None:
    """A 307 that preserved POST->POST (body intact) is permitted."""
    original = httpx.Request("POST", "https://string-db.org/api/json/network")
    redirect_resp = httpx.Response(307, request=original)
    final_req = httpx.Request("POST", "https://version-12-0.string-db.org/api/json/network")
    final_resp = httpx.Response(200, request=final_req, history=[redirect_resp])
    check_no_redirect_method_change(final_resp)


@pytest.mark.asyncio
async def test_method_changing_redirect_fails_closed() -> None:
    """A 302 generic->versioned redirect rewrites POST->GET (drops the form body).

    Both hosts are allowlisted, so the origin guard permits the hop -- but httpx
    then converts the POST to a bodyless GET. The client must FAIL CLOSED rather
    than silently send the bodyless request and return the (wrong/empty) result.
    """
    production_allowlist = build_host_allowlist(GENERIC_BASE, VERSIONED_BASE)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "string-db.org":
            return httpx.Response(
                302,
                headers={"location": "https://version-12-0.string-db.org/api/json/network"},
            )
        # Reaching here means httpx sent the rewritten bodyless GET -- the exact
        # silent-failure the fix must prevent.
        return httpx.Response(200, json=[{"stringId_A": "9606.ENSP1"}])

    client = _guarded_client(
        httpx.MockTransport(handler),
        GENERIC_BASE,
        allowed_hosts=production_allowlist,
    )
    try:
        with pytest.raises(RedirectBodyLossError):
            await client._make_request("network", {"identifiers": "TP53\rMDM2"})
    finally:
        await client.close()


# --------------------------------------------------------------------------- #
# F-17 gate fix 3: the blocked host never reaches a log record / response      #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_guard_message_is_host_free() -> None:
    """The DisallowedURLError carries a FIXED message -- never the blocked host."""
    blocked = "attacker-controlled.evil.example"
    guard = make_url_guard(build_host_allowlist(VERSIONED_BASE))
    with pytest.raises(DisallowedURLError) as excinfo:
        await guard(httpx.Request("POST", f"https://{blocked}/steal"))
    assert blocked not in str(excinfo.value)


@pytest.mark.asyncio
async def test_blocked_host_redirect_never_logs_or_returns_host(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A blocked-host redirect leaks the attacker host to NEITHER logs NOR message.

    The host arrives via a redirect ``Location`` (attacker-influenceable). Neither
    the raised exception (which becomes the caller-visible message) nor any emitted
    log record may contain it.
    """
    blocked = "attacker-controlled.evil.example"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "version-12-0.string-db.org":
            return httpx.Response(307, headers={"location": f"https://{blocked}/steal"})
        raise AssertionError("guard must block the cross-host redirect hop")

    client = _guarded_client(httpx.MockTransport(handler), VERSIONED_BASE)
    try:
        with caplog.at_level(logging.DEBUG), pytest.raises(DisallowedURLError) as excinfo:
            await client._make_request("network", {"identifiers": "TP53"})
    finally:
        await client.close()

    assert blocked not in str(excinfo.value)
    for record in caplog.records:
        assert blocked not in record.getMessage()
        assert blocked not in str(record.__dict__)
