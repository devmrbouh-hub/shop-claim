"""YooKassa payment API integration."""

from __future__ import annotations

import base64
import logging
import uuid
from typing import Any

import httpx

from shop_claim_portal.config import Settings, get_settings
from shop_claim_portal.models import BillingPayment, Tenant

logger = logging.getLogger(__name__)


class YooKassaError(Exception):
    pass


def _auth_header(settings: Settings) -> str:
    raw = f"{settings.yookassa_shop_id}:{settings.yookassa_secret_key}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _api_base(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    return s.yookassa_api_base.rstrip("/")


def _payment_description(payment: BillingPayment, tenant: Tenant) -> str:
    target = payment.max_servers_snapshot + payment.max_servers_delta
    if payment.payment_kind == "renewal":
        if target <= 1:
            tier = "1 карта"
        elif target < 4:
            tier = "сеть до 3 карт"
        else:
            tier = "безлимит"
        label = f"Продление ShopClaim ({tier})"
    elif target >= 50 and payment.max_servers_delta > 1:
        label = "Переход на безлимит ShopClaim"
    else:
        label = "Добавление слота и продление ShopClaim"
    return f"{label}: {payment.months} мес., tenant {tenant.tenant_id}"


async def create_yookassa_payment(
    payment: BillingPayment,
    tenant: Tenant,
    subscriber_email: str,
    *,
    settings: Settings | None = None,
) -> str:
    s = settings or get_settings()
    amount_rub = payment.amount_kopecks // 100
    amount_str = f"{amount_rub:.2f}"
    return_url = f"{s.public_url.rstrip('/')}/app/billing?payment=success&payment_id={payment.id}"
    payload: dict[str, Any] = {
        "amount": {"value": amount_str, "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": _payment_description(payment, tenant)[:128],
        "metadata": {"payment_db_id": payment.id},
    }
    if subscriber_email:
        payload["receipt"] = {
            "customer": {"email": subscriber_email},
            "items": [
                {
                    "description": _payment_description(payment, tenant)[:128],
                    "quantity": "1.00",
                    "amount": {"value": amount_str, "currency": "RUB"},
                    "vat_code": 1,
                    "payment_mode": "full_payment",
                    "payment_subject": "service",
                }
            ],
        }
    headers = {
        "Authorization": _auth_header(s),
        "Idempotence-Key": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{_api_base(s)}/payments", json=payload, headers=headers)
    if resp.status_code >= 400:
        logger.warning("YooKassa create payment failed: %s %s", resp.status_code, resp.text[:500])
        raise YooKassaError(f"YooKassa error {resp.status_code}")
    data = resp.json()
    payment.yookassa_payment_id = data.get("id")
    confirmation = data.get("confirmation") or {}
    url = confirmation.get("confirmation_url")
    if not url:
        raise YooKassaError("No confirmation_url in YooKassa response")
    return url


async def fetch_yookassa_payment(payment_id: str, *, settings: Settings | None = None) -> dict[str, Any]:
    s = settings or get_settings()
    headers = {"Authorization": _auth_header(s)}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{_api_base(s)}/payments/{payment_id}", headers=headers)
    if resp.status_code >= 400:
        raise YooKassaError(f"YooKassa fetch error {resp.status_code}")
    return resp.json()
