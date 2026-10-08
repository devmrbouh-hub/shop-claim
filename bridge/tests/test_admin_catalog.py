"""Test Bridge admin catalog reload."""

from __future__ import annotations

import json
from contextlib import AsyncExitStack
from datetime import date, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from shop_claim_bridge.main import create_app


@pytest.fixture
def admin_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cat = tmp_path / "tenants" / "t1"
    cat.mkdir(parents=True)
    (cat / "offers.yaml").write_text(
        "offers:\n  1001:\n    type: container\n    name: Before\n"
        "    container: SeaChest\n    items: []\n",
        encoding="utf-8",
    )
    (cat / "vehicle_profiles.yaml").write_text("profiles: {}\n", encoding="utf-8")
    future = (date.today() + timedelta(days=365)).isoformat()
    config = {
        "server": {"host": "127.0.0.1", "port": 8787},
        "poll": {"interval_sec": 9999},
        "database": {"path": "data/test.db"},
        "dev_mode": False,
        "tenants": [
            {
                "tenant_id": "t1",
                "enabled": True,
                "subscription_until": future,
                "wargm": {"shop_id": "1", "api_key": "k"},
                "catalog": {
                    "offers_path": "tenants/t1/offers.yaml",
                    "vehicle_profiles_path": "tenants/t1/vehicle_profiles.yaml",
                },
                "servers": [
                    {
                        "server_id": "s1",
                        "shop_server_id": 1,
                        "api_token": "tok",
                        "enabled": True,
                    }
                ],
            }
        ],
    }
    cfg_path = tmp_path / "bridge.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("SHOP_CLAIM_BRIDGE_CONFIG", str(cfg_path))
    monkeypatch.setenv("BRIDGE_ADMIN_SECRET", "test-admin-secret")
    return tmp_path


@pytest_asyncio.fixture
async def admin_client(admin_env: Path) -> AsyncClient:
    import shop_claim_bridge.main as bridge_main

    bridge_main.state = None
    bridge_main.poller = None
    app = create_app()
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(app.router.lifespan_context(app))
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    if bridge_main.poller:
        await bridge_main.poller.stop()
    bridge_main.state = None
    bridge_main.poller = None


@pytest.mark.asyncio
async def test_catalog_reload_requires_secret(admin_client: AsyncClient) -> None:
    r = await admin_client.post("/admin/catalog/reload?tenant_id=t1")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_catalog_reload_picks_up_yaml_change(
    admin_client: AsyncClient, admin_env: Path
) -> None:
    import shop_claim_bridge.main as bridge_main

    assert bridge_main.state is not None
    cat = bridge_main.state.registry.get_catalog_for_server("s1")
    assert cat is not None
    assert cat.get("1001")["name"] == "Before"

    offers = admin_env / "tenants" / "t1" / "offers.yaml"
    offers.write_text(
        "offers:\n  1001:\n    type: container\n    name: After\n"
        "    container: SeaChest\n    items: []\n",
        encoding="utf-8",
    )

    r = await admin_client.post(
        "/admin/catalog/reload?tenant_id=t1",
        headers={"X-Bridge-Admin-Secret": "test-admin-secret"},
    )
    assert r.status_code == 200
    assert r.json()["reloaded"] >= 1

    cat2 = bridge_main.state.registry.get_catalog_for_server("s1")
    assert cat2 is not None
    assert cat2.get("1001")["name"] == "After"
