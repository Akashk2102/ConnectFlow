import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """
    In-memory Sliding Window Rate Limiter.
    Tracks timestamps of incoming requests per identifier (API key or IP).
    """

    def __init__(self, requests_limit: int = 60, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self._history: Dict[str, List[float]] = defaultdict(list)

    def _clean_expired(self, key: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._history[key] = [t for t in self._history[key] if t > cutoff]

    async def __call__(self, request: Request) -> None:
        # Prefer X-API-Key if present, fallback to client IP
        client_key = request.headers.get("X-API-Key")
        if not client_key:
            client_key = request.client.host if request.client else "unknown_client"

        now = time.time()
        self._clean_expired(client_key, now)

        if len(self._history[client_key]) >= self.requests_limit:
            oldest = self._history[client_key][0]
            retry_after = max(1, int(self.window_seconds - (now - oldest)))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: maximum {self.requests_limit} requests per {self.window_seconds}s.",
                headers={"Retry-After": str(retry_after)},
            )

        self._history[client_key].append(now)

    def reset(self):
        self._history.clear()


# Default global rate limiter: 100 requests per 60s
default_rate_limiter = SlidingWindowRateLimiter(requests_limit=100, window_seconds=60)
