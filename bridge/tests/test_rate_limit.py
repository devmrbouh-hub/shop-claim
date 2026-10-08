"""Bridge API rate limit tests."""

import pytest
from httpx import AsyncClient

from shop_claim_bridge.main import create_app
from shop_claim_bridge.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


def test_rate_limiter_blocks_after_max():
    for _ in range(300):
        assert rate_limiter.allow("api_v1:127.0.0.1", max_events=300, window_sec=60)
    assert not rate_limiter.allow("api_v1:127.0.0.1", max_events=300, window_sec=60)


def test_app_registers_rate_limit_middleware(bridge_env):
    app = create_app()
    assert any("ApiRateLimitMiddleware" in repr(m) for m in app.user_middleware)


@pytest.mark.asyncio
async def test_health_not_rate_limited(client: AsyncClient):
    for _ in range(10):
        r = await client.get("/health")
        assert r.status_code == 200
