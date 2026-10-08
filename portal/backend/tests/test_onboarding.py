"""Onboarding API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_tenant_default_free_year(client: AsyncClient, admin_cookies: dict) -> None:
    from datetime import date, timedelta

    r = await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": "free_year_default",
            "subscriber_email": "freeyear@example.com",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["plan"] == "free_year"
    expected = date.today() + timedelta(days=365)
    assert data["subscription_until"] == expected.isoformat()


@pytest.mark.asyncio
async def test_create_tenant_without_wargm(client: AsyncClient, admin_cookies: dict) -> None:
    r = await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": "onboard_test",
            "subscription_until": "2027-12-31",
            "subscriber_email": "onboard@example.com",
            "max_servers": 2,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["wargm_configured"] is False
    assert data["max_servers"] == 2


@pytest.mark.asyncio
async def test_subscriber_wargm_and_servers(client: AsyncClient, admin_cookies: dict) -> None:
    await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": "sub_setup",
            "subscription_until": "2027-12-31",
            "subscriber_email": "subsetup@example.com",
            "max_servers": 1,
        },
    )
    from shop_claim_portal.db import get_session
    from shop_claim_portal.models import User
    from shop_claim_portal.services.password import hash_password
    from sqlalchemy import select

    async for session in get_session():
        result = await session.execute(select(User).where(User.email == "subsetup@example.com"))
        user = result.scalar_one()
        user.password_hash = hash_password("subscriberpass12")
        user.is_active = True
        await session.commit()
        break

    login = await client.post(
        "/api/auth/login",
        json={"email": "subsetup@example.com", "password": "subscriberpass12"},
    )
    assert login.status_code == 200
    cookies = dict(login.cookies)

    sub = await client.get("/api/tenant/subscription", cookies=cookies)
    assert sub.json()["wargm_configured"] is False
    assert sub.json()["max_servers"] == 1

    w = await client.put(
        "/api/tenant/wargm",
        cookies=cookies,
        json={
            "wargm_shop_id": "99",
            "wargm_api_key": "secret-key",
            "current_password": "subscriberpass12",
        },
    )
    assert w.status_code == 200

    s = await client.post(
        "/api/tenant/servers",
        cookies=cookies,
        json={"server_id": "sub_setup_s1", "shop_server_id": 12345},
    )
    assert s.status_code == 201

    over = await client.post(
        "/api/tenant/servers",
        cookies=cookies,
        json={"server_id": "sub_setup_s2", "shop_server_id": 12346},
    )
    assert over.status_code == 400

    invite_r = await client.get("/api/tenant/subscription", cookies=cookies)
    assert invite_r.json()["wargm_configured"] is True
    assert invite_r.json()["server_count"] == 1


@pytest.mark.asyncio
async def test_admin_tenant_detail_and_invite_code(client: AsyncClient, admin_cookies: dict) -> None:
    create = await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": "detail_test",
            "subscription_until": "2027-06-01",
            "subscriber_email": "detail@example.com",
        },
    )
    assert create.status_code == 201

    detail = await client.get("/api/admin/tenants/detail_test", cookies=admin_cookies)
    assert detail.status_code == 200
    body = detail.json()
    assert len(body["users"]) == 1

    user_id = body["users"][0]["id"]
    inv = await client.post(f"/api/admin/users/{user_id}/invite", cookies=admin_cookies, json={})
    assert inv.status_code == 200
    assert "invite_code" in inv.json()
    assert len(inv.json()["invite_code"]) > 20


@pytest.mark.asyncio
async def test_server_id_rejects_invalid_chars(client: AsyncClient, admin_cookies: dict) -> None:
    await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": "srv_val_test",
            "subscription_until": "2027-12-31",
            "max_servers": 1,
        },
    )
    r = await client.post(
        "/api/admin/tenants/srv_val_test/servers",
        cookies=admin_cookies,
        json={"server_id": "<script>", "shop_server_id": 1},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_max_servers_increase_and_decrease(client: AsyncClient, admin_cookies: dict) -> None:
    await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": "quota_patch",
            "subscription_until": "2027-12-31",
            "subscriber_email": "quota@example.com",
            "max_servers": 1,
        },
    )
    from shop_claim_portal.db import get_session
    from shop_claim_portal.models import User
    from shop_claim_portal.services.password import hash_password
    from sqlalchemy import select

    async for session in get_session():
        result = await session.execute(select(User).where(User.email == "quota@example.com"))
        user = result.scalar_one()
        user.password_hash = hash_password("subscriberpass12")
        user.is_active = True
        await session.commit()
        break

    login = await client.post(
        "/api/auth/login",
        json={"email": "quota@example.com", "password": "subscriberpass12"},
    )
    assert login.status_code == 200
    sub_cookies = dict(login.cookies)

    s1 = await client.post(
        "/api/tenant/servers",
        cookies=sub_cookies,
        json={"server_id": "quota_s1", "shop_server_id": 10001},
    )
    assert s1.status_code == 201

    up = await client.patch(
        "/api/admin/tenants/quota_patch",
        cookies=admin_cookies,
        json={"max_servers": 3},
    )
    assert up.status_code == 200
    assert up.json()["max_servers"] == 3

    s2 = await client.post(
        "/api/tenant/servers",
        cookies=sub_cookies,
        json={"server_id": "quota_s2", "shop_server_id": 10002},
    )
    assert s2.status_code == 201

    await client.post(
        "/api/tenant/servers",
        cookies=sub_cookies,
        json={"server_id": "quota_s3", "shop_server_id": 10003},
    )

    down = await client.patch(
        "/api/admin/tenants/quota_patch",
        cookies=admin_cookies,
        json={"max_servers": 1},
    )
    assert down.status_code == 400
    assert "Лимит не может быть меньше" in down.json()["detail"]


@pytest.mark.asyncio
async def test_patch_subscription_until_only(client: AsyncClient, admin_cookies: dict) -> None:
    create = await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": "sub_date_patch",
            "subscription_until": "2027-06-01",
            "max_servers": 2,
        },
    )
    assert create.status_code == 201
    assert create.json()["max_servers"] == 2

    patch = await client.patch(
        "/api/admin/tenants/sub_date_patch",
        cookies=admin_cookies,
        json={"subscription_until": "2028-01-15"},
    )
    assert patch.status_code == 200
    assert patch.json()["subscription_until"] == "2028-01-15"
    assert patch.json()["max_servers"] == 2
