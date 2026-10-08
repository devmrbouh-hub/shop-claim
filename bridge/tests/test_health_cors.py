"""CORS for status page on GET /health only."""

import pytest
from httpx import AsyncClient

STATUS_ORIGIN = "http://127.0.0.1:8790"
OTHER_ORIGIN = "https://evil.example"


@pytest.mark.asyncio
async def test_health_cors_allows_status_origin(client: AsyncClient):
    r = await client.get("/health", headers={"Origin": STATUS_ORIGIN})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == STATUS_ORIGIN
    assert "Origin" in (r.headers.get("vary") or "")


@pytest.mark.asyncio
async def test_health_cors_rejects_other_origin(client: AsyncClient):
    r = await client.get("/health", headers={"Origin": OTHER_ORIGIN})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") is None


@pytest.mark.asyncio
async def test_health_cors_options_preflight(client: AsyncClient):
    r = await client.options("/health", headers={"Origin": STATUS_ORIGIN})
    assert r.status_code == 204
    assert r.headers.get("access-control-allow-origin") == STATUS_ORIGIN
    assert "GET" in (r.headers.get("access-control-allow-methods") or "")


@pytest.mark.asyncio
async def test_api_v1_no_cors_from_status_origin(client: AsyncClient):
    r = await client.get(
        "/api/v1/servers/demo_map_1/players/76561198000000001/pending",
        headers={
            "Origin": STATUS_ORIGIN,
            "Authorization": "Bearer test-token-1",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") is None
