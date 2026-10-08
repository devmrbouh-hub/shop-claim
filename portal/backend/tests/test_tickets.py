"""Tenant ticket API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from shop_claim_portal.db import get_session
from shop_claim_portal.models import Ticket, User
from shop_claim_portal.services.password import hash_password


async def _subscriber_cookies(client: AsyncClient, admin_cookies: dict, tenant_id: str, email: str) -> dict:
    await client.post(
        "/api/admin/tenants",
        cookies=admin_cookies,
        json={
            "tenant_id": tenant_id,
            "subscription_until": "2027-12-31",
            "subscriber_email": email,
            "max_servers": 1,
        },
    )
    async for session in get_session():
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.password_hash = hash_password("subscriberpass12")
        user.is_active = True
        await session.commit()
        break
    login = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "subscriberpass12"},
    )
    assert login.status_code == 200
    return dict(login.cookies)


async def _create_ticket(client: AsyncClient, cookies: dict) -> int:
    r = await client.post(
        "/api/tenant/tickets",
        cookies=cookies,
        json={"subject": "Test issue", "body": "Something broke on server"},
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.asyncio
async def test_subscriber_reply_ticket(client: AsyncClient, admin_cookies: dict) -> None:
    cookies = await _subscriber_cookies(client, admin_cookies, "ticket_a", "ticketa@example.com")
    ticket_id = await _create_ticket(client, cookies)

    r = await client.post(
        f"/api/tenant/tickets/{ticket_id}/messages",
        cookies=cookies,
        json={"body": "Additional details here"},
    )
    assert r.status_code == 201
    assert r.json()["is_provider"] is False

    detail = await client.get(f"/api/tenant/tickets/{ticket_id}", cookies=cookies)
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 2
    assert detail.json()["status"] == "waiting_provider"


@pytest.mark.asyncio
async def test_subscriber_reply_ticket_idor(client: AsyncClient, admin_cookies: dict) -> None:
    cookies_a = await _subscriber_cookies(client, admin_cookies, "ticket_b", "ticketb@example.com")
    cookies_b = await _subscriber_cookies(client, admin_cookies, "ticket_c", "ticketc@example.com")
    ticket_id = await _create_ticket(client, cookies_a)

    r = await client.post(
        f"/api/tenant/tickets/{ticket_id}/messages",
        cookies=cookies_b,
        json={"body": "Trying to hijack"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_subscriber_reply_rejects_secrets(client: AsyncClient, admin_cookies: dict) -> None:
    cookies = await _subscriber_cookies(client, admin_cookies, "ticket_d", "ticketd@example.com")
    ticket_id = await _create_ticket(client, cookies)

    r = await client.post(
        f"/api/tenant/tickets/{ticket_id}/messages",
        cookies=cookies,
        json={"body": "my api_token=abc123secret"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_subscriber_reply_resolved_ticket(client: AsyncClient, admin_cookies: dict) -> None:
    cookies = await _subscriber_cookies(client, admin_cookies, "ticket_e", "tickete@example.com")
    ticket_id = await _create_ticket(client, cookies)

    async for session in get_session():
        ticket = await session.get(Ticket, ticket_id)
        assert ticket is not None
        ticket.status = "resolved"
        await session.commit()
        break

    r = await client.post(
        f"/api/tenant/tickets/{ticket_id}/messages",
        cookies=cookies,
        json={"body": "Reopen please"},
    )
    assert r.status_code == 409
