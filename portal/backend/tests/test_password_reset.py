"""Password reset and email change flow tests."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from shop_claim_portal.db import get_session
from shop_claim_portal.models import User
from shop_claim_portal.services.password import hash_password


@pytest.fixture
def smtp_ok(monkeypatch):
    captures: dict[str, str] = {}

    def fake_confirm(*, to_email: str, code: str) -> bool:
        captures["confirm_email"] = to_email
        captures["confirm_code"] = code
        return True

    def fake_reset(*, to_email: str, code: str) -> bool:
        captures["reset_email"] = to_email
        captures["reset_code"] = code
        return True

    def fake_notice(*args, **kwargs) -> bool:
        return True

    monkeypatch.setattr(
        "shop_claim_portal.routes.auth.send_email_change_confirm",
        fake_confirm,
    )
    monkeypatch.setattr(
        "shop_claim_portal.routes.auth.send_email_change_requested_notice",
        fake_notice,
    )
    monkeypatch.setattr(
        "shop_claim_portal.routes.auth.send_email_changed_notice",
        fake_notice,
    )
    monkeypatch.setattr(
        "shop_claim_portal.routes.auth.send_password_reset_email",
        fake_reset,
    )
    return captures


@pytest.mark.asyncio
async def test_change_email_pending_then_confirm(client: AsyncClient, admin_cookies: dict, smtp_ok):
    r = await client.post(
        "/api/auth/change-email",
        cookies=admin_cookies,
        json={"current_password": "adminpass123", "new_email": "admin2@example.com"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "admin@example.com"
    assert body["pending_email"] == "admin2@example.com"

    me = await client.get("/api/auth/me", cookies=admin_cookies)
    assert me.json()["pending_email"] == "admin2@example.com"

    code = smtp_ok["confirm_code"]
    confirm = await client.post("/api/auth/confirm-email-change", json={"code": code})
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
async def test_cancel_email_change(client: AsyncClient, admin_cookies: dict, smtp_ok):
    await client.post(
        "/api/auth/change-email",
        cookies=admin_cookies,
        json={"current_password": "adminpass123", "new_email": "pending@example.com"},
    )
    cancel = await client.post("/api/auth/cancel-email-change", cookies=admin_cookies)
    assert cancel.status_code == 200
    me = await client.get("/api/auth/me", cookies=admin_cookies)
    assert me.json()["pending_email"] is None


@pytest.mark.asyncio
async def test_forgot_password_generic(client: AsyncClient):
    r = await client.post(
        "/api/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_forgot_and_reset_password(client: AsyncClient, smtp_ok):
    forgot = await client.post(
        "/api/auth/forgot-password",
        json={"email": "admin@example.com"},
    )
    assert forgot.status_code == 200

    code = smtp_ok["reset_code"]
    reset = await client.post(
        "/api/auth/reset-password",
        json={"code": code, "password": "resetadminpass"},
    )
    assert reset.status_code == 200

    old = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "adminpass123"},
    )
    assert old.status_code == 401

    new = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "resetadminpass"},
    )
    assert new.status_code == 200


@pytest.mark.asyncio
async def test_set_password_rejects_reset_token(client: AsyncClient, smtp_ok):
    await client.post("/api/auth/forgot-password", json={"email": "admin@example.com"})
    code = smtp_ok["reset_code"]
    r = await client.post(
        "/api/auth/set-password",
        json={"code": code, "password": "hackerpass123"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_pending_email_blocks_other_user(client: AsyncClient, admin_cookies: dict, smtp_ok):
    await client.post(
        "/api/auth/change-email",
        cookies=admin_cookies,
        json={"current_password": "adminpass123", "new_email": "held@example.com"},
    )
    await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": "other_tenant",
            "subscription_until": str(date.today().replace(year=date.today().year + 1)),
            "wargm_shop_id": "1",
            "wargm_api_key": "key",
            "subscriber_email": "sub2@example.com",
        },
    )
    async for session in get_session():
        res = await session.execute(select(User).where(User.email == "sub2@example.com"))
        user = res.scalar_one()
        user.password_hash = hash_password("subscriberpass12")
        user.is_active = True
        await session.commit()
        break

    sub_login = await client.post(
        "/api/auth/login",
        json={"email": "sub2@example.com", "password": "subscriberpass12"},
    )
    sub_cookies = dict(sub_login.cookies)
    taken = await client.post(
        "/api/auth/change-email",
        cookies=sub_cookies,
        json={"current_password": "subscriberpass12", "new_email": "held@example.com"},
    )
    assert taken.status_code == 409
