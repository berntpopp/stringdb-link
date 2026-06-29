"""Centralized caching utilities for StringDB-Link.

This module provides a CacheManager class that wraps async-lru with
statistics tracking and observability features.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

from async_lru import alru_cache

from stringdb_link.config import settings
from stringdb_link.logging_config import get_logger

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

F = TypeVar("F", bound=Callable[..., Any])


class CacheStats:
    """Statistics for cache performance tracking."""

    def __init__(self) -> None:
        """Initialize cache statistics."""
        self.hits = 0
        self.misses = 0
        self.total_requests = 0
        self.total_time_saved = 0.0
        self.avg_hit_time = 0.0
        self.avg_miss_time = 0.0
        self._lock = asyncio.Lock()

    async def record_hit(self, time_saved: float) -> None:
        """Record a cache hit."""
        async with self._lock:
            self.hits += 1
            self.total_requests += 1
            self.total_time_saved += time_saved
            # Update running average
            self.avg_hit_time = (
                (self.avg_hit_time * (self.hits - 1) + time_saved) / self.hits
                if self.hits > 0
                else 0.0
            )

    async def record_miss(self, execution_time: float) -> None:
        """Record a cache miss."""
        async with self._lock:
            self.misses += 1
            self.total_requests += 1
            # Update running average
            self.avg_miss_time = (
                (self.avg_miss_time * (self.misses - 1) + execution_time) / self.misses
                if self.misses > 0
                else 0.0
            )

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        return (self.hits / self.total_requests * 100) if self.total_requests > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate as percentage."""
        return (self.misses / self.total_requests * 100) if self.total_requests > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary for logging/monitoring."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 2),
            "miss_rate": round(self.miss_rate, 2),
            "total_time_saved": round(self.total_time_saved, 3),
            "avg_hit_time": round(self.avg_hit_time, 3),
            "avg_miss_time": round(self.avg_miss_time, 3),
        }


class CacheManager:
    """Centralized cache manager with statistics and observability."""

    def __init__(
        self,
        logger: FilteringBoundLogger | None = None,
        enabled: bool = True,
    ) -> None:
        """Initialize the cache manager.

        Args:
            logger: Logger instance for cache events
            enabled: Whether caching is enabled
        """
        self.logger = logger or get_logger(__name__)
        self.enabled = enabled and settings.cache_enabled
        self.stats: dict[str, CacheStats] = {}
        self._lock = asyncio.Lock()

    async def get_stats(self, cache_name: str | None = None) -> dict[str, Any]:
        """Get cache statistics.

        Args:
            cache_name: Specific cache to get stats for, or None for all

        Returns:
            Dictionary containing cache statistics
        """
        async with self._lock:
            if cache_name:
                return {cache_name: self.stats.get(cache_name, CacheStats()).to_dict()}
            return {name: stats.to_dict() for name, stats in self.stats.items()}

    async def _get_cache_stats(self, cache_name: str) -> CacheStats:
        """Get or create cache stats for a given cache name."""
        async with self._lock:
            if cache_name not in self.stats:
                self.stats[cache_name] = CacheStats()
            return self.stats[cache_name]

    def cached(
        self,
        maxsize: int = 256,
        ttl: float | None = None,
        cache_name: str | None = None,
    ) -> Callable[[F], F]:
        """Create caching decorator for async functions with statistics.

        Args:
            maxsize: Maximum number of entries in cache
            ttl: Time-to-live in seconds (uses settings default if None)
            cache_name: Name for this cache in statistics

        Returns:
            Decorated function with caching and statistics
        """

        def decorator(func: F) -> F:
            if not self.enabled:
                # Return original function if caching disabled
                return func

            # Use function name as cache name if not provided
            actual_cache_name = cache_name or f"{func.__module__}.{func.__qualname__}"

            # Apply alru_cache
            cached_func = alru_cache(maxsize=maxsize, ttl=ttl)(func)

            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                stats = await self._get_cache_stats(actual_cache_name)

                start_time = time.time()

                # Check if this will be a cache hit
                cache_info = cached_func.cache_info()
                initial_hits = cache_info.hits

                try:
                    result = await cached_func(*args, **kwargs)
                    execution_time = time.time() - start_time

                    # Check if we got a cache hit
                    new_cache_info = cached_func.cache_info()
                    if new_cache_info.hits > initial_hits:
                        # Cache hit
                        await stats.record_hit(execution_time)
                        self.logger.debug(
                            "Cache hit",
                            cache_name=actual_cache_name,
                            execution_time=execution_time,
                            cache_size=new_cache_info.currsize,
                        )
                    else:
                        # Cache miss
                        await stats.record_miss(execution_time)
                        self.logger.debug(
                            "Cache miss",
                            cache_name=actual_cache_name,
                            execution_time=execution_time,
                            cache_size=new_cache_info.currsize,
                        )

                    return result

                except Exception as e:
                    execution_time = time.time() - start_time
                    await stats.record_miss(execution_time)
                    self.logger.exception(
                        "Cache error",
                        cache_name=actual_cache_name,
                        error=str(e),
                        execution_time=execution_time,
                    )
                    raise

            # Add cache management methods to the wrapper
            wrapper.cache_info = cached_func.cache_info  # type: ignore
            wrapper.cache_clear = cached_func.cache_clear  # type: ignore
            wrapper.cache_stats = lambda: asyncio.create_task(  # type: ignore
                self.get_stats(actual_cache_name)
            )

            return wrapper  # type: ignore

        return decorator

    async def clear_all_caches(self) -> None:
        """Clear all managed caches and reset statistics."""
        async with self._lock:
            self.stats.clear()
            self.logger.info("All caches cleared")

    async def log_cache_summary(self) -> None:
        """Log a summary of all cache statistics."""
        stats = await self.get_stats()
        if stats:
            self.logger.info("Cache statistics summary", cache_stats=stats)
        else:
            self.logger.info("No cache statistics available")


# Global cache manager instance
cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    return cache_manager
