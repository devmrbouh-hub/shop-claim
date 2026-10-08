"""Race conditions and idempotent order transitions."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

import shop_claim_bridge.main as main_module
from shop_claim_bridge.order_service import OrderService
from shop_claim_bridge.poller import Poller

TOKEN = "test-token-1"
STEAM = "76561198000000001"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _insert_wargm_spawned_container(
    operation_id: str = "wargm-race-1",
) -> None:
    assert main_module.state is not None
    db = main_module.state.db
    now = _now()
    await db.conn.execute(
        """
        INSERT INTO orders (
            operation_id, offer_id, steam_id, shop_server_id, tenant_id,
            local_status, source, wargm_confirmed, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'spawned', 'wargm', 0, ?, ?)
        """,
        (operation_id, "5001", STEAM, 10001, "default", now, now),
    )
    await db.conn.commit()


@pytest.mark.asyncio
async def test_delivered_idempotent(client: AsyncClient):
    r = await client.post(
        "/dev/mock-operation",
        json={
            "steam_id": STEAM,
            "offer_id": 5001,
            "shop_server_id": 10001,
            "server_id": "demo_map_1",
        },
    )
    op_id = r.json()["operation_id"]

    await client.post(
        f"/api/v1/servers/demo_map_1/operations/{op_id}/spawned",
        headers=HEADERS,
    )
    r1 = await client.post(
        f"/api/v1/servers/demo_map_1/operations/{op_id}/delivered",
        headers=HEADERS,
    )
    assert r1.status_code == 200

    r2 = await client.post(
        f"/api/v1/servers/demo_map_1/operations/{op_id}/delivered",
        headers=HEADERS,
    )
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_spawned_concurrent(client: AsyncClient):
    r = await client.post(
        "/dev/mock-operation",
        json={
            "steam_id": STEAM,
            "offer_id": 5001,
            "shop_server_id": 10001,
            "server_id": "demo_map_1",
        },
    )
    op_id = r.json()["operation_id"]

    results = await asyncio.gather(
        client.post(
            f"/api/v1/servers/demo_map_1/operations/{op_id}/spawned",
            headers=HEADERS,
        ),
        client.post(
            f"/api/v1/servers/demo_map_1/operations/{op_id}/spawned",
            headers=HEADERS,
        ),
    )
    assert all(r.status_code == 200 for r in results)
    order = await main_module.state.db.get_order(op_id)
    assert order["local_status"] == "spawned"


@pytest.mark.asyncio
async def test_delivered_concurrent_wargm(client: AsyncClient):
    await _insert_wargm_spawned_container("wargm-concurrent-1")
    assert main_module.state is not None

    mock_client = AsyncMock()
    mock_client.operation_success = AsyncMock(return_value=True)

    with patch.object(main_module.state, "get_wargm_client", return_value=mock_client):
        results = await asyncio.gather(
            client.post(
                "/api/v1/servers/demo_map_1/operations/wargm-concurrent-1/delivered",
                headers=HEADERS,
            ),
            client.post(
                "/api/v1/servers/demo_map_1/operations/wargm-concurrent-1/delivered",
                headers=HEADERS,
            ),
        )

    assert all(r.status_code == 200 for r in results)
    assert mock_client.operation_success.call_count == 1
    order = await main_module.state.db.get_order("wargm-concurrent-1")
    assert order["local_status"] == "done"
    assert order["wargm_confirmed"] == 1


@pytest.mark.asyncio
async def test_handler_poller_no_double_sync(client: AsyncClient):
    await _insert_wargm_spawned_container("wargm-poller-1")
    assert main_module.state is not None

    mock_client = AsyncMock()
    mock_client.operation_success = AsyncMock(return_value=True)

    tenant = main_module.state.registry.get_tenant("default")
    assert tenant is not None
    poller = Poller(main_module.state)

    with patch.object(main_module.state, "get_wargm_client", return_value=mock_client):
        await asyncio.gather(
            client.post(
                "/api/v1/servers/demo_map_1/operations/wargm-poller-1/delivered",
                headers=HEADERS,
            ),
            poller._sync_once(tenant),
        )

    assert mock_client.operation_success.call_count == 1


@pytest.mark.asyncio
async def test_delivered_retry_unconfirmed(client: AsyncClient):
    await _insert_wargm_spawned_container("wargm-retry-1")
    assert main_module.state is not None

    mock_client = AsyncMock()
    mock_client.operation_success = AsyncMock(side_effect=[False, True])

    with patch.object(main_module.state, "get_wargm_client", return_value=mock_client):
        r1 = await client.post(
            "/api/v1/servers/demo_map_1/operations/wargm-retry-1/delivered",
            headers=HEADERS,
        )
        assert r1.status_code == 200
        order = await main_module.state.db.get_order("wargm-retry-1")
        assert order["wargm_confirmed"] == 0

        r2 = await client.post(
            "/api/v1/servers/demo_map_1/operations/wargm-retry-1/delivered",
            headers=HEADERS,
        )
        assert r2.status_code == 200

    assert mock_client.operation_success.call_count == 2
    order = await main_module.state.db.get_order("wargm-retry-1")
    assert order["wargm_confirmed"] == 1


@pytest.mark.asyncio
async def test_transition_to_done_db_unit(bridge_env):
    from shop_claim_bridge.db import Database

    db_path = bridge_env / "unit.db"
    db = Database(db_path)
    await db.connect("default")
    now = _now()
    await db.conn.execute(
        """
        INSERT INTO orders (
            operation_id, offer_id, steam_id, shop_server_id, tenant_id,
            local_status, source, wargm_confirmed, created_at, updated_at
        ) VALUES ('op-u1', '1', 's', 1, 'default', 'spawned', 'wargm', 0, ?, ?)
        """,
        (now, now),
    )
    await db.conn.commit()

    r1 = await db.transition_to_done("op-u1", allowed_from=("spawned",), wargm_confirmed=False)
    assert r1 == "applied"
    r2 = await db.transition_to_done("op-u1", allowed_from=("spawned",), wargm_confirmed=False)
    assert r2 == "already_in_target"

    await db.conn.execute(
        "UPDATE orders SET local_status='failed' WHERE operation_id='op-u1'"
    )
    await db.conn.commit()
    r3 = await db.transition_to_done("op-u1", allowed_from=("spawned",), wargm_confirmed=False)
    assert r3 == "invalid_state"

    await db.close()


@pytest.mark.asyncio
async def test_sync_wargm_if_needed_skips_confirmed(client: AsyncClient):
    await _insert_wargm_spawned_container("wargm-skip-1")
    assert main_module.state is not None

    mock_client = AsyncMock()
    mock_client.operation_success = AsyncMock(return_value=True)

    svc = OrderService(main_module.state)
    with patch.object(main_module.state, "get_wargm_client", return_value=mock_client):
        await svc.mark_delivered("demo_map_1", "wargm-skip-1")
        await svc.sync_wargm_if_needed("wargm-skip-1")

    assert mock_client.operation_success.call_count == 1
