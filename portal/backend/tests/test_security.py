"""Security and auth tests."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/api/public/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_cors_allows_status_origin(client: AsyncClient):
    from shop_claim_portal.config import get_settings

    origin = "http://127.0.0.1:5173"
    assert origin in get_settings().cors_origin_list
    r = await client.options(
        "/api/public/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == origin


@pytest.mark.asyncio
async def test_lead_honeypot(client: AsyncClient):
    r = await client.post(
        "/api/public/leads",
        json={
            "project_name": "Test",
            "email": "a@b.com",
            "instance_count": 1,
            "website": "http://spam",
        },
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_lead_rate_limit_uses_forwarded_ip(client: AsyncClient, admin_cookies: dict):
    """Each X-Forwarded-For IP gets its own rate-limit bucket (Caddy prod)."""
    for i in range(6):
        r = await client.post(
            "/api/public/leads",
            json={
                "project_name": "Test",
                "email": f"lead-xff-{i}@example.com",
                "instance_count": 1,
            },
            headers={"X-Forwarded-For": f"203.0.113.{i + 1}"},
        )
        assert r.status_code == 200
    leads = await client.get("/api/admin/leads", cookies=admin_cookies)
    assert leads.status_code == 200
    emails = {row["email"] for row in leads.json()}
    assert "lead-xff-5@example.com" in emails


@pytest.mark.asyncio
async def test_lead_email_crlf_rejected(client: AsyncClient):
    r = await client.post(
        "/api/public/leads",
        json={
            "project_name": "Test",
            "email": "a@b.com\r\nBcc: evil@x.com",
            "instance_count": 1,
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_password_max_length(client: AsyncClient):
    r = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "x" * 129},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_subscriber_cannot_access_admin(client: AsyncClient, admin_cookies: dict):
    # create tenant + subscriber via admin
    r = await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": "acme",
            "subscription_until": str(date.today().replace(year=date.today().year + 1)),
            "wargm_shop_id": "1",
            "wargm_api_key": "key",
            "subscriber_email": "sub@example.com",
        },
    )
    assert r.status_code == 201

    from sqlalchemy import select
    from shop_claim_portal.db import get_session
    from shop_claim_portal.models import User
    from shop_claim_portal.services.password import hash_password

    async for session in get_session():
        res = await session.execute(select(User).where(User.email == "sub@example.com"))
        user = res.scalar_one()
        user.password_hash = hash_password("subscriberpass12")
        user.is_active = True
        await session.commit()
        break

    sub_login = await client.post(
        "/api/auth/login",
        json={"email": "sub@example.com", "password": "subscriberpass12"},
    )
    assert sub_login.status_code == 200
    sub_cookies = dict(sub_login.cookies)
    forbidden = await client.get("/api/admin/leads", cookies=sub_cookies)
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_bridge_sync_dry_run(client: AsyncClient, admin_cookies: dict):
    await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": "sync_test",
            "subscription_until": str(date.today().replace(year=date.today().year + 1)),
            "wargm_shop_id": "1",
            "wargm_api_key": "testkey",
        },
    )
    r = await client.post("/api/admin/bridge/sync?dry_run=true", cookies=admin_cookies)
    assert r.status_code == 200
    assert r.json()["dry_run"] is True
