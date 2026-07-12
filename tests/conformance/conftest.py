"""Bind the canonical HTTP-policy v1 suite to StringDB's real guard helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

import httpx
import pytest

from stringdb_link.api.url_guard import (
    DisallowedURLError,
    ResponseTooLargeError,
    build_host_allowlist,
    make_url_guard,
    read_capped,
)


class _Adapter:
    def __init__(self) -> None:
        self._guard = make_url_guard(build_host_allowlist("https://allowed.example"))

    @staticmethod
    def _run(coro: object) -> object:
        return asyncio.run(coro)  # type: ignore[arg-type]

    def allow(self, url: str) -> object:
        self._run(self._guard(httpx.Request("POST", url)))
        return "allowed"

    def request(self, url: str, redirects: list[str], max_redirects: int) -> None:
        self.allow(url)
        for index, redirect in enumerate(redirects, start=1):
            if index > max_redirects:
                raise DisallowedURLError("redirect limit exceeded")
            self.allow(redirect)

    def read_decoded(self, chunks: Iterable[bytes], cap: int) -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"".join(chunks))

        async def read() -> None:
            async with (
                httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client,
                client.stream("POST", "https://allowed.example/") as response,
            ):
                await read_capped(response, cap)

        self._run(read())

    def is_non_retryable(self, error: Exception) -> bool:
        return isinstance(error, (DisallowedURLError, ResponseTooLargeError))

    def public_message(self, error: Exception) -> str:
        return str(error)


@pytest.fixture
def http_policy_adapter() -> _Adapter:
    return _Adapter()
