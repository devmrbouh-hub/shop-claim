"""Pytest fixtures."""

from __future__ import annotations

import json
import os
from contextlib import AsyncExitStack
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from shop_claim_bridge.main import create_app


@pytest.fixture
def bridge_env(tmp_path: Path) -> Path:
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    catalog_src = Path(__file__).resolve().parents[1].parent / "catalog"
    offers_src = catalog_src / "offers.yaml"
    profiles_src = catalog_src / "vehicle_profiles.yaml"
    if offers_src.is_file():
        (catalog_dir / "offers.yaml").write_text(
            offers_src.read_text(encoding="utf-8"), encoding="utf-8"
        )
    else:
        (catalog_dir / "offers.yaml").write_text(
            "offers:\n  5001:\n    type: container\n    name: Test\n"
            "    container: SeaChest\n    items: []\n",
            encoding="utf-8",
        )
    if profiles_src.is_file():
        (catalog_dir / "vehicle_profiles.yaml").write_text(
            profiles_src.read_text(encoding="utf-8"), encoding="utf-8"
        )
    config = {
        "wargm": {
            "shop_id": "YOUR_SHOP_ID",
            "api_key": "YOUR_SHOP_API_KEY",
        },
        "server": {"host": "127.0.0.1", "port": 8787},
        "poll": {"interval_sec": 9999, "sync_retry_sec": 9999},
        "database": {"path": "data/test.db"},
        "catalog": {"path": "catalog/offers.yaml"},
        "servers": [
            {
                "server_id": "demo_map_1",
                "shop_server_id": 10001,
                "api_token": "test-token-1",
                "enabled": True,
            },
            {
                "server_id": "demo_map_2",
                "shop_server_id": 99999,
                "api_token": "test-token-2",
                "enabled": True,
            },
        ],
        "dev_mode": True,
    }
    cfg_path = tmp_path / "bridge.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")
    os.environ["SHOP_CLAIM_BRIDGE_CONFIG"] = str(cfg_path)
    yield tmp_path
    os.environ.pop("SHOP_CLAIM_BRIDGE_CONFIG", None)


@pytest_asyncio.fixture
async def client(bridge_env: Path):
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
