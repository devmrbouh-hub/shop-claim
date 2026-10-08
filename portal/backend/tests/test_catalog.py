"""Catalog API tests."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient

from shop_claim_portal.models import GameServer, Tenant, User, UserRole
from shop_claim_portal.services.crypto import encrypt_secret
from shop_claim_portal.services.password import hash_password


@pytest.fixture
async def catalog_env(client: AsyncClient, tmp_path: Path, test_settings) -> dict:
    from shop_claim_portal.db import get_session

    catalog_root = tmp_path / "bridge-data"
    tenant_dir = catalog_root / "tenants" / "acme"
    tenant_dir.mkdir(parents=True)
    (tenant_dir / "offers.yaml").write_text(
        "offers:\n  1001:\n    type: container\n    name: Published\n"
        "    container: SeaChest\n    items:\n      - class: BandageDressing\n        qty: 1\n",
        encoding="utf-8",
    )
    (tenant_dir / "vehicle_profiles.yaml").write_text("profiles: {}\n", encoding="utf-8")

    import os

    os.environ["PORTAL_CATALOG_ROOT"] = str(catalog_root)
    os.environ["PORTAL_BRIDGE_ADMIN_SECRET"] = "test-secret"
    test_settings.__class__.model_config = test_settings.model_config  # keep cached
    from shop_claim_portal.config import get_settings

    get_settings.cache_clear()

    async for session in get_session():
        tenant = Tenant(
            tenant_id="acme",
            enabled=True,
            subscription_until=date.today() + timedelta(days=30),
            wargm_shop_id="1",
            wargm_api_key_enc=encrypt_secret("key"),
            catalog_offers_path="tenants/acme/offers.yaml",
            catalog_vehicle_profiles_path="tenants/acme/vehicle_profiles.yaml",
        )
        session.add(tenant)
        await session.flush()
        sub = User(
            email="sub@example.com",
            password_hash=hash_password("subpass12345"),
            role=UserRole.subscriber.value,
            tenant_pk=tenant.id,
            is_active=True,
        )
        session.add(sub)
        session.add(
            GameServer(
                tenant_pk=tenant.id,
                server_id="srv1",
                shop_server_id=10001,
                api_token_enc=encrypt_secret("tok"),
                enabled=True,
            )
        )
        await session.commit()
        break

    sub_cookies = dict(
        (
            await client.post(
                "/api/auth/login",
                json={"email": "sub@example.com", "password": "subpass12345"},
            )
        ).cookies
    )
    return {
        "cookies": sub_cookies,
        "catalog_root": catalog_root,
        "tenant_dir": tenant_dir,
    }


@pytest.mark.asyncio
async def test_get_catalog_merged(client: AsyncClient, catalog_env: dict) -> None:
    r = await client.get("/api/tenant/catalog", cookies=catalog_env["cookies"])
    assert r.status_code == 200
    data = r.json()
    assert "1001" in data["offers"]
    assert data["offers"]["1001"]["name"] == "Published"
    assert data["has_unpublished_changes"] is False


@pytest.mark.asyncio
async def test_put_offer_draft_only(client: AsyncClient, catalog_env: dict) -> None:
    r = await client.put(
        "/api/tenant/catalog/offers/2002",
        cookies=catalog_env["cookies"],
        json={
            "type": "container",
            "name": "Draft box",
            "container": "SeaChest",
            "items": [{"class": "Apple", "qty": 1}],
        },
    )
    assert r.status_code == 200
    assert r.json()["has_unpublished_changes"] is True
    assert "2002" in r.json()["offers"]

    offers_file = catalog_env["tenant_dir"] / "offers.yaml"
    text = offers_file.read_text(encoding="utf-8")
    assert "2002" not in text


@pytest.mark.asyncio
async def test_publish_writes_yaml(client: AsyncClient, catalog_env: dict, monkeypatch) -> None:
    await client.put(
        "/api/tenant/catalog/offers/2002",
        cookies=catalog_env["cookies"],
        json={
            "type": "container",
            "name": "New box",
            "container": "SeaChest",
            "items": [{"class": "Apple", "qty": 2}],
        },
    )

    async def fake_reload(**kwargs):
        return 1

    monkeypatch.setattr(
        "shop_claim_portal.routes.catalog.reload_bridge_catalog",
        fake_reload,
    )

    r = await client.post(
        "/api/tenant/catalog/publish",
        cookies=catalog_env["cookies"],
        json={"current_password": "subpass12345"},
    )
    assert r.status_code == 200
    assert r.json()["offer_count"] == 2

    text = (catalog_env["tenant_dir"] / "offers.yaml").read_text(encoding="utf-8")
    assert "2002" in text
    assert "New box" in text


@pytest.mark.asyncio
async def test_subscriber_cannot_access_other_tenant_catalog(
    client: AsyncClient, catalog_env: dict
) -> None:
    r = await client.get("/api/admin/tenants/other/catalog")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_discard_restores_published(client: AsyncClient, catalog_env: dict) -> None:
    await client.put(
        "/api/tenant/catalog/offers/2002",
        cookies=catalog_env["cookies"],
        json={
            "type": "container",
            "name": "Temp",
            "container": "SeaChest",
            "items": [{"class": "Apple", "qty": 1}],
        },
    )
    r = await client.post("/api/tenant/catalog/discard", cookies=catalog_env["cookies"])
    assert r.status_code == 200
    assert "2002" not in r.json()["offers"]
    assert r.json()["has_unpublished_changes"] is False


@pytest.mark.asyncio
async def test_put_legacy_wargm_server_ids(client: AsyncClient, catalog_env: dict) -> None:
    """Prod YAML uses wargm_server_ids + give_key — editor must accept them."""
    r = await client.put(
        "/api/tenant/catalog/offers/5002",
        cookies=catalog_env["cookies"],
        json={
            "type": "container",
            "name": "Legacy servers test",
            "container": "SeaChest",
            "items": [{"class": "Apple", "qty": 1}],
            "wargm_server_ids": [10001, 10002],
        },
    )
    assert r.status_code == 200
    offer = r.json()["offers"]["5002"]
    assert offer.get("shop_server_ids") == [10001, 10002]
    assert "wargm_server_ids" not in offer


@pytest.mark.asyncio
async def test_put_vehicle_with_give_key(client: AsyncClient, catalog_env: dict) -> None:
    r = await client.put(
        "/api/tenant/catalog/offers/5010",
        cookies=catalog_env["cookies"],
        json={
            "type": "vehicle",
            "name": "ADA 4x4",
            "class": "OffroadHatchback",
            "give_key": True,
            "wargm_server_ids": [10001],
            "spawn": {"distance_m": 6, "max_slope_deg": 15, "check_radius_m": 2.5},
        },
    )
    assert r.status_code == 200
    offer = r.json()["offers"]["5010"]
    assert offer.get("shop_server_ids") == [10001]
    assert "give_key" not in offer


@pytest.mark.asyncio
async def test_publish_requires_step_up_password(client: AsyncClient, catalog_env: dict) -> None:
    r = await client.post(
        "/api/tenant/catalog/publish",
        cookies=catalog_env["cookies"],
        json={},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_import_wargm_merges_draft(client: AsyncClient, catalog_env: dict, monkeypatch) -> None:
    async def fake_batch(self, offer_ids: list[str]):
        return [
            (
                offer_ids[0],
                {
                    "id": int(offer_ids[0]),
                    "active": True,
                    "servers": [10001],
                    "delivery": "api",
                },
                None,
            )
        ]

    monkeypatch.setattr(
        "shop_claim_portal.services.wargm_client.PortalWargmClient.fetch_offers_batch",
        fake_batch,
    )
    r = await client.post(
        "/api/tenant/catalog/import-wargm",
        cookies=catalog_env["cookies"],
        json={"offer_ids": ["9999"], "current_password": "subpass12345"},
    )
    assert r.status_code == 200
    assert "9999" in r.json()["imported"]

    cat = await client.get("/api/tenant/catalog", cookies=catalog_env["cookies"])
    assert "9999" in cat.json()["offers"]
