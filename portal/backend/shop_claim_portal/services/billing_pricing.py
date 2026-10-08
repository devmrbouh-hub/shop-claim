"""Billing price calculation and platform settings."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shop_claim_portal.config import Settings, get_settings
from shop_claim_portal.models import (
    PLATFORM_SETTINGS_ID,
    BillingPayment,
    BillingPaymentStatus,
    PaymentKind,
    PlatformSettings,
    Tenant,
)
from shop_claim_portal.services.onboarding import maybe_auto_bridge_sync, mark_deploy_pending

ALLOWED_MONTHS = frozenset({1, 3, 12})
MAX_SERVERS = 50
PENDING_STALE_HOURS = 24
NETWORK3_RUB = 699
UNLIMITED_RUB = 1490
UNLIMITED_THRESHOLD = 4  # target max_servers >= 4 → unlimited tier (50 slots)


def add_calendar_months(start: date, months: int) -> date:
    y = start.year
    m = start.month + months
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    last_day = calendar.monthrange(y, m)[1]
    return date(y, m, min(start.day, last_day))


def extend_subscription_until(tenant: Tenant, months: int) -> None:
    base = max(date.today(), tenant.subscription_until)
    tenant.subscription_until = add_calendar_months(base, months)


def clamp_max_servers(value: int) -> int:
    return max(1, min(MAX_SERVERS, value))


def monthly_fee_rub(max_servers: int, price_per_server_rub: int) -> int:
    """Flat monthly fee for a given slot limit."""
    n = clamp_max_servers(max_servers)
    if n <= 1:
        return price_per_server_rub
    if n < UNLIMITED_THRESHOLD:
        return NETWORK3_RUB
    return UNLIMITED_RUB


def pricing_tier(max_servers: int) -> str:
    n = clamp_max_servers(max_servers)
    if n <= 1:
        return "single"
    if n < UNLIMITED_THRESHOLD:
        return "network3"
    return "unlimited"


def resolve_add_target(snapshot: int) -> int:
    """Target max_servers after add-slot payment."""
    nxt = clamp_max_servers(snapshot) + 1
    if nxt >= UNLIMITED_THRESHOLD:
        return MAX_SERVERS
    return nxt


def resolve_payment_target(payment_kind: str, snapshot: int) -> int:
    if payment_kind == PaymentKind.renewal.value:
        return clamp_max_servers(snapshot)
    if payment_kind in (PaymentKind.add_server.value, PaymentKind.renewal_and_add_server.value):
        return resolve_add_target(snapshot)
    raise ValueError(f"Unknown payment_kind: {payment_kind}")


def calc_amount_rub(payment_kind: str, max_servers: int, months: int, price_per_server_rub: int) -> int:
    target = resolve_payment_target(payment_kind, max_servers)
    return monthly_fee_rub(target, price_per_server_rub) * months


def calc_amount_kopecks(payment_kind: str, max_servers: int, months: int, price_per_server_rub: int) -> int:
    return calc_amount_rub(payment_kind, max_servers, months, price_per_server_rub) * 100


async def get_platform_settings(session: AsyncSession, settings: Settings | None = None) -> PlatformSettings:
    s = settings or get_settings()
    row = await session.get(PlatformSettings, PLATFORM_SETTINGS_ID)
    if row is None:
        row = PlatformSettings(
            id=PLATFORM_SETTINGS_ID,
            price_per_server_rub=s.billing_price_per_server_rub,
            billing_enabled=True,
        )
        session.add(row)
        await session.flush()
    return row


async def ensure_platform_settings_seed(session: AsyncSession) -> None:
    await get_platform_settings(session)


def yookassa_configured(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return bool(s.yookassa_shop_id.strip() and s.yookassa_secret_key.strip())


async def expire_stale_pending(session: AsyncSession, tenant_pk: int) -> None:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=PENDING_STALE_HOURS)
    result = await session.execute(
        select(BillingPayment).where(
            BillingPayment.tenant_pk == tenant_pk,
            BillingPayment.status == BillingPaymentStatus.pending.value,
            BillingPayment.created_at < cutoff,
        )
    )
    for payment in result.scalars().all():
        payment.status = BillingPaymentStatus.canceled.value


async def get_active_pending(session: AsyncSession, tenant_pk: int) -> BillingPayment | None:
    await expire_stale_pending(session, tenant_pk)
    result = await session.execute(
        select(BillingPayment).where(
            BillingPayment.tenant_pk == tenant_pk,
            BillingPayment.status == BillingPaymentStatus.pending.value,
        )
    )
    return result.scalar_one_or_none()


def apply_successful_payment(tenant: Tenant, payment: BillingPayment) -> None:
    if payment.status == BillingPaymentStatus.succeeded.value:
        return
    kind = payment.payment_kind
    months = payment.months
    if kind in (PaymentKind.renewal.value, PaymentKind.add_server.value, PaymentKind.renewal_and_add_server.value):
        extend_subscription_until(tenant, months)
    if kind in (PaymentKind.add_server.value, PaymentKind.renewal_and_add_server.value):
        tenant.max_servers = clamp_max_servers(
            payment.max_servers_snapshot + payment.max_servers_delta
        )
    if tenant.plan == "free_year":
        tenant.plan = "starter"
    payment.status = BillingPaymentStatus.succeeded.value
    payment.paid_at = datetime.now(timezone.utc).replace(tzinfo=None)


async def find_billing_payment_for_yookassa(
    session: AsyncSession,
    *,
    yookassa_payment_id: str,
    payment_db_id: str | None,
) -> BillingPayment | None:
    load_opts = [selectinload(BillingPayment.tenant).selectinload(Tenant.sync_state)]
    if payment_db_id:
        payment = await session.get(BillingPayment, str(payment_db_id), options=load_opts)
        if payment is not None:
            return payment
    result = await session.execute(
        select(BillingPayment)
        .where(BillingPayment.yookassa_payment_id == yookassa_payment_id)
        .options(*load_opts)
    )
    return result.scalar_one_or_none()


class BillingCompleteError(Exception):
    """Payment cannot be applied (amount, tenant, remote status)."""


def verify_payment_amount(remote: dict, payment: BillingPayment) -> bool:
    amount = remote.get("amount") or {}
    try:
        value = float(amount.get("value", 0))
    except (TypeError, ValueError):
        return False
    return int(round(value * 100)) == payment.amount_kopecks


async def complete_yookassa_payment(
    session: AsyncSession,
    payment: BillingPayment,
    remote: dict,
) -> str:
    """Apply a succeeded YooKassa payment. Returns ok or already_succeeded."""
    if payment.status == BillingPaymentStatus.succeeded.value:
        return "already_succeeded"
    remote_status = remote.get("status")
    if remote_status != "succeeded":
        raise BillingCompleteError(f"remote status is {remote_status!r}")
    if not verify_payment_amount(remote, payment):
        raise BillingCompleteError("amount mismatch")
    tenant = payment.tenant
    if not tenant:
        raise BillingCompleteError("tenant not found")
    apply_successful_payment(tenant, payment)
    mark_deploy_pending(tenant)
    await session.commit()
    await maybe_auto_bridge_sync(session)
    await session.commit()
    return "ok"
