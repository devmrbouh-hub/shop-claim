"""Billing tests."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from shop_claim_portal.models import BillingPayment, BillingPaymentStatus, PaymentKind, Tenant, User
from shop_claim_portal.services.billing_pricing import (
    NETWORK3_RUB,
    UNLIMITED_RUB,
    add_calendar_months,
    apply_successful_payment,
    calc_amount_rub,
    monthly_fee_rub,
    resolve_add_target,
)
from shop_claim_portal.services.password import hash_password


@pytest.mark.asyncio
async def test_public_pricing_default(client: AsyncClient) -> None:
    r = await client.get("/api/public/pricing")
    assert r.status_code == 200
    data = r.json()
    assert data["price_per_server_rub"] == 299
    assert data["network3_rub"] == NETWORK3_RUB
    assert data["unlimited_rub"] == UNLIMITED_RUB
    assert data["billing_enabled"] is True


@pytest.mark.asyncio
async def test_admin_update_pricing(client: AsyncClient, admin_cookies: dict) -> None:
    r = await client.patch(
        "/api/admin/billing/settings",
        json={"price_per_server_rub": 349},
        cookies=admin_cookies,
    )
    assert r.status_code == 200
    assert r.json()["price_per_server_rub"] == 349
    pub = await client.get("/api/public/pricing")
    assert pub.json()["price_per_server_rub"] == 349


@pytest.mark.asyncio
async def test_admin_price_above_network3_rejected(client: AsyncClient, admin_cookies: dict) -> None:
    r = await client.patch(
        "/api/admin/billing/settings",
        json={"price_per_server_rub": NETWORK3_RUB + 1},
        cookies=admin_cookies,
    )
    assert r.status_code == 400


def test_monthly_fee_bands() -> None:
    assert monthly_fee_rub(1, 299) == 299
    assert monthly_fee_rub(2, 299) == NETWORK3_RUB
    assert monthly_fee_rub(3, 299) == NETWORK3_RUB
    assert monthly_fee_rub(4, 299) == UNLIMITED_RUB
    assert monthly_fee_rub(50, 299) == UNLIMITED_RUB


def test_calc_amount_renewal() -> None:
    assert calc_amount_rub(PaymentKind.renewal.value, 1, 1, 299) == 299
    assert calc_amount_rub(PaymentKind.renewal.value, 3, 1, 299) == NETWORK3_RUB
    assert calc_amount_rub(PaymentKind.renewal.value, 3, 3, 299) == NETWORK3_RUB * 3
    assert calc_amount_rub(PaymentKind.renewal.value, 10, 1, 299) == UNLIMITED_RUB


def test_calc_amount_add_server() -> None:
    # 1 → 2: network3
    assert calc_amount_rub(PaymentKind.add_server.value, 1, 1, 299) == NETWORK3_RUB
    # 2 → 3: still network3
    assert calc_amount_rub(PaymentKind.add_server.value, 2, 1, 299) == NETWORK3_RUB
    # 3 → 50 unlimited
    assert calc_amount_rub(PaymentKind.add_server.value, 3, 1, 299) == UNLIMITED_RUB
    assert resolve_add_target(3) == 50


def test_apply_uses_snapshot_not_live_max() -> None:
    tenant = Tenant(
        tenant_id="snap_test",
        subscription_until=date.today(),
        max_servers=1,  # live changed after checkout
        plan="starter",
        enabled=True,
    )
    payment = BillingPayment(
        id="pay-snap",
        tenant_pk=0,
        payment_kind=PaymentKind.renewal_and_add_server.value,
        months=1,
        max_servers_snapshot=3,
        max_servers_delta=47,
        price_per_server_rub=299,
        amount_kopecks=UNLIMITED_RUB * 100,
        status=BillingPaymentStatus.pending.value,
    )
    apply_successful_payment(tenant, payment)
    assert tenant.max_servers == 50
    assert payment.status == BillingPaymentStatus.succeeded.value


def test_add_calendar_months_jan_to_feb() -> None:
    assert add_calendar_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


async def _setup_billing_subscriber(client: AsyncClient, admin_cookies: dict) -> dict:
    until = (date.today() - timedelta(days=5)).isoformat()
    r = await client.post(
        "/api/admin/tenants",
        json={
            "tenant_id": "billing_smoke",
            "subscription_until": until,
            "max_servers": 1,
            "subscriber_email": "billing@example.com",
        },
        cookies=admin_cookies,
    )
    assert r.status_code == 201
    from shop_claim_portal.db import get_session

    async for session in get_session():
        user = (await session.execute(select(User).where(User.email == "billing@example.com"))).scalar_one()
        user.password_hash = hash_password("subscriberpass12")
        user.is_active = True
        await session.commit()
        break
    login = await client.post(
        "/api/auth/login",
        json={"email": "billing@example.com", "password": "subscriberpass12"},
    )
    assert login.status_code == 200
    return dict(login.cookies)


@pytest.mark.asyncio
async def test_webhook_renewal_extends_until(
    client: AsyncClient, admin_cookies: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PORTAL_YOOKASSA_SHOP_ID", "test_shop")
    monkeypatch.setenv("PORTAL_YOOKASSA_SECRET_KEY", "test_secret")
    from shop_claim_portal.config import get_settings

    get_settings.cache_clear()

    sub_cookies = await _setup_billing_subscriber(client, admin_cookies)
    with patch(
        "shop_claim_portal.routes.billing.create_yookassa_payment",
        new_callable=AsyncMock,
        return_value="https://yookassa.test/pay",
    ):
        checkout = await client.post(
            "/api/tenant/billing/checkout",
            json={"payment_kind": "renewal", "months": 1},
            cookies=sub_cookies,
        )
    assert checkout.status_code == 200
    payment_id = checkout.json()["payment_id"]

    from shop_claim_portal.db import get_session

    amount_kopecks = 29900
    async for session in get_session():
        payment = await session.get(BillingPayment, payment_id)
        assert payment is not None
        amount_kopecks = payment.amount_kopecks
        payment.yookassa_payment_id = "yk-test-1"
        await session.commit()
        break

    remote = {
        "id": "yk-test-1",
        "status": "succeeded",
        "amount": {"value": f"{amount_kopecks / 100:.2f}", "currency": "RUB"},
        "metadata": {"payment_db_id": payment_id},
    }
    with patch(
        "shop_claim_portal.routes.billing.fetch_yookassa_payment",
        new_callable=AsyncMock,
        return_value=remote,
    ):
        wh = await client.post(
            "/api/billing/yookassa/webhook",
            json={"event": "payment.succeeded", "object": {"id": "yk-test-1"}},
        )
    assert wh.status_code == 200

    sub = await client.get("/api/tenant/subscription", cookies=sub_cookies)
    assert sub.json()["active"] is True


@pytest.mark.asyncio
async def test_admin_extend_30_days(client: AsyncClient, admin_cookies: dict) -> None:
    await _setup_billing_subscriber(client, admin_cookies)
    r = await client.post(
        "/api/admin/billing/tenants/billing_smoke/extend",
        json={"days": 30, "reason": "test"},
        cookies=admin_cookies,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def _checkout_payment(
    client: AsyncClient,
    sub_cookies: dict,
    *,
    payment_kind: str = "renewal",
    months: int = 1,
) -> tuple[str, int]:
    with patch(
        "shop_claim_portal.routes.billing.create_yookassa_payment",
        new_callable=AsyncMock,
        return_value="https://yookassa.test/pay",
    ):
        checkout = await client.post(
            "/api/tenant/billing/checkout",
            json={"payment_kind": payment_kind, "months": months},
            cookies=sub_cookies,
        )
    assert checkout.status_code == 200
    payment_id = checkout.json()["payment_id"]
    amount_kopecks = 0
    from shop_claim_portal.db import get_session

    async for session in get_session():
        payment = await session.get(BillingPayment, payment_id)
        assert payment is not None
        amount_kopecks = payment.amount_kopecks
        break
    return payment_id, amount_kopecks


def _remote_payment(yk_id: str, payment_db_id: str, amount_kopecks: int) -> dict:
    return {
        "id": yk_id,
        "status": "succeeded",
        "amount": {"value": f"{amount_kopecks / 100:.2f}", "currency": "RUB"},
        "metadata": {"payment_db_id": payment_db_id},
    }


@pytest.mark.asyncio
async def test_webhook_metadata_only_lookup(
    client: AsyncClient, admin_cookies: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PORTAL_YOOKASSA_SHOP_ID", "test_shop")
    monkeypatch.setenv("PORTAL_YOOKASSA_SECRET_KEY", "test_secret")
    from shop_claim_portal.config import get_settings

    get_settings.cache_clear()
    sub_cookies = await _setup_billing_subscriber(client, admin_cookies)
    payment_id, amount_kopecks = await _checkout_payment(client, sub_cookies)
    remote = _remote_payment("yk-meta-only", payment_id, amount_kopecks)
    with patch(
        "shop_claim_portal.routes.billing.fetch_yookassa_payment",
        new_callable=AsyncMock,
        return_value=remote,
    ):
        wh = await client.post(
            "/api/billing/yookassa/webhook",
            json={"event": "payment.succeeded", "object": {"id": "yk-meta-only"}},
        )
    assert wh.status_code == 200
    assert wh.json()["status"] == "ok"
    from shop_claim_portal.db import get_session

    async for session in get_session():
        payment = await session.get(BillingPayment, payment_id)
        assert payment is not None
        assert payment.status == BillingPaymentStatus.succeeded.value
        assert payment.yookassa_payment_id is None
        break


@pytest.mark.asyncio
async def test_webhook_idempotent(
    client: AsyncClient, admin_cookies: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PORTAL_YOOKASSA_SHOP_ID", "test_shop")
    monkeypatch.setenv("PORTAL_YOOKASSA_SECRET_KEY", "test_secret")
    from shop_claim_portal.config import get_settings

    get_settings.cache_clear()
    sub_cookies = await _setup_billing_subscriber(client, admin_cookies)
    payment_id, amount_kopecks = await _checkout_payment(client, sub_cookies)
    from shop_claim_portal.db import get_session

    async for session in get_session():
        payment = await session.get(BillingPayment, payment_id)
        assert payment is not None
        payment.yookassa_payment_id = "yk-idem"
        await session.commit()
        break
    remote = _remote_payment("yk-idem", payment_id, amount_kopecks)
    with patch(
        "shop_claim_portal.routes.billing.fetch_yookassa_payment",
        new_callable=AsyncMock,
        return_value=remote,
    ):
        first = await client.post(
            "/api/billing/yookassa/webhook",
            json={"event": "payment.succeeded", "object": {"id": "yk-idem"}},
        )
        second = await client.post(
            "/api/billing/yookassa/webhook",
            json={"event": "payment.succeeded", "object": {"id": "yk-idem"}},
        )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_webhook_pending_returns_503(
    client: AsyncClient, admin_cookies: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PORTAL_YOOKASSA_SHOP_ID", "test_shop")
    monkeypatch.setenv("PORTAL_YOOKASSA_SECRET_KEY", "test_secret")
    from shop_claim_portal.config import get_settings

    get_settings.cache_clear()
    sub_cookies = await _setup_billing_subscriber(client, admin_cookies)
    payment_id, _ = await _checkout_payment(client, sub_cookies)
    from shop_claim_portal.db import get_session

    async for session in get_session():
        payment = await session.get(BillingPayment, payment_id)
        assert payment is not None
        payment.yookassa_payment_id = "yk-pending"
        await session.commit()
        break
    with patch(
        "shop_claim_portal.routes.billing.fetch_yookassa_payment",
        new_callable=AsyncMock,
        return_value={"id": "yk-pending", "status": "pending", "metadata": {"payment_db_id": payment_id}},
    ):
        wh = await client.post(
            "/api/billing/yookassa/webhook",
            json={"event": "payment.succeeded", "object": {"id": "yk-pending"}},
        )
    assert wh.status_code == 503
    async for session in get_session():
        payment = await session.get(BillingPayment, payment_id)
        assert payment is not None
        assert payment.status == BillingPaymentStatus.pending.value
        break


@pytest.mark.asyncio
async def test_reconcile_endpoint(
    client: AsyncClient, admin_cookies: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PORTAL_YOOKASSA_SHOP_ID", "test_shop")
    monkeypatch.setenv("PORTAL_YOOKASSA_SECRET_KEY", "test_secret")
    from shop_claim_portal.config import get_settings

    get_settings.cache_clear()
    sub_cookies = await _setup_billing_subscriber(client, admin_cookies)
    payment_id, amount_kopecks = await _checkout_payment(client, sub_cookies)
    from shop_claim_portal.db import get_session

    async for session in get_session():
        payment = await session.get(BillingPayment, payment_id)
        assert payment is not None
        payment.yookassa_payment_id = "yk-reconcile"
        await session.commit()
        break
    remote = _remote_payment("yk-reconcile", payment_id, amount_kopecks)
    with patch(
        "shop_claim_portal.routes.billing.fetch_yookassa_payment",
        new_callable=AsyncMock,
        return_value=remote,
    ):
        r = await client.post(
            "/api/tenant/billing/reconcile",
            json={"payment_id": payment_id},
            cookies=sub_cookies,
        )
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "applied": True}
    sub = await client.get("/api/tenant/subscription", cookies=sub_cookies)
    assert sub.json()["active"] is True


@pytest.mark.asyncio
async def test_webhook_add_server_increments_max_servers(
    client: AsyncClient, admin_cookies: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PORTAL_YOOKASSA_SHOP_ID", "test_shop")
    monkeypatch.setenv("PORTAL_YOOKASSA_SECRET_KEY", "test_secret")
    from shop_claim_portal.config import get_settings

    get_settings.cache_clear()
    sub_cookies = await _setup_billing_subscriber(client, admin_cookies)
    before = await client.get("/api/tenant/subscription", cookies=sub_cookies)
    max_before = before.json()["max_servers"]
    until_before = date.fromisoformat(before.json()["subscription_until"])
    payment_id, amount_kopecks = await _checkout_payment(
        client, sub_cookies, payment_kind="add_server", months=1
    )
    assert amount_kopecks == NETWORK3_RUB * 100  # 1 → 2
    from shop_claim_portal.db import get_session

    async for session in get_session():
        payment = await session.get(BillingPayment, payment_id)
        assert payment is not None
        assert payment.max_servers_delta == 1
        payment.yookassa_payment_id = "yk-add-server"
        await session.commit()
        break
    remote = _remote_payment("yk-add-server", payment_id, amount_kopecks)
    with patch(
        "shop_claim_portal.routes.billing.fetch_yookassa_payment",
        new_callable=AsyncMock,
        return_value=remote,
    ):
        wh = await client.post(
            "/api/billing/yookassa/webhook",
            json={"event": "payment.succeeded", "object": {"id": "yk-add-server"}},
        )
    assert wh.status_code == 200
    after = await client.get("/api/tenant/subscription", cookies=sub_cookies)
    assert after.json()["max_servers"] == max_before + 1
    until_after = date.fromisoformat(after.json()["subscription_until"])
    assert until_after > until_before


@pytest.mark.asyncio
async def test_webhook_add_from_3_goes_unlimited(
    client: AsyncClient, admin_cookies: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PORTAL_YOOKASSA_SHOP_ID", "test_shop")
    monkeypatch.setenv("PORTAL_YOOKASSA_SECRET_KEY", "test_secret")
    from shop_claim_portal.config import get_settings

    get_settings.cache_clear()
    sub_cookies = await _setup_billing_subscriber(client, admin_cookies)
    from shop_claim_portal.db import get_session

    async for session in get_session():
        tenant = (await session.execute(select(Tenant).where(Tenant.tenant_id == "billing_smoke"))).scalar_one()
        tenant.max_servers = 3
        await session.commit()
        break
    payment_id, amount_kopecks = await _checkout_payment(
        client, sub_cookies, payment_kind="renewal_and_add_server", months=1
    )
    assert amount_kopecks == UNLIMITED_RUB * 100
    async for session in get_session():
        payment = await session.get(BillingPayment, payment_id)
        assert payment is not None
        assert payment.max_servers_snapshot == 3
        assert payment.max_servers_delta == 47
        payment.yookassa_payment_id = "yk-unlimited"
        await session.commit()
        break
    remote = _remote_payment("yk-unlimited", payment_id, amount_kopecks)
    with patch(
        "shop_claim_portal.routes.billing.fetch_yookassa_payment",
        new_callable=AsyncMock,
        return_value=remote,
    ):
        wh = await client.post(
            "/api/billing/yookassa/webhook",
            json={"event": "payment.succeeded", "object": {"id": "yk-unlimited"}},
        )
    assert wh.status_code == 200
    after = await client.get("/api/tenant/subscription", cookies=sub_cookies)
    assert after.json()["max_servers"] == 50
    assert after.json()["tier"] == "unlimited"
    assert after.json()["monthly_fee_rub"] == UNLIMITED_RUB


@pytest.mark.asyncio
async def test_reconcile_already_succeeded(
    client: AsyncClient, admin_cookies: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PORTAL_YOOKASSA_SHOP_ID", "test_shop")
    monkeypatch.setenv("PORTAL_YOOKASSA_SECRET_KEY", "test_secret")
    from shop_claim_portal.config import get_settings

    get_settings.cache_clear()
    sub_cookies = await _setup_billing_subscriber(client, admin_cookies)
    payment_id, amount_kopecks = await _checkout_payment(client, sub_cookies)
    from shop_claim_portal.db import get_session

    async for session in get_session():
        payment = await session.get(BillingPayment, payment_id)
        assert payment is not None
        payment.yookassa_payment_id = "yk-reconcile-idem"
        await session.commit()
        break
    remote = _remote_payment("yk-reconcile-idem", payment_id, amount_kopecks)
    with patch(
        "shop_claim_portal.routes.billing.fetch_yookassa_payment",
        new_callable=AsyncMock,
        return_value=remote,
    ):
        wh = await client.post(
            "/api/billing/yookassa/webhook",
            json={"event": "payment.succeeded", "object": {"id": "yk-reconcile-idem"}},
        )
    assert wh.status_code == 200
    with patch(
        "shop_claim_portal.routes.billing.fetch_yookassa_payment",
        new_callable=AsyncMock,
        return_value=remote,
    ):
        again = await client.post(
            "/api/tenant/billing/reconcile",
            json={"payment_id": payment_id},
            cookies=sub_cookies,
        )
    assert again.status_code == 200
    assert again.json() == {"status": "ok", "applied": False}


async def _setup_reduce_limit_tenant(client: AsyncClient, admin_cookies: dict) -> dict:
    until = (date.today() + timedelta(days=30)).isoformat()
    r = await client.post(
        "/api/admin/tenants",
        json={
            "tenant_id": "billing_reduce",
            "subscription_until": until,
            "max_servers": 5,
            "subscriber_email": "reduce@example.com",
        },
        cookies=admin_cookies,
    )
    assert r.status_code == 201
    from shop_claim_portal.db import get_session

    async for session in get_session():
        user = (await session.execute(select(User).where(User.email == "reduce@example.com"))).scalar_one()
        user.password_hash = hash_password("subscriberpass12")
        user.is_active = True
        await session.commit()
        break
    login = await client.post(
        "/api/auth/login",
        json={"email": "reduce@example.com", "password": "subscriberpass12"},
    )
    assert login.status_code == 200
    sub_cookies = dict(login.cookies)
    for i in range(3):
        sr = await client.post(
            "/api/tenant/servers",
            json={"server_id": f"reduce_srv_{i}", "shop_server_id": 100 + i},
            cookies=sub_cookies,
        )
        assert sr.status_code == 201
    return sub_cookies


@pytest.mark.asyncio
async def test_reduce_limit_ok(client: AsyncClient, admin_cookies: dict) -> None:
    sub_cookies = await _setup_reduce_limit_tenant(client, admin_cookies)
    r = await client.post(
        "/api/tenant/billing/reduce-limit",
        json={"max_servers": 4},
        cookies=sub_cookies,
    )
    assert r.status_code == 200
    assert r.json()["max_servers"] == 4
    sub = await client.get("/api/tenant/subscription", cookies=sub_cookies)
    assert sub.json()["max_servers"] == 4


@pytest.mark.asyncio
async def test_reduce_limit_below_server_count(client: AsyncClient, admin_cookies: dict) -> None:
    sub_cookies = await _setup_reduce_limit_tenant(client, admin_cookies)
    r = await client.post(
        "/api/tenant/billing/reduce-limit",
        json={"max_servers": 2},
        cookies=sub_cookies,
    )
    assert r.status_code == 400
    assert "серверов" in r.json()["detail"]


@pytest.mark.asyncio
async def test_reduce_limit_increase_rejected(client: AsyncClient, admin_cookies: dict) -> None:
    sub_cookies = await _setup_reduce_limit_tenant(client, admin_cookies)
    r = await client.post(
        "/api/tenant/billing/reduce-limit",
        json={"max_servers": 6},
        cookies=sub_cookies,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_reduce_limit_unchanged(client: AsyncClient, admin_cookies: dict) -> None:
    sub_cookies = await _setup_reduce_limit_tenant(client, admin_cookies)
    r = await client.post(
        "/api/tenant/billing/reduce-limit",
        json={"max_servers": 5},
        cookies=sub_cookies,
    )
    assert r.status_code == 400
