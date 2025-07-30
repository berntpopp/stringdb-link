"""Rate limiting utilities for StringDB-Link.

This module provides a TokenBucketRateLimiter class for rate limiting
API requests with burst capability and rate tracking.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any


class TokenBucketRateLimiter:
    """Token bucket rate limiter for API requests with burst capability."""

    # Constants for rate calculation
    _RATE_WINDOW_SECONDS = 10.0
    _MIN_REQUESTS_FOR_RATE = 2

    def __init__(self, rate: float, burst: int = 1) -> None:
        """Initialize rate limiter.

        Args:
            rate: Requests per second
            burst: Maximum burst size (number of tokens in bucket)
        """
        self.rate = max(0.01, rate)  # Ensure minimum rate to avoid division by zero
        self.burst = max(1.0, float(burst))
        self.tokens = float(burst)
        self.last_update = time.time()
        self._lock = asyncio.Lock()
        self.request_times: list[float] = []

    async def acquire(self) -> float:
        """Acquire a token, waiting if necessary.

        Returns:
            Wait time in seconds (0 if no wait required)
        """
        async with self._lock:
            now = time.time()

            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= 1:
                # Token available, consume it
                self.tokens -= 1

                # Track request time for rate calculation
                self.request_times.append(now)

                # Keep only recent requests for rate calculation
                self.request_times = [
                    t for t in self.request_times if now - t <= self._RATE_WINDOW_SECONDS
                ]

                return 0.0

            # No tokens available, calculate wait time
            return (1 - self.tokens) / self.rate

    async def wait_if_needed(self) -> float:
        """Wait for a token if rate limiting is required.

        Returns:
            Time waited in seconds
        """
        wait_time = await self.acquire()
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        return wait_time

    @property
    def current_tokens(self) -> float:
        """Get current number of available tokens without updating state."""
        now = time.time()
        elapsed = now - self.last_update
        return min(self.burst, self.tokens + elapsed * self.rate)

    def current_rate(self) -> float:
        """Get current rate based on recent request times.

        Returns:
            Current estimated rate in requests per second
        """
        now = time.time()

        # Clean up old request times
        recent_requests = [t for t in self.request_times if now - t <= self._RATE_WINDOW_SECONDS]

        if len(recent_requests) < self._MIN_REQUESTS_FOR_RATE:
            return 0.0

        # Calculate rate based on requests over time window
        time_window = now - recent_requests[0]
        if time_window <= 0:
            return 0.0

        return len(recent_requests) / time_window

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics.

        Returns:
            Dictionary containing rate limiter stats
        """
        now = time.time()
        recent_requests = [t for t in self.request_times if now - t <= self._RATE_WINDOW_SECONDS]

        return {
            "configured_rate": self.rate,
            "burst_size": int(self.burst),
            "current_tokens": round(self.current_tokens, 2),
            "current_rate": round(self.current_rate(), 2),
            "recent_requests": len(recent_requests),
            "total_requests": len(self.request_times),
            "last_request_time": max(self.request_times) if self.request_times else None,
        }

    def reset(self) -> None:
        """Reset the rate limiter state."""
        self.tokens = self.burst
        self.last_update = time.time()
        self.request_times.clear()


class AdaptiveRateLimiter(TokenBucketRateLimiter):
    """Adaptive rate limiter that adjusts based on API responses."""

    def __init__(
        self,
        initial_rate: float,
        burst: int = 1,
        min_rate: float = 0.1,
        max_rate: float = 10.0,
        backoff_factor: float = 0.5,
        recovery_factor: float = 1.1,
    ) -> None:
        """Initialize adaptive rate limiter.

        Args:
            initial_rate: Initial requests per second
            burst: Maximum burst size
            min_rate: Minimum allowed rate
            max_rate: Maximum allowed rate
            backoff_factor: Factor to reduce rate on rate limiting (< 1.0)
            recovery_factor: Factor to increase rate on success (> 1.0)
        """
        super().__init__(initial_rate, burst)
        self.initial_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.backoff_factor = max(0.1, min(1.0, backoff_factor))
        self.recovery_factor = max(1.0, recovery_factor)
        self.consecutive_successes = 0
        self.consecutive_rate_limits = 0

    async def on_rate_limited(self) -> None:
        """Handle rate limiting response."""
        async with self._lock:
            self.consecutive_successes = 0
            self.consecutive_rate_limits += 1

            # Reduce rate more aggressively with consecutive rate limits
            reduction_factor = self.backoff_factor**self.consecutive_rate_limits
            new_rate = max(self.min_rate, self.rate * reduction_factor)

            if new_rate != self.rate:
                self.rate = new_rate
                # Reset tokens to prevent burst after rate reduction
                self.tokens = min(self.tokens, self.burst)

    async def on_success(self) -> None:
        """Handle successful response."""
        async with self._lock:
            self.consecutive_rate_limits = 0
            self.consecutive_successes += 1

            # Gradually increase rate after consecutive successes
            if self.consecutive_successes >= 10:  # Wait for sustained success
                new_rate = min(self.max_rate, self.rate * self.recovery_factor)
                if new_rate != self.rate:
                    self.rate = new_rate
                    self.consecutive_successes = 0

    def get_stats(self) -> dict[str, Any]:
        """Get adaptive rate limiter statistics."""
        stats = super().get_stats()
        stats.update(
            {
                "initial_rate": self.initial_rate,
                "min_rate": self.min_rate,
                "max_rate": self.max_rate,
                "consecutive_successes": self.consecutive_successes,
                "consecutive_rate_limits": self.consecutive_rate_limits,
                "backoff_factor": self.backoff_factor,
                "recovery_factor": self.recovery_factor,
            }
        )
        return stats
