"""API integration tests."""

import pytest
from httpx import AsyncClient

TOKEN = "test-token-1"
STEAM = "76561198000000001"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
SERVER = "demo_map_1"


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["dev_mode"] is True
    assert body["tenant_count"] == 1
    assert body["tenants"][0]["tenant_id"] == "default"


@pytest.mark.asyncio
async def test_mock_and_pending_flow(client: AsyncClient):
    r = await client.post(
        "/dev/mock-operation",
        json={
            "steam_id": STEAM,
            "offer_id": 5001,
            "shop_server_id": 10001,
            "server_id": SERVER,
        },
    )
    assert r.status_code == 200
    op_id = r.json()["operation_id"]
    assert op_id.startswith("mock-")

    r = await client.get(
        f"/api/v1/servers/{SERVER}/players/{STEAM}/pending",
        headers=HEADERS,
    )
    assert r.status_code == 200
    pending = r.json()
    assert len(pending) == 1
    assert pending[0]["operation_id"] == op_id
    assert pending[0]["type"] == "container"
    assert pending[0]["status"] == "available"

    r = await client.post(
        f"/api/v1/servers/{SERVER}/operations/{op_id}/spawned",
        headers=HEADERS,
    )
    assert r.status_code == 200

    r = await client.post(
        f"/api/v1/servers/{SERVER}/operations/{op_id}/delivered",
        headers=HEADERS,
    )
    assert r.status_code == 200

    r = await client.get(
        f"/api/v1/servers/{SERVER}/players/{STEAM}/pending",
        headers=HEADERS,
    )
    assert r.json() == []


@pytest.mark.asyncio
async def test_vehicle_delivered_without_spawned(client: AsyncClient):
    r = await client.post(
        "/dev/mock-operation",
        json={
            "steam_id": STEAM,
            "offer_id": 5010,
            "shop_server_id": 10001,
            "server_id": SERVER,
        },
    )
    op_id = r.json()["operation_id"]

    r = await client.post(
        f"/api/v1/servers/{SERVER}/operations/{op_id}/spawned",
        headers=HEADERS,
    )
    assert r.status_code == 422

    r = await client.post(
        f"/api/v1/servers/{SERVER}/operations/{op_id}/delivered",
        headers=HEADERS,
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_unknown_offer_mock_rejected(client: AsyncClient):
    r = await client.post(
        "/dev/mock-operation",
        json={
            "steam_id": STEAM,
            "offer_id": 999999,
            "shop_server_id": 10001,
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_auth_required(client: AsyncClient):
    r = await client.get(f"/api/v1/servers/{SERVER}/players/{STEAM}/pending")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_auth_query_token_pending(client: AsyncClient):
    r = await client.post(
        "/dev/mock-operation",
        json={
            "steam_id": STEAM,
            "offer_id": 5001,
            "shop_server_id": 10001,
            "server_id": SERVER,
        },
    )
    assert r.status_code == 200

    r = await client.get(
        f"/api/v1/servers/{SERVER}/players/{STEAM}/pending?api_token={TOKEN}",
    )
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_wrong_server_token(client: AsyncClient):
    r = await client.get(
        f"/api/v1/servers/demo_map_2/players/{STEAM}/pending",
        headers={"Authorization": "Bearer test-token-1"},
    )
    assert r.status_code == 403
