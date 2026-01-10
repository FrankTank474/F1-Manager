import time
import asyncio
from collections import defaultdict
from typing import Dict, List

from ..config import settings


class RateLimiter:
    """In-memory rate limiter for login attempts."""

    def __init__(
        self,
        max_requests: int = None,
        window_seconds: int = None,
    ):
        self.max_requests = max_requests or settings.RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()

        async with self._lock:
            # Clean old entries
            self._requests[key] = [
                t for t in self._requests[key] if now - t < self.window_seconds
            ]

            if len(self._requests[key]) >= self.max_requests:
                return False

            self._requests[key].append(now)
            return True

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key (e.g., after successful login)."""
        async with self._lock:
            self._requests.pop(key, None)

    def get_remaining(self, key: str) -> int:
        """Get remaining requests allowed for a key."""
        now = time.time()
        recent = [t for t in self._requests.get(key, []) if now - t < self.window_seconds]
        return max(0, self.max_requests - len(recent))

    def get_reset_time(self, key: str) -> int:
        """Get seconds until rate limit resets for a key."""
        if key not in self._requests or not self._requests[key]:
            return 0
        oldest = min(self._requests[key])
        reset_at = oldest + self.window_seconds
        return max(0, int(reset_at - time.time()))


# Global rate limiter instance
rate_limiter = RateLimiter()
