"""Pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from shop_claim_portal.config import Settings, get_settings
from shop_claim_portal.db import create_tables, dispose_db, init_db
from shop_claim_portal.main import create_app
from shop_claim_portal.bootstrap import ensure_bootstrap_admin
from shop_claim_portal.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    rate_limiter._hits.clear()


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_portal.db"


@pytest.fixture
def test_settings(tmp_db: Path, tmp_path: Path) -> Settings:
    os.environ["PORTAL_ENV"] = "development"
    os.environ["PORTAL_DATABASE_PATH"] = str(tmp_db)
    os.environ["PORTAL_JWT_SECRET"] = "test-secret-key-32-bytes-minimum!!"
    os.environ["PORTAL_FERNET_KEY"] = ""
    os.environ["PORTAL_BOOTSTRAP_ADMIN_EMAIL"] = "admin@example.com"
    os.environ["PORTAL_BOOTSTRAP_ADMIN_PASSWORD"] = "adminpass123"
    os.environ["PORTAL_BRIDGE_CONFIG_PATH"] = str(tmp_path / "bridge.json")
    os.environ["PORTAL_YOOKASSA_SHOP_ID"] = "test_shop"
    os.environ["PORTAL_YOOKASSA_SECRET_KEY"] = "test_secret"
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
async def client(test_settings: Settings, tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    bridge = tmp_path / "bridge.json"
    bridge.write_text(
        '{"server":{"host":"127.0.0.1","port":8787},"poll":{"interval_sec":45},'
        '"database":{"path":"data/orders.db"},"dev_mode":false,"tenants":[]}\n',
        encoding="utf-8",
    )
    init_db(test_settings, tmp_path)
    await create_tables()
    from shop_claim_portal.db import get_session

    async for session in get_session():
        await ensure_bootstrap_admin(session, test_settings)
        break
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await dispose_db()
    get_settings.cache_clear()


@pytest.fixture
async def admin_cookies(client: AsyncClient) -> dict:
    r = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "adminpass123"},
    )
    assert r.status_code == 200
    return dict(r.cookies)
