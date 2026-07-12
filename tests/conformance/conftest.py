"""Bind the canonical suite to StringDB's production HTTP client.

The fixture only injects ``MockTransport`` at actual client construction.  The
production origin configuration, hook, redirect, POST, and stream/cap paths
are all executed unchanged.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from unittest.mock import patch

import httpx
import pytest

from stringdb_link.api.client import StringDBClient
from stringdb_link.api.url_guard import DisallowedURLError, ResponseTooLargeError

_BASE_URL = "https://allowed.example/api"
_ORIGIN = "https://allowed.example"


class _Adapter:
    @staticmethod
    def _run(coro: object) -> object:
        return asyncio.run(coro)  # type: ignore[arg-type]

    @staticmethod
    def _client(
        handler: Callable[[httpx.Request], httpx.Response],
    ) -> tuple[StringDBClient, object]:
        real_async_client = httpx.AsyncClient

        def with_mock_transport(**kwargs: object) -> httpx.AsyncClient:
            return real_async_client(transport=httpx.MockTransport(handler), **kwargs)

        return StringDBClient(base_url=_BASE_URL), patch(
            "stringdb_link.api.client.httpx.AsyncClient", side_effect=with_mock_transport
        )

    @staticmethod
    def _assert_production_configuration(client: StringDBClient) -> None:
        assert client._client is not None
        assert client._client.follow_redirects is True
        assert client._client.max_redirects == 5
        assert client._client.event_hooks["request"]
        assert ("allowed.example", 443) in client._allowed_hosts

    def allow(self, url: str) -> object:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[])

        async def request() -> object:
            client, async_client_patch = self._client(handler)
            with async_client_patch:
                try:
                    result = await client._make_request("network", {}, method="POST")
                    self._assert_production_configuration(client)
                    return result
                finally:
                    await client.close()

        if url != _BASE_URL and not url.startswith(f"{_BASE_URL}/"):
            # Route arbitrary canonical URLs through the actual configured
            # request hook while retaining its production client setup.
            async def hook_only() -> object:
                client, async_client_patch = self._client(handler)
                with async_client_patch:
                    try:
                        await client._ensure_client()
                        assert client._client is not None
                        for hook in client._client.event_hooks["request"]:
                            await hook(httpx.Request("POST", url))
                        self._assert_production_configuration(client)
                        return []
                    finally:
                        await client.close()

            return self._run(hook_only())
        return self._run(request())

    def request(self, url: str, redirects: list[str], max_redirects: int) -> None:
        seen = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal seen
            if seen < len(redirects):
                location = redirects[seen]
                seen += 1
                return httpx.Response(307, headers={"location": location})
            return httpx.Response(200, json=[])

        async def send() -> None:
            client, async_client_patch = self._client(handler)
            with async_client_patch:
                try:
                    await client._make_request("network", {}, method="POST")
                    self._assert_production_configuration(client)
                finally:
                    await client.close()

        assert url.startswith(_ORIGIN)
        assert max_redirects == 5
        self._run(send())

    def read_decoded(self, chunks: Iterable[bytes], cap: int) -> None:
        payload = b"".join(chunks)

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=payload)

        async def read() -> None:
            client, async_client_patch = self._client(handler)
            with patch("stringdb_link.api.client.MAX_RESPONSE_BYTES", cap), async_client_patch:
                try:
                    await client._make_request("network", {}, method="POST")
                finally:
                    await client.close()

        self._run(read())

    def is_non_retryable(self, error: Exception) -> bool:
        return isinstance(error, (DisallowedURLError, ResponseTooLargeError))

    def public_message(self, error: Exception) -> str:
        return str(error)


@pytest.fixture
def http_policy_adapter() -> _Adapter:
    return _Adapter()
