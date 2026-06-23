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


class DemoUsageLimiter:
    def __init__(self) -> None:
        self._embedding_requests: dict[str, deque[float]] = defaultdict(deque)
        self._answer_requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    @staticmethod
    def _prune(requests: deque[float], window_start: float) -> None:
        while requests and requests[0] <= window_start:
            requests.popleft()

    @staticmethod
    def _raise_limit(window_seconds: int, oldest: float, now: float) -> None:
        retry_after = max(1, round(window_seconds - (now - oldest)))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Public demo usage limit reached",
            headers={"Retry-After": str(retry_after)},
        )

    def check_embedding(
        self,
        key: str,
        embedding_limit: int,
        window_seconds: int,
    ) -> None:
        now = monotonic()
        window_start = now - window_seconds

        with self._lock:
            embeddings = self._embedding_requests[key]
            self._prune(embeddings, window_start)

            if len(embeddings) >= embedding_limit:
                self._raise_limit(window_seconds, embeddings[0], now)

            embeddings.append(now)

    def check_answer(
        self,
        key: str,
        answer_limit: int,
        window_seconds: int,
    ) -> None:
        now = monotonic()
        window_start = now - window_seconds

        with self._lock:
            answers = self._answer_requests[key]
            self._prune(answers, window_start)

            if len(answers) >= answer_limit:
                self._raise_limit(window_seconds, answers[0], now)

            answers.append(now)


demo_usage_limiter = DemoUsageLimiter()


def enforce_rate_limit(
    principal: Principal = Depends(require_principal),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if principal.is_demo:
        return principal

    rate_limiter.check(
        key=principal.rate_limit_key,
        request_limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    return principal


def enforce_demo_embedding_limit(
    principal: Principal,
    settings: Settings,
) -> None:
    if not principal.is_demo:
        return

    demo_usage_limiter.check_embedding(
        key=principal.rate_limit_key,
        embedding_limit=settings.demo_embedding_requests,
        window_seconds=settings.demo_window_seconds,
    )


def enforce_demo_answer_limit(
    principal: Principal,
    settings: Settings,
) -> None:
    if not principal.is_demo:
        return

    demo_usage_limiter.check_answer(
        key=principal.rate_limit_key,
        answer_limit=settings.demo_answer_requests,
        window_seconds=settings.demo_window_seconds,
    )
