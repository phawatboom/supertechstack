import pytest
from fastapi import HTTPException

from app.rate_limit import DemoUsageLimiter


def test_demo_embedding_limit_is_enforced():
    limiter = DemoUsageLimiter()

    limiter.check_embedding("ip:demo", 2, 60)
    limiter.check_embedding("ip:demo", 2, 60)

    with pytest.raises(HTTPException) as error:
        limiter.check_embedding("ip:demo", 2, 60)

    assert error.value.status_code == 429


def test_demo_answer_limit_is_separate_from_search_limit():
    limiter = DemoUsageLimiter()

    limiter.check_embedding("ip:demo", 1, 60)
    limiter.check_answer("ip:demo", 1, 60)

    with pytest.raises(HTTPException) as error:
        limiter.check_answer("ip:demo", 1, 60)

    assert error.value.status_code == 429
