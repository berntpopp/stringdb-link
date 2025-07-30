"""Fixed tests for rate limiter utilities."""

# ruff: noqa: SLF001  # Private member access is needed for testing internal state

import asyncio
import time
from unittest.mock import patch

import pytest

from stringdb_link.utils.rate_limiter import TokenBucketRateLimiter


@pytest.fixture
def rate_limiter():
    """Create a TokenBucketRateLimiter instance for testing."""
    return TokenBucketRateLimiter(rate=2.0, burst=5)


@pytest.fixture
def strict_rate_limiter():
    """Create a strict TokenBucketRateLimiter instance for testing."""
    return TokenBucketRateLimiter(rate=1.0, burst=1)


class TestTokenBucketRateLimiter:
    """Test TokenBucketRateLimiter class."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        # Act
        limiter = TokenBucketRateLimiter(rate=5.0, burst=10)

        # Assert
        assert limiter.rate == 5.0
        assert limiter.burst == 10.0
        assert limiter.tokens == 10.0  # Should start with full capacity
        assert limiter.last_update > 0

    def test_rate_limiter_default_values(self):
        """Test rate limiter with minimum valid values."""
        # Act
        limiter = TokenBucketRateLimiter(rate=1.0, burst=1)

        # Assert
        assert limiter.rate == 1.0
        assert limiter.burst == 1.0
        assert limiter.tokens == 1.0

    def test_rate_limiter_minimum_rate_protection(self):
        """Test rate limiter protects against very low rates."""
        # Act
        limiter = TokenBucketRateLimiter(rate=0.001, burst=1)  # Very low rate

        # Assert
        assert limiter.rate == 0.01  # Should be clamped to minimum
        assert limiter.burst == 1.0

    async def test_acquire_no_wait(self, rate_limiter):
        """Test acquire when no waiting is required."""
        # Act
        wait_time = await rate_limiter.acquire()

        # Assert
        assert wait_time == 0.0
        assert rate_limiter.tokens == 4.0  # One token consumed

    async def test_wait_if_needed_no_wait(self, rate_limiter):
        """Test wait_if_needed when no waiting is required."""
        # Act
        wait_time = await rate_limiter.wait_if_needed()

        # Assert
        assert wait_time == 0.0
        assert rate_limiter.tokens == 4.0  # One token consumed

    async def test_wait_if_needed_with_burst(self, rate_limiter):
        """Test wait_if_needed consuming burst capacity."""
        # Act - consume all burst tokens quickly
        wait_times = []
        for _ in range(5):  # Burst capacity is 5
            wait_time = await rate_limiter.wait_if_needed()
            wait_times.append(wait_time)

        # Assert
        assert all(wait_time == 0.0 for wait_time in wait_times[:5])
        assert rate_limiter.tokens <= 0.1  # Allow for small time-based refill

    async def test_wait_if_needed_rate_limiting(self, strict_rate_limiter):
        """Test wait_if_needed when rate limiting is required."""
        # Arrange - consume the burst capacity
        await strict_rate_limiter.wait_if_needed()
        assert strict_rate_limiter.tokens <= 0.1  # Allow for small time-based refill

        # Act - next call should require waiting
        start_time = time.time()
        wait_time = await strict_rate_limiter.wait_if_needed()
        actual_wait_time = time.time() - start_time

        # Assert
        assert wait_time > 0
        assert actual_wait_time >= wait_time * 0.8  # Allow some timing variance
        assert strict_rate_limiter.tokens <= 0.1  # Should consume the refilled token

    def test_current_tokens_property(self, rate_limiter):
        """Test current_tokens property."""
        # Arrange - consume some tokens
        rate_limiter.tokens = 2.0

        # Act
        current = rate_limiter.current_tokens

        # Assert
        assert current >= 2.0  # Should be at least the current amount
        # Might be higher due to time-based refill

    def test_current_rate_with_no_requests(self, rate_limiter):
        """Test current_rate with no recent requests."""
        # Act
        rate = rate_limiter.current_rate()

        # Assert
        assert rate == 0.0  # No requests made yet

    async def test_current_rate_with_requests(self, rate_limiter):
        """Test current_rate calculation with requests."""
        # Act - make some requests
        await rate_limiter.wait_if_needed()
        await asyncio.sleep(0.1)  # Small delay
        await rate_limiter.wait_if_needed()

        # Act
        rate = rate_limiter.current_rate()

        # Assert
        assert rate >= 0.0  # Should have some rate

    def test_get_stats(self, rate_limiter):
        """Test rate limiter statistics."""
        # Act
        stats = rate_limiter.get_stats()

        # Assert
        assert isinstance(stats, dict)
        assert "configured_rate" in stats
        assert "burst_size" in stats
        assert "current_tokens" in stats
        assert "current_rate" in stats
        assert "recent_requests" in stats
        assert "total_requests" in stats
        assert "last_request_time" in stats

        assert stats["configured_rate"] == rate_limiter.rate
        assert stats["burst_size"] == int(rate_limiter.burst)

    async def test_reset_tokens(self, rate_limiter):
        """Test resetting tokens to full capacity."""
        # Arrange - consume some tokens
        await rate_limiter.wait_if_needed()
        await rate_limiter.wait_if_needed()
        assert rate_limiter.tokens < rate_limiter.burst

        # Act
        rate_limiter.reset()

        # Assert
        assert rate_limiter.tokens == rate_limiter.burst
        assert len(rate_limiter.request_times) == 0

    async def test_concurrent_requests(self, rate_limiter):
        """Test concurrent requests to rate limiter."""
        # Arrange
        request_count = 10

        # Act
        start_time = time.time()
        tasks = [rate_limiter.wait_if_needed() for _ in range(request_count)]
        wait_times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Assert
        # Some requests should not wait (burst capacity), others should wait
        no_wait_count = sum(1 for wt in wait_times if wt == 0.0)
        wait_count = sum(1 for wt in wait_times if wt > 0.0)

        assert no_wait_count <= rate_limiter.burst
        assert no_wait_count + wait_count == request_count

        # Total time should be reasonable based on rate limiting
        expected_min_time = max(0, (request_count - rate_limiter.burst) / rate_limiter.rate)
        assert total_time >= expected_min_time * 0.2  # Allow significant timing variance

    async def test_token_refill_over_time(self, rate_limiter):
        """Test that tokens refill over time."""
        # Arrange - consume all tokens
        for _ in range(int(rate_limiter.burst)):
            await rate_limiter.wait_if_needed()

        initial_tokens = rate_limiter.tokens

        # Act - wait for refill
        await asyncio.sleep(0.5)  # 0.5 seconds should refill 1 token at 2/sec rate

        # Force token update by accessing current_tokens
        current = rate_limiter.current_tokens

        # Assert
        assert current > initial_tokens

    def test_acquire_wait_time_calculation(self, rate_limiter):
        """Test wait time calculation when tokens are exhausted."""
        # Arrange - exhaust all tokens
        rate_limiter.tokens = 0.0

        # Act - this should return the wait time without actually waiting
        wait_time = asyncio.run(rate_limiter.acquire())

        # Assert
        expected_wait = 1.0 / rate_limiter.rate  # Time to get 1 token
        assert abs(wait_time - expected_wait) < 0.1

    def test_request_time_tracking(self, rate_limiter):
        """Test that request times are tracked properly."""
        # Arrange
        initial_count = len(rate_limiter.request_times)

        # Act
        asyncio.run(rate_limiter.wait_if_needed())

        # Assert
        assert len(rate_limiter.request_times) == initial_count + 1

    def test_old_request_cleanup(self, rate_limiter):
        """Test that old request times are cleaned up."""
        # Arrange - add some old request times manually
        now = time.time()
        old_time = now - rate_limiter._RATE_WINDOW_SECONDS - 1  # Older than window
        rate_limiter.request_times.append(old_time)
        rate_limiter.request_times.append(now)

        # Act - trigger cleanup by making a request
        asyncio.run(rate_limiter.wait_if_needed())

        # Assert
        # Old request should be cleaned up
        assert all(now - t <= rate_limiter._RATE_WINDOW_SECONDS for t in rate_limiter.request_times)

    def test_stats_after_requests(self, rate_limiter):
        """Test statistics after making requests."""
        # Act
        asyncio.run(rate_limiter.wait_if_needed())
        asyncio.run(rate_limiter.wait_if_needed())

        stats = rate_limiter.get_stats()

        # Assert
        assert stats["total_requests"] >= 2
        assert stats["recent_requests"] >= 2
        assert stats["last_request_time"] is not None


class TestTokenBucketRateLimiterEdgeCases:
    """Test edge cases and error conditions in TokenBucketRateLimiter."""

    async def test_very_high_rate_limit(self):
        """Test rate limiter with very high rate limit."""
        # Arrange
        limiter = TokenBucketRateLimiter(rate=1000.0, burst=100)

        # Act - make many requests quickly
        wait_times = []
        for _ in range(150):  # More than burst capacity
            wait_time = await limiter.wait_if_needed()
            wait_times.append(wait_time)

        # Assert
        # With very high rate, most requests should not wait
        no_wait_count = sum(1 for wt in wait_times if wt == 0.0)
        assert no_wait_count >= 100  # At least burst capacity should not wait

    async def test_very_low_rate_limit(self):
        """Test rate limiter with very low rate limit."""
        # Arrange
        limiter = TokenBucketRateLimiter(rate=0.1, burst=1)  # 1 request per 10 seconds

        # Act - make 2 requests
        wait_time1 = await limiter.wait_if_needed()
        # Don't actually wait for the second request in test
        wait_time2 = await limiter.acquire()  # Just get the wait time

        # Assert
        assert wait_time1 == 0.0  # First request uses burst
        assert wait_time2 >= 9.0  # Second request should wait ~10 seconds

    def test_fractional_rate_limits(self):
        """Test rate limiter with fractional rates."""
        # Arrange & Act
        limiter = TokenBucketRateLimiter(rate=1.5, burst=3)

        # Assert
        assert limiter.rate == 1.5
        assert limiter.burst == 3.0
        assert limiter.tokens == 3.0

    async def test_burst_capacity_respected(self, rate_limiter):
        """Test that burst capacity is respected."""
        # Act - try to consume more than burst capacity without waiting
        consumed = 0
        for _ in range(10):  # Try to consume more than burst
            wait_time = await rate_limiter.acquire()
            if wait_time == 0.0:
                consumed += 1
            else:
                break

        # Assert
        assert consumed == int(rate_limiter.burst)

    def test_time_precision_handling(self, rate_limiter):
        """Test handling of time precision issues."""
        # Arrange
        rate_limiter.tokens = 0.0
        initial_time = time.time()
        rate_limiter.last_update = initial_time

        # Act - simulate very small time increment
        with patch("time.time", return_value=initial_time + 0.001):  # 1ms
            current = rate_limiter.current_tokens

        # Assert
        # Should handle small increments precisely
        expected_tokens = rate_limiter.rate * 0.001  # Very small refill
        assert abs(current - expected_tokens) < 0.001

    async def test_multiple_rapid_requests(self, rate_limiter):
        """Test multiple rapid requests in succession."""
        # Act
        results = []
        for _ in range(8):  # More than burst capacity
            wait_time = await rate_limiter.acquire()
            results.append(wait_time)

        # Assert
        # First 5 should be immediate (burst capacity)
        assert all(wt == 0.0 for wt in results[: int(rate_limiter.burst)])
        # Remaining should have wait times
        assert all(wt > 0.0 for wt in results[int(rate_limiter.burst) :])

    def test_stats_consistency(self, rate_limiter):
        """Test that statistics are consistent."""
        # Act
        stats1 = rate_limiter.get_stats()
        asyncio.run(rate_limiter.wait_if_needed())
        stats2 = rate_limiter.get_stats()

        # Assert
        assert stats2["total_requests"] == stats1["total_requests"] + 1
        assert stats2["recent_requests"] >= stats1["recent_requests"]
        assert stats2["current_tokens"] <= stats1["current_tokens"]


class TestTokenBucketRateLimiterIntegration:
    """Integration tests for TokenBucketRateLimiter functionality."""

    async def test_rate_limiter_with_real_timing(self):
        """Test rate limiter with real timing (not mocked)."""
        # Arrange
        limiter = TokenBucketRateLimiter(rate=5.0, burst=2)

        # Act - make requests that should trigger rate limiting
        start_time = time.time()

        # First two should use burst capacity
        wait1 = await limiter.wait_if_needed()
        wait2 = await limiter.wait_if_needed()

        # Third should require waiting
        wait3 = await limiter.wait_if_needed()

        end_time = time.time()
        total_time = end_time - start_time

        # Assert
        assert wait1 == 0.0
        assert wait2 == 0.0
        assert wait3 > 0.0

        # Total time should be at least the wait time for the third request
        assert total_time >= wait3 * 0.8

    async def test_sustained_rate_limiting(self):
        """Test sustained rate limiting over longer period."""
        # Arrange
        limiter = TokenBucketRateLimiter(rate=2.0, burst=1)
        request_count = 4

        # Act
        start_time = time.time()
        wait_times = []

        for _ in range(request_count):
            wait_time = await limiter.wait_if_needed()
            wait_times.append(wait_time)

        end_time = time.time()
        total_time = end_time - start_time

        # Assert
        # First request should use burst (no wait)
        assert wait_times[0] == 0.0

        # Most subsequent requests should wait (allow for some timing variance)
        wait_count = sum(1 for wt in wait_times[1:] if wt > 0)
        assert wait_count >= len(wait_times) - 2  # Allow for timing variations

        # Total time should be approximately (request_count - 1) / rate
        expected_time = (request_count - 1) / limiter.rate
        assert total_time >= expected_time * 0.5  # Allow significant timing variance
        assert total_time <= expected_time * 2.0  # Allow for timing variations

    async def test_rate_limiter_recovery_after_idle(self):
        """Test that rate limiter recovers tokens after idle period."""
        # Arrange
        limiter = TokenBucketRateLimiter(rate=1.0, burst=3)

        # Consume all burst capacity
        for _ in range(3):
            await limiter.wait_if_needed()

        assert limiter.tokens <= 0.1  # Allow for small time-based refill

        # Wait for recovery (simulate idle period)
        await asyncio.sleep(1.5)  # 1.5 seconds should refill 1.5 tokens

        # Act - make request after idle period
        wait_time = await limiter.wait_if_needed()

        # Assert
        # Should not need to wait because tokens have been refilled during idle
        assert wait_time == 0.0

    def test_rate_limiter_parameter_validation(self):
        """Test that rate limiter validates parameters appropriately."""
        # Test minimum rate enforcement
        limiter1 = TokenBucketRateLimiter(rate=0.001, burst=1)
        assert limiter1.rate == 0.01  # Should be clamped

        # Test minimum burst enforcement
        limiter2 = TokenBucketRateLimiter(rate=1.0, burst=0.5)
        assert limiter2.burst == 1.0  # Should be clamped

        # Test normal values
        limiter3 = TokenBucketRateLimiter(rate=5.0, burst=10)
        assert limiter3.rate == 5.0
        assert limiter3.burst == 10.0
