"""StringDB HTTP client with async support, rate limiting, and error handling.

This module provides a comprehensive HTTP client for the STRING protein-protein
interaction database API with built-in token bucket rate limiting, retry logic,
and comprehensive error handling.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING, Any, NoReturn, Self, cast
from urllib.parse import urljoin

import httpx

from stringdb_link.config import settings
from stringdb_link.exceptions import (
    NetworkError,
    StringDBAPIError,
    StringDBRateLimitError,
    StringDBTimeoutError,
)
from stringdb_link.logging_config import get_logger, log_stringdb_request
from stringdb_link.models.stringdb import OutputFormat
from stringdb_link.utils.rate_limiter import AdaptiveRateLimiter

if TYPE_CHECKING:
    import types

    from structlog.typing import FilteringBoundLogger


class StringDBClient:
    """Async HTTP client for StringDB API with token bucket rate limiting."""

    # HTTP status code constants
    _HTTP_OK = 200
    _HTTP_CLIENT_ERROR = 400
    _HTTP_TOO_MANY_REQUESTS = 429
    _HTTP_SERVER_ERROR = 500

    # Response tracking constants
    _MAX_RESPONSE_TIMES = 1000
    _RESPONSE_TIMES_KEEP = 500

    # Methods that may be wrapped with an opt-in alru_cache decorator.
    _CACHED_METHOD_NAMES: tuple[str, ...] = (
        "get_string_ids",
        "get_network_interactions",
        "get_interaction_partners",
        "get_functional_enrichment",
        "get_functional_annotation",
        "get_network_image",
        "get_homology_scores",
        "get_homology_best_hits",
        "get_ppi_enrichment",
        "get_version",
    )

    def _raise_rate_limit_error(self, endpoint: str, response: httpx.Response) -> NoReturn:
        """Raise rate limit error with proper details."""
        retry_after = int(response.headers.get("Retry-After", 60))
        msg = f"Rate limit exceeded for endpoint {endpoint}"
        raise StringDBRateLimitError(
            msg,
            retry_after=retry_after,
            endpoint=endpoint,
        )

    def _raise_server_error(self, endpoint: str, response: httpx.Response) -> NoReturn:
        """Raise server error with proper details."""
        msg = f"StringDB server error: {response.status_code}"
        raise StringDBAPIError(
            msg,
            status_code=response.status_code,
            endpoint=endpoint,
        )

    def _raise_client_error(
        self, endpoint: str, response: httpx.Response, error_data: dict[str, Any]
    ) -> NoReturn:
        """Raise client error with proper details."""
        msg = f"StringDB API error: {response.status_code}"
        raise StringDBAPIError(
            msg,
            status_code=response.status_code,
            response_data=error_data,
            endpoint=endpoint,
        )

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        rate_limit_per_second: float | None = None,
        max_retries: int | None = None,
        caller_identity: str | None = None,
        logger: FilteringBoundLogger | None = None,
    ) -> None:
        """Initialize the StringDB client.

        Args:
            base_url: Base URL for StringDB API
            timeout: Request timeout in seconds
            rate_limit_per_second: Requests per second rate limit
            max_retries: Maximum number of retries
            caller_identity: Caller identity for STRING API
            logger: Logger instance
        """
        self.base_url = base_url or settings.stringdb_base_url
        self.timeout = timeout or settings.stringdb_request_timeout
        self.max_retries = max_retries or settings.stringdb_max_retries
        self.caller_identity = caller_identity or "StringDB-Link/0.1.0"
        self.logger = logger or get_logger("stringdb_client")

        # Initialize statistics tracking
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times: list[float] = []
        self.start_time = time.time()

        # Initialize adaptive rate limiter
        rate_per_second = rate_limit_per_second or (1.0 / settings.stringdb_rate_limit_delay)
        self.rate_limiter = AdaptiveRateLimiter(
            initial_rate=rate_per_second,
            burst=2,  # Allow small bursts
            min_rate=0.1,
            max_rate=rate_per_second * 2,
        )

        # HTTP client configuration
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(
                    max_connections=settings.connection_pool_size,
                    max_keepalive_connections=settings.connection_pool_max_size,
                    keepalive_expiry=settings.keepalive_timeout,
                ),
                headers={
                    "User-Agent": "StringDB-Link/0.1.0",
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                follow_redirects=True,
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def get_stats(self) -> dict[str, Any]:
        """Get client statistics for monitoring.

        Returns:
            Dictionary containing client statistics
        """
        uptime = time.time() - self.start_time
        avg_response_time = (
            sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        )
        success_rate = (
            (self.successful_requests / self.total_requests * 100)
            if self.total_requests > 0
            else 0.0
        )

        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(success_rate, 2),
            "avg_response_time": round(avg_response_time, 3),
            "uptime_seconds": round(uptime, 1),
            "rate_limiter": self.rate_limiter.get_stats(),
        }

    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any],
        output_format: str = "json",
        method: str = "POST",
        retries: int = 0,
    ) -> list[dict[str, Any]] | str:
        """Make a request to StringDB API with error handling and retries.

        Args:
            endpoint: API endpoint
            params: Request parameters
            output_format: Output format (json, tsv, etc.)
            method: HTTP method
            retries: Current retry count

        Returns:
            Response data

        Raises:
            StringDBAPIError: API returned an error
            StringDBTimeoutError: Request timed out
            StringDBRateLimitError: Rate limit exceeded
            NetworkError: Network-related error
        """
        await self._ensure_client()
        assert self._client is not None

        # Apply token bucket rate limiting
        wait_time = await self.rate_limiter.wait_if_needed()
        if wait_time > 0:
            self.logger.debug("Rate limited, waited %.3fs", wait_time)

        # Construct URL
        url_path = f"{output_format}/{endpoint}"
        url = urljoin(self.base_url.rstrip("/") + "/", url_path)

        start_time = time.time()
        self.total_requests += 1

        try:
            # Make the HTTP request
            if method == "POST":
                response = await self._client.post(url, data=params)
            else:
                response = await self._client.get(url, params=params)

            duration = time.time() - start_time
            self.response_times.append(duration)

            # Keep only recent response times for statistics
            if len(self.response_times) > self._MAX_RESPONSE_TIMES:
                self.response_times = self.response_times[-self._RESPONSE_TIMES_KEEP :]

            # Log the request
            log_stringdb_request(
                self.logger,
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                duration=duration,
            )

            # Handle response based on status code
            if response.status_code == self._HTTP_OK:
                # Success
                self.successful_requests += 1
                await self.rate_limiter.on_success()

                # JSON responses decode to a list of records; every other
                # format (tsv/xml/psi-mi/...) is returned as text. Binary image
                # formats are served by get_network_image, not this path.
                if output_format == "json":
                    return cast("list[dict[str, Any]]", response.json())
                return response.text

            if response.status_code == self._HTTP_TOO_MANY_REQUESTS:
                # Rate limit exceeded
                self.failed_requests += 1
                await self.rate_limiter.on_rate_limited()

                self._raise_rate_limit_error(endpoint, response)

            if response.status_code >= self._HTTP_SERVER_ERROR:
                # Server error - retry if we have retries left
                self.failed_requests += 1

                if retries < self.max_retries:
                    delay = settings.stringdb_retry_delay * (2**retries)
                    self.logger.warning(
                        "StringDB server error, retrying",
                        endpoint=endpoint,
                        status_code=response.status_code,
                        retry=retries + 1,
                        delay=delay,
                    )
                    await asyncio.sleep(delay)
                    return await self._make_request(
                        endpoint,
                        params,
                        output_format,
                        method,
                        retries + 1,
                    )

                self._raise_server_error(endpoint, response)

            # Client error (4xx)
            self.failed_requests += 1

            try:
                error_data = response.json()
            except json.JSONDecodeError:
                error_data = {"message": response.text}

            self._raise_client_error(endpoint, response, error_data)

        except httpx.TimeoutException as e:
            self.failed_requests += 1
            msg = f"Request to {endpoint} timed out after {self.timeout}s"
            raise StringDBTimeoutError(
                msg,
                timeout=self.timeout,
                endpoint=endpoint,
            ) from e

        except httpx.RequestError as e:
            self.failed_requests += 1
            msg = f"Network error accessing {endpoint}: {e}"
            raise NetworkError(
                msg,
                original_error=e,
                endpoint=endpoint,
            ) from e

        except Exception as e:
            self.failed_requests += 1
            self.logger.exception(
                "Unexpected error during StringDB request",
                endpoint=endpoint,
                error=str(e),
            )
            msg = f"Unexpected error accessing {endpoint}: {e}"
            raise StringDBAPIError(
                msg,
                endpoint=endpoint,
            ) from e

    # Cached methods for frequently accessed data
    async def get_string_ids(
        self,
        identifiers: list[str],
        species: int | None = None,
        *,
        echo_query: bool = False,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> list[dict[str, Any]] | str:
        """Map protein identifiers to STRING IDs.

        Args:
            identifiers: List of protein identifiers
            species: NCBI taxon ID
            echo_query: Include input identifier in output
            output_format: Output format (json, tsv, xml, psi-mi)

        Returns:
            List of identifier mappings (JSON) or formatted string (TSV/XML/PSI-MI)
        """
        params = {
            "identifiers": "\r".join(identifiers),
            "echo_query": 1 if echo_query else 0,
            "caller_identity": self.caller_identity,
        }

        if species:
            params["species"] = species

        return await self._make_request("get_string_ids", params, output_format.value)

    async def get_network_interactions(
        self,
        identifiers: list[str],
        species: int | None = None,
        required_score: int = 400,
        network_type: str = "functional",
        add_nodes: int = 0,
        *,
        show_query_node_labels: bool = False,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> list[dict[str, Any]] | str:
        """Get protein-protein interaction network.

        Args:
            identifiers: List of protein identifiers
            species: NCBI taxon ID
            required_score: Minimum confidence score on STRING's 0-1000 integer scale (e.g. 400 = 0.4)
            network_type: Network type (functional or physical)
            add_nodes: Number of additional nodes to add
            show_query_node_labels: Use submitted names as labels
            output_format: Output format (json, tsv, xml, psi-mi)

        Returns:
            List of network interactions (JSON) or formatted string (TSV/XML/PSI-MI)
        """
        params = {
            "identifiers": "\r".join(identifiers),
            "required_score": required_score,
            "network_type": network_type,
            "show_query_node_labels": 1 if show_query_node_labels else 0,
            "caller_identity": self.caller_identity,
        }

        if species:
            params["species"] = species

        if add_nodes > 0:
            params["add_nodes"] = add_nodes

        return await self._make_request("network", params, output_format.value)

    async def get_interaction_partners(
        self,
        identifiers: list[str],
        species: int | None = None,
        limit: int = 10,
        required_score: int = 400,
        network_type: str = "functional",
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> list[dict[str, Any]] | str:
        """Get all interaction partners for proteins.

        Args:
            identifiers: List of protein identifiers
            species: NCBI taxon ID
            limit: Maximum number of partners per protein
            required_score: Minimum confidence score on STRING's 0-1000 integer scale (e.g. 400 = 0.4)
            network_type: Network type (functional or physical)
            output_format: Output format (json, tsv, xml, psi-mi)

        Returns:
            List of interaction partners (JSON) or formatted string (TSV/XML/PSI-MI)
        """
        params = {
            "identifiers": "\r".join(identifiers),
            "limit": limit,
            "required_score": required_score,
            "network_type": network_type,
            "caller_identity": self.caller_identity,
        }

        if species:
            params["species"] = species

        return await self._make_request("interaction_partners", params, output_format.value)

    # @alru_cache(maxsize=64, ttl=21600)  # Cache for 6 hours
    async def get_functional_enrichment(
        self,
        identifiers: list[str],
        species: int | None = None,
        background_string_identifiers: list[str] | None = None,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> list[dict[str, Any]] | str:
        """Perform functional enrichment analysis.

        Args:
            identifiers: List of protein identifiers
            species: NCBI taxon ID
            background_string_identifiers: Background proteome identifiers
            output_format: Output format (json, tsv, xml, psi-mi)

        Returns:
            List of enriched terms (JSON) or formatted string (TSV/XML/PSI-MI)
        """
        params: dict[str, Any] = {
            "identifiers": "\r".join(identifiers),
            "caller_identity": self.caller_identity,
        }

        if species:
            params["species"] = species

        if background_string_identifiers:
            params["background_string_identifiers"] = "\r".join(
                background_string_identifiers,
            )

        return await self._make_request("enrichment", params, output_format.value)

    # @alru_cache(maxsize=128, ttl=21600)  # Cache for 6 hours
    async def get_functional_annotation(
        self,
        identifiers: list[str],
        species: int | None = None,
        *,
        allow_pubmed: bool = False,
        only_pubmed: bool = False,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> list[dict[str, Any]] | str:
        """Get functional annotations for proteins.

        Args:
            identifiers: List of protein identifiers
            species: NCBI taxon ID
            allow_pubmed: Include PubMed annotations
            only_pubmed: Return only PubMed annotations
            output_format: Output format (json, tsv, xml, psi-mi)

        Returns:
            List of functional annotations (JSON) or formatted string (TSV/XML/PSI-MI)
        """
        params = {
            "identifiers": "\r".join(identifiers),
            "allow_pubmed": 1 if allow_pubmed else 0,
            "only_pubmed": 1 if only_pubmed else 0,
            "caller_identity": self.caller_identity,
        }

        if species:
            params["species"] = species

        return await self._make_request("functional_annotation", params, output_format.value)

    # @alru_cache(maxsize=32, ttl=7200)  # Cache for 2 hours
    async def get_network_image(
        self,
        identifiers: list[str],
        species: int | None = None,
        add_color_nodes: int = 0,
        add_white_nodes: int = 0,
        network_flavor: str = "evidence",
        network_type: str = "functional",
        required_score: int = 400,
        image_format: str = "image",
        hide_node_labels: bool = False,
        hide_disconnected_nodes: bool = False,
        show_query_node_labels: bool = False,
    ) -> bytes:
        """Generate network visualization image.

        Args:
            identifiers: List of protein identifiers
            species: NCBI taxon ID
            add_color_nodes: Number of colored nodes to add
            add_white_nodes: Number of white nodes to add
            network_flavor: Network style (evidence, confidence, actions)
            network_type: Network type (functional or physical)
            required_score: Minimum confidence score on STRING's 0-1000 integer scale (e.g. 400 = 0.4)
            image_format: Image format (image, highres_image, svg)

        Returns:
            Image data as bytes
        """
        params = {
            "identifiers": "\r".join(identifiers),
            "network_flavor": network_flavor,
            "network_type": network_type,
            "required_score": required_score,
            "hide_node_labels": 1 if hide_node_labels else 0,
            "hide_disconnected_nodes": 1 if hide_disconnected_nodes else 0,
            "show_query_node_labels": 1 if show_query_node_labels else 0,
            "caller_identity": self.caller_identity,
        }

        if species:
            params["species"] = species

        if add_color_nodes > 0:
            params["add_color_nodes"] = add_color_nodes

        if add_white_nodes > 0:
            params["add_white_nodes"] = add_white_nodes

        # For image endpoints, we expect binary data
        await self._ensure_client()
        assert self._client is not None

        await self.rate_limiter.wait_if_needed()

        url_path = f"{image_format}/network"
        url = urljoin(self.base_url.rstrip("/") + "/", url_path)

        start_time = asyncio.get_event_loop().time()

        try:
            response = await self._client.post(url, data=params)
            duration = asyncio.get_event_loop().time() - start_time

            log_stringdb_request(
                self.logger,
                endpoint="network_image",
                method="POST",
                status_code=response.status_code,
                duration=duration,
            )

            if response.status_code == self._HTTP_OK:
                return response.content
            msg = f"Failed to generate network image: {response.status_code}"
            raise StringDBAPIError(
                msg,
                status_code=response.status_code,
                endpoint="network_image",
            )

        except httpx.TimeoutException as e:
            msg = "Network image generation timed out"
            raise StringDBTimeoutError(
                msg,
                timeout=self.timeout,
                endpoint="network_image",
            ) from e

    # @alru_cache(maxsize=64, ttl=43200)  # Cache for 12 hours
    async def get_homology_scores(
        self,
        identifiers: list[str],
        species: int | None = None,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> list[dict[str, Any]] | str:
        """Get protein homology scores.

        Args:
            identifiers: List of protein identifiers
            species: NCBI taxon ID
            output_format: Output format (json, tsv, xml, psi-mi)

        Returns:
            List of homology scores (JSON) or formatted string (TSV/XML/PSI-MI)
        """
        params: dict[str, Any] = {
            "identifiers": "\r".join(identifiers),
            "caller_identity": self.caller_identity,
        }

        if species:
            params["species"] = species

        return await self._make_request("homology", params, output_format.value)

    # @alru_cache(maxsize=64, ttl=43200)  # Cache for 12 hours
    async def get_homology_best_hits(
        self,
        identifiers: list[str],
        species: int | None = None,
        species_b: list[int] | None = None,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> list[dict[str, Any]] | str:
        """Get best homology hits between species.

        Args:
            identifiers: List of protein identifiers
            species: Source species NCBI taxon ID
            species_b: Target species list
            output_format: Output format (json, tsv, xml, psi-mi)

        Returns:
            List of best homology hits (JSON) or formatted string (TSV/XML/PSI-MI)
        """
        params: dict[str, Any] = {
            "identifiers": "\r".join(identifiers),
            "caller_identity": self.caller_identity,
        }

        if species:
            params["species"] = species

        if species_b:
            params["species_b"] = "\r".join(map(str, species_b))

        return await self._make_request("homology_best", params, output_format.value)

    # @alru_cache(maxsize=32, ttl=21600)  # Cache for 6 hours
    async def get_ppi_enrichment(
        self,
        identifiers: list[str],
        species: int | None = None,
        required_score: int = 400,
        background_string_identifiers: list[str] | None = None,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> dict[str, Any] | str:
        """Perform protein-protein interaction enrichment analysis.

        Args:
            identifiers: List of protein identifiers
            species: NCBI taxon ID
            required_score: Minimum confidence score on STRING's 0-1000 integer scale (e.g. 400 = 0.4)
            background_string_identifiers: Background proteome identifiers
            output_format: Output format (json, tsv, xml, psi-mi)

        Returns:
            PPI enrichment results (JSON) or formatted string (TSV/XML/PSI-MI)
        """
        params = {
            "identifiers": "\r".join(identifiers),
            "required_score": required_score,
            "caller_identity": self.caller_identity,
        }

        if species:
            params["species"] = species

        if background_string_identifiers:
            params["background_string_identifiers"] = "\r".join(
                background_string_identifiers,
            )

        result = await self._make_request("ppi_enrichment", params, output_format.value)
        # For JSON format, API returns a list with one dict, we return just the dict
        if output_format == OutputFormat.JSON and isinstance(result, list) and result:
            return result[0]
        return cast("dict[str, Any] | str", result)

    # @alru_cache(maxsize=16, ttl=86400)  # Cache for 24 hours
    async def get_version(
        self, output_format: OutputFormat = OutputFormat.JSON
    ) -> dict[str, Any] | str:
        """Get current STRING version information.

        Args:
            output_format: Output format (json, tsv, xml, psi-mi)

        Returns:
            Version information (JSON) or formatted string (TSV/XML/PSI-MI)
        """
        result = await self._make_request("version", {}, output_format.value)
        # For JSON format, API returns a list with one dict, we return just the dict
        if output_format == OutputFormat.JSON and isinstance(result, list) and result:
            return result[0]
        return cast("dict[str, Any] | str", result)

    async def get_link(
        self,
        identifiers: list[str],
        species: int | None = None,
        output_format: OutputFormat = OutputFormat.JSON,
        **kwargs: Any,
    ) -> dict[str, Any] | str:
        """Get link to STRING webpage for the network.

        Args:
            identifiers: List of protein identifiers
            species: NCBI taxon ID
            output_format: Output format (json, tsv, xml, psi-mi)
            **kwargs: Additional parameters for network visualization

        Returns:
            Link information (JSON) or formatted string (TSV/XML/PSI-MI)
        """
        params = {
            "identifiers": "\r".join(identifiers),
            "caller_identity": self.caller_identity,
            **kwargs,
        }

        if species:
            params["species"] = species

        result = await self._make_request("get_link", params, output_format.value)
        # For JSON format, API returns a list with one dict, we return just the dict
        if output_format == OutputFormat.JSON and isinstance(result, list) and result:
            return result[0]
        return cast("dict[str, Any] | str", result)

    def clear_cache(self) -> None:
        """Clear all cached data."""
        # Caching is opt-in (decorators may be disabled), so only call
        # cache_clear on methods that actually expose it.
        for method_name in self._CACHED_METHOD_NAMES:
            method = getattr(self, method_name)
            if hasattr(method, "cache_clear"):
                method.cache_clear()

        self.logger.info("Cleared all cached data")

    def get_cache_stats(self) -> dict[str, dict[str, Any]]:
        """Get cache statistics for all cached methods.

        Returns:
            Dictionary with cache stats for each method
        """
        stats: dict[str, dict[str, Any]] = {}
        for method_name in self._CACHED_METHOD_NAMES:
            method = getattr(self, method_name)
            if hasattr(method, "cache_info"):
                info = method.cache_info()
                stats[method_name] = {
                    "hits": info.hits,
                    "misses": info.misses,
                    "maxsize": info.maxsize,
                    "currsize": info.currsize,
                }

        return stats
