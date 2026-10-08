"""Multi-tenant API, DB isolation, and poller tests."""

from __future__ import annotations

import json
import os
from contextlib import AsyncExitStack
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from shop_claim_bridge.main import create_app
from shop_claim_bridge.poller import Poller


def _write_catalog(dir_path: Path, offers_yaml: str) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "offers.yaml").write_text(offers_yaml, encoding="utf-8")
    (dir_path / "vehicle_profiles.yaml").write_text("profiles: {}\n", encoding="utf-8")


@pytest.fixture
def multi_tenant_env(tmp_path: Path) -> Path:
    cat_a = tmp_path / "tenants" / "tenant_a"
    cat_b = tmp_path / "tenants" / "tenant_b"
    _write_catalog(
        cat_a,
        "offers:\n  1001:\n    type: container\n    name: A Box\n"
        "    container: SeaChest\n    items: []\n",
    )
    _write_catalog(
        cat_b,
        "offers:\n  2001:\n    type: container\n    name: B Box\n"
        "    container: SeaChest\n    items: []\n",
    )
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    future = (date.today() + timedelta(days=365)).isoformat()
    config = {
        "server": {"host": "127.0.0.1", "port": 8787},
        "poll": {"interval_sec": 9999, "sync_retry_sec": 9999},
        "database": {"path": "data/test.db"},
        "dev_mode": True,
        "tenants": [
            {
                "tenant_id": "tenant_a",
                "enabled": True,
                "subscription_until": future,
                "wargm": {"shop_id": "SHOP_A", "api_key": "key-a"},
                "catalog": {
                    "offers_path": "tenants/tenant_a/offers.yaml",
                    "vehicle_profiles_path": "tenants/tenant_a/vehicle_profiles.yaml",
                },
                "servers": [
                    {
                        "server_id": "server_a",
                        "shop_server_id": 11111,
                        "api_token": "token-a",
                        "enabled": True,
                    }
                ],
            },
            {
                "tenant_id": "tenant_b",
                "enabled": True,
                "subscription_until": yesterday,
                "wargm": {"shop_id": "SHOP_B", "api_key": "key-b"},
                "catalog": {
                    "offers_path": "tenants/tenant_b/offers.yaml",
                    "vehicle_profiles_path": "tenants/tenant_b/vehicle_profiles.yaml",
                },
                "servers": [
                    {
                        "server_id": "server_b",
                        "shop_server_id": 22222,
                        "api_token": "token-b",
                        "enabled": True,
                    }
                ],
            },
        ],
    }
    cfg_path = tmp_path / "bridge.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")
    os.environ["SHOP_CLAIM_BRIDGE_CONFIG"] = str(cfg_path)
    yield tmp_path
    os.environ.pop("SHOP_CLAIM_BRIDGE_CONFIG", None)


@pytest_asyncio.fixture
async def multi_client(multi_tenant_env: Path):
    import shop_claim_bridge.main as main_module

    main_module.state = None
    main_module.poller = None
    app = create_app()
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(app.router.lifespan_context(app))
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", trust_env=False
        ) as ac:
            yield ac
    if main_module.poller:
        await main_module.poller.stop()
    main_module.state = None
    main_module.poller = None


@pytest.mark.asyncio
async def test_health_reports_two_tenants(multi_client: AsyncClient):
    r = await multi_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_count"] == 2
    assert len(body["tenants"]) == 2
    poll_by_id = {t["tenant_id"]: t["poll"] for t in body["tenants"]}
    assert poll_by_id["tenant_a"] is True
    assert poll_by_id["tenant_b"] is False


@pytest.mark.asyncio
async def test_subscription_expired_returns_403(multi_client: AsyncClient):
    r = await multi_client.get(
        "/api/v1/servers/server_b/players/76561198000000001/pending",
        headers={"Authorization": "Bearer token-b"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "Subscription expired"


@pytest.mark.asyncio
async def test_pending_scoped_by_tenant(multi_client: AsyncClient):
    r = await multi_client.post(
        "/dev/mock-operation",
        json={
            "steam_id": "76561198000000001",
            "offer_id": 1001,
            "shop_server_id": 11111,
            "server_id": "server_a",
        },
    )
    assert r.status_code == 200
    op_a = r.json()["operation_id"]

    # Same shop_server_id as tenant_b server would use if misconfigured — use server_b token
    # but subscription expired; use active tenant with wrong offer for isolation via DB
    r = await multi_client.get(
        "/api/v1/servers/server_a/players/76561198000000001/pending",
        headers={"Authorization": "Bearer token-a"},
    )
    assert r.status_code == 200
    ids = [x["operation_id"] for x in r.json()]
    assert op_a in ids

    # tenant_b cannot list tenant_a orders even if shop_server_id collided (different tenant_id in DB)
    import shop_claim_bridge.main as main_module

    state = main_module.state
    assert state is not None
    rows_b = await state.db.list_pending("tenant_b", 11111, "76561198000000001")
    assert rows_b == []


@pytest.mark.asyncio
async def test_poll_uses_tenant_catalog(multi_tenant_env: Path):
    import shop_claim_bridge.main as main_module
    from shop_claim_bridge.app_state import AppState
    from shop_claim_bridge.config import load_config

    config, base_dir = load_config(multi_tenant_env / "bridge.json")
    state = AppState(config, base_dir)
    await state.db.connect(state._default_tenant_id)
    poller = Poller(state)
    tenant = state.registry.get_tenant("tenant_a")
    assert tenant is not None

    mock_ops = [
        {
            "operation_id": "op-unmapped",
            "offer_id": "2001",
            "steam_id": "76561198000000001",
            "shop_server_id": 11111,
        },
        {
            "operation_id": "op-mapped",
            "offer_id": "1001",
            "steam_id": "76561198000000001",
            "shop_server_id": 11111,
        },
    ]
    mock_client = AsyncMock()
    mock_client.fetch_all_pending_operations = AsyncMock(return_value=mock_ops)

    with patch.object(state, "get_wargm_client", return_value=mock_client):
        await poller._poll_once(tenant)

    unmapped = await state.db.get_order("op-unmapped")
    mapped = await state.db.get_order("op-mapped")
    assert unmapped is not None
    assert unmapped["local_status"] == "unmapped"
    assert unmapped["tenant_id"] == "tenant_a"
    assert mapped is not None
    assert mapped["local_status"] == "available"

    await state.db.close()


@pytest.mark.asyncio
async def test_poll_skips_foreign_shop_server_id(multi_tenant_env: Path):
    import shop_claim_bridge.main as main_module
    from shop_claim_bridge.app_state import AppState
    from shop_claim_bridge.config import load_config

    config, base_dir = load_config(multi_tenant_env / "bridge.json")
    state = AppState(config, base_dir)
    await state.db.connect(state._default_tenant_id)
    poller = Poller(state)
    tenant = state.registry.get_tenant("tenant_a")
    assert tenant is not None

    mock_client = AsyncMock()
    mock_client.fetch_all_pending_operations = AsyncMock(
        return_value=[
            {
                "operation_id": "op-foreign",
                "offer_id": "1001",
                "steam_id": "76561198000000001",
                "shop_server_id": 99999,
            }
        ]
    )

    with patch.object(state, "get_wargm_client", return_value=mock_client):
        await poller._poll_once(tenant)

    assert await state.db.get_order("op-foreign") is None
    await state.db.close()


@pytest.mark.asyncio
async def test_upsert_tenant_mismatch_skipped(multi_tenant_env: Path):
    from shop_claim_bridge.app_state import AppState
    from shop_claim_bridge.config import load_config

    config, base_dir = load_config(multi_tenant_env / "bridge.json")
    state = AppState(config, base_dir)
    await state.db.connect(state._default_tenant_id)

    await state.db.upsert_from_wargm(
        "shared-op",
        "1001",
        "76561198000000001",
        11111,
        "tenant_a",
        has_catalog_entry=True,
    )
    await state.db.upsert_from_wargm(
        "shared-op",
        "1001",
        "76561198000000001",
        11111,
        "tenant_b",
        has_catalog_entry=True,
    )
    order = await state.db.get_order("shared-op")
    assert order is not None
    assert order["tenant_id"] == "tenant_a"
    await state.db.close()
