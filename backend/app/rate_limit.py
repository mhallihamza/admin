"""In-memory sliding-window rate limiter (per user or IP + scope).

Good enough for a single-instance deployment; swap for Redis when scaling
out. Fails open only on internal errors — never for the caller's benefit.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > window_seconds:
            window.popleft()
        if len(window) >= limit:
            retry_after = max(1, int(window_seconds - (now - window[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded.",
                headers={"Retry-After": str(retry_after)},
            )
        window.append(now)

    def reset(self) -> None:
        self._hits.clear()


rate_limiter = RateLimiter()


def client_key(request: Request, user_id: str | None) -> str:
    if user_id:
        return f"user:{user_id}"
    ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


def rate_limit(scope: str, limit: int):
    """Dependency factory: limits requests per user/IP for a given scope."""

    async def dependency(request: Request) -> None:
        user_id: str | None = None
        try:
            user = request.scope.get("current_user")
            if user is not None:
                user_id = user.id
        except Exception:
            user_id = None
        rate_limiter.check(f"{scope}:{client_key(request, user_id)}", limit)

    return dependency
