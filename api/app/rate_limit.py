from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import Depends, HTTPException, status

from app.config import Settings, get_settings
from app.security import Principal, require_principal


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(
        self,
        key: str,
        request_limit: int,
        window_seconds: int,
    ) -> None:
        now = monotonic()
        window_start = now - window_seconds

        with self._lock:
            requests = self._requests[key]

            while requests and requests[0] <= window_start:
                requests.popleft()

            if len(requests) >= request_limit:
                retry_after = max(
                    1,
                    round(window_seconds - (now - requests[0])),
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)},
                )

            requests.append(now)


rate_limiter = InMemoryRateLimiter()


def enforce_rate_limit(
    principal: Principal = Depends(require_principal),
    settings: Settings = Depends(get_settings),
) -> Principal:
    rate_limiter.check(
        key=principal.rate_limit_key,
        request_limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    return principal
