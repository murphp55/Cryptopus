"""Tests for the RateLimiter."""
from cryptopus.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_allows_within_limit(self):
        limiter = RateLimiter(max_calls=5, period_seconds=60.0)
        for _ in range(5):
            assert limiter.acquire() is True

    def test_blocks_over_limit(self):
        limiter = RateLimiter(max_calls=3, period_seconds=60.0)
        for _ in range(3):
            limiter.acquire()
        assert limiter.acquire() is False

    def test_single_call_succeeds(self):
        limiter = RateLimiter(max_calls=1, period_seconds=60.0)
        assert limiter.acquire() is True
        assert limiter.acquire() is False
