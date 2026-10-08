"""Account settings (change password / email) tests."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from shop_claim_portal.db import get_session
from shop_claim_portal.models import Tenant, User
from shop_claim_portal.services.password import hash_password


async def _subscriber_cookies(client: AsyncClient, admin_cookies: dict) -> dict:
    r = await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": "acct_test",
            "subscription_until": str(date.today().replace(year=date.today().year + 1)),
            "wargm_shop_id": "1",
            "wargm_api_key": "key",
            "subscriber_email": "sub@example.com",
        },
    )
    assert r.status_code == 201

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
    return dict(sub_login.cookies)


@pytest.mark.asyncio
async def test_change_password_unauthenticated(client: AsyncClient):
    r = await client.post(
        "/api/auth/change-password",
        json={"current_password": "x", "new_password": "newpassword12"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient, admin_cookies: dict):
    r = await client.post(
        "/api/auth/change-password",
        cookies=admin_cookies,
        json={"current_password": "wrongpass12", "new_password": "newpassword12"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Неверный текущий пароль"


@pytest.mark.asyncio
async def test_change_password_same_as_current(client: AsyncClient, admin_cookies: dict):
    r = await client.post(
        "/api/auth/change-password",
        cookies=admin_cookies,
        json={"current_password": "adminpass123", "new_password": "adminpass123"},
    )
    assert r.status_code == 400
    assert "отличаться" in r.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_success_keeps_session(client: AsyncClient, admin_cookies: dict):
    from sqlalchemy import select

    from shop_claim_portal.db import get_session
    from shop_claim_portal.models import AdminAuditLog

    r = await client.post(
        "/api/auth/change-password",
        cookies=admin_cookies,
        json={"current_password": "adminpass123", "new_password": "newadminpass1"},
    )
    assert r.status_code == 200
    cookies = dict(r.cookies)

    async for session in get_session():
        result = await session.execute(
            select(AdminAuditLog).where(AdminAuditLog.action == "password_changed")
        )
        assert result.scalars().first() is not None
        break

    me = await client.get("/api/auth/me", cookies=cookies)
    assert me.status_code == 200

    old_login = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "adminpass123"},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "newadminpass1"},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_subscriber_change_password_writes_audit_log(client: AsyncClient, admin_cookies: dict):
    from sqlalchemy import select

    from shop_claim_portal.db import get_session
    from shop_claim_portal.models import AdminAuditLog

    sub_cookies = await _subscriber_cookies(client, admin_cookies)
    r = await client.post(
        "/api/auth/change-password",
        cookies=sub_cookies,
        json={"current_password": "subscriberpass12", "new_password": "newsubpass123"},
    )
    assert r.status_code == 200

    async for session in get_session():
        result = await session.execute(
            select(AdminAuditLog)
            .where(AdminAuditLog.action == "password_changed")
            .order_by(AdminAuditLog.id.desc())
        )
        entry = result.scalars().first()
        assert entry is not None
        break
    r = await client.post(
        "/api/auth/change-email",
        cookies=admin_cookies,
        json={"current_password": "adminpass123", "new_email": "admin@example.com"},
    )
    assert r.status_code == 400
    assert "совпадает" in r.json()["detail"]


@pytest.mark.asyncio
async def test_change_email_taken(client: AsyncClient, admin_cookies: dict):
    await _subscriber_cookies(client, admin_cookies)
    r = await client.post(
        "/api/auth/change-email",
        cookies=admin_cookies,
        json={"current_password": "adminpass123", "new_email": "sub@example.com"},
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "Email уже используется"


@pytest.mark.asyncio
async def test_change_email_success(client: AsyncClient, admin_cookies: dict, monkeypatch):
  captures: dict[str, str] = {}

  def fake_confirm(*, to_email: str, code: str) -> bool:
    captures["code"] = code
    return True

  monkeypatch.setattr(
    "shop_claim_portal.routes.auth.send_email_change_confirm",
    fake_confirm,
  )
  monkeypatch.setattr(
    "shop_claim_portal.routes.auth.send_email_change_requested_notice",
    lambda **_: True,
  )
  monkeypatch.setattr(
    "shop_claim_portal.routes.auth.send_email_changed_notice",
    lambda **_: True,
  )

  r = await client.post(
    "/api/auth/change-email",
    cookies=admin_cookies,
    json={"current_password": "adminpass123", "new_email": "admin2@example.com"},
  )
  assert r.status_code == 200
  assert r.json()["pending_email"] == "admin2@example.com"

  confirm = await client.post(
    "/api/auth/confirm-email-change",
    json={"code": captures["code"]},
  )
  assert confirm.status_code == 200
  assert confirm.json()["email"] == "admin2@example.com"

  old_login = await client.post(
    "/api/auth/login",
    json={"email": "admin@example.com", "password": "adminpass123"},
  )
  assert old_login.status_code == 401

  new_login = await client.post(
    "/api/auth/login",
    json={"email": "admin2@example.com", "password": "adminpass123"},
  )
  assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_subscriber_still_cannot_access_admin(client: AsyncClient, admin_cookies: dict):
    sub_cookies = await _subscriber_cookies(client, admin_cookies)
    r = await client.post(
        "/api/auth/change-password",
        cookies=sub_cookies,
        json={"current_password": "subscriberpass12", "new_password": "subscriberpass99"},
    )
    assert r.status_code == 200
    cookies = dict(r.cookies)
    forbidden = await client.get("/api/admin/leads", cookies=cookies)
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_change_password_when_tenant_disabled(client: AsyncClient, admin_cookies: dict):
    sub_cookies = await _subscriber_cookies(client, admin_cookies)

    async for session in get_session():
        res = await session.execute(select(Tenant).where(Tenant.tenant_id == "acct_test"))
        tenant = res.scalar_one()
        tenant.enabled = False
        await session.commit()
        break

    sub = await client.get("/api/tenant/subscription", cookies=sub_cookies)
    assert sub.status_code == 403

    pw = await client.post(
        "/api/auth/change-password",
        cookies=sub_cookies,
        json={"current_password": "subscriberpass12", "new_password": "subscriberpass99"},
    )
    assert pw.status_code == 200


@pytest.mark.asyncio
async def test_logout_clears_session(client: AsyncClient):
    login = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "adminpass123"},
    )
    assert login.status_code == 200

    me_before = await client.get("/api/auth/me")
    assert me_before.status_code == 200
    assert me_before.json() is not None

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert logout.json()["status"] == "ok"

    me_after = await client.get("/api/auth/me")
    assert me_after.status_code == 200
    assert me_after.json() is None
