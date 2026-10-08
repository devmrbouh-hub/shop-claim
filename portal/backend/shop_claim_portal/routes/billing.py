"""Billing routes: checkout, webhook, admin settings."""

from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shop_claim_portal.auth.deps import SessionUser, require_provider, require_subscriber
from shop_claim_portal.config import get_settings
from shop_claim_portal.db import get_session
from shop_claim_portal.models import BillingPayment, BillingPaymentStatus, PaymentKind, Tenant
from shop_claim_portal.rate_limit import rate_limiter
from shop_claim_portal.schemas import (
    BillingCheckoutIn,
    BillingCheckoutOut,
    BillingExtendIn,
    BillingPaymentOut,
    BillingReconcileIn,
    BillingReconcileOut,
    BillingReduceLimitIn,
    BillingReduceLimitOut,
    BillingSettingsOut,
    BillingSettingsUpdate,
    PricingOut,
)
from shop_claim_portal.services.audit import log_admin_action
from shop_claim_portal.services.billing_pricing import (
    ALLOWED_MONTHS,
    MAX_SERVERS,
    NETWORK3_RUB,
    UNLIMITED_RUB,
    BillingCompleteError,
    calc_amount_kopecks,
    complete_yookassa_payment,
    find_billing_payment_for_yookassa,
    get_active_pending,
    get_platform_settings,
    resolve_payment_target,
    yookassa_configured,
)
from shop_claim_portal.services.onboarding import (
    assert_max_servers_floor,
    maybe_auto_bridge_sync,
    mark_deploy_pending,
)
from shop_claim_portal.services.yookassa_billing import (
    YooKassaError,
    create_yookassa_payment,
    fetch_yookassa_payment,
)

logger = logging.getLogger(__name__)

tenant_router = APIRouter(prefix="/api/tenant/billing", tags=["billing"])
webhook_router = APIRouter(prefix="/api/billing", tags=["billing"])
admin_router = APIRouter(prefix="/api/admin/billing", tags=["billing"])
public_pricing_router = APIRouter(prefix="/api/public", tags=["public"])

_RETRY_REMOTE_STATUSES = frozenset({"pending", "waiting_for_capture"})


def _check_checkout_rate_limit(request: Request, tenant_pk: int) -> None:
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"billing-checkout:ip:{ip}", max_events=20, window_sec=3600):
        raise HTTPException(status_code=429, detail="Слишком много запросов")
    if not rate_limiter.allow(f"billing-checkout:tenant:{tenant_pk}", max_events=10, window_sec=3600):
        raise HTTPException(status_code=429, detail="Слишком много запросов")


def _check_reconcile_rate_limit(request: Request, tenant_pk: int) -> None:
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"billing-reconcile:ip:{ip}", max_events=30, window_sec=3600):
        raise HTTPException(status_code=429, detail="Слишком много запросов")
    if not rate_limiter.allow(f"billing-reconcile:tenant:{tenant_pk}", max_events=15, window_sec=3600):
        raise HTTPException(status_code=429, detail="Слишком много запросов")


def _check_reduce_limit_rate_limit(request: Request, tenant_pk: int) -> None:
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"billing-reduce-limit:ip:{ip}", max_events=20, window_sec=3600):
        raise HTTPException(status_code=429, detail="Слишком много запросов")
    if not rate_limiter.allow(f"billing-reduce-limit:tenant:{tenant_pk}", max_events=10, window_sec=3600):
        raise HTTPException(status_code=429, detail="Слишком много запросов")


async def _load_subscriber_tenant(session: AsyncSession, user: SessionUser) -> Tenant:
    if not user.tenant_pk:
        raise HTTPException(status_code=404, detail="Not found")
    result = await session.execute(
        select(Tenant)
        .where(Tenant.id == user.tenant_pk)
        .options(selectinload(Tenant.sync_state))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Not found")
    if not tenant.enabled:
        raise HTTPException(status_code=403, detail="Tenant disabled")
    return tenant


async def _load_payment_for_reconcile(
    session: AsyncSession,
    tenant_pk: int,
    payment_id: str | None,
) -> BillingPayment | BillingReconcileOut | None:
    """Load payment for reconcile. Returns BillingReconcileOut if already succeeded."""
    load_opts = [selectinload(BillingPayment.tenant).selectinload(Tenant.sync_state)]
    if payment_id:
        payment = await session.get(BillingPayment, payment_id, options=load_opts)
        if payment is None or payment.tenant_pk != tenant_pk:
            raise HTTPException(status_code=404, detail="Платёж не найден")
        if payment.status == BillingPaymentStatus.succeeded.value:
            return BillingReconcileOut(status="ok", applied=False)
        if payment.status != BillingPaymentStatus.pending.value:
            raise HTTPException(status_code=409, detail="Платёж не может быть зачислен")
        return payment
    payment = await get_active_pending(session, tenant_pk)
    if payment is None:
        raise HTTPException(status_code=404, detail="Нет ожидающего платежа")
    loaded = await session.get(BillingPayment, payment.id, options=load_opts)
    return loaded or payment


@public_pricing_router.get("/pricing", response_model=PricingOut)
async def public_pricing(session: AsyncSession = Depends(get_session)) -> PricingOut:
    ps = await get_platform_settings(session)
    enabled = ps.billing_enabled and yookassa_configured()
    return PricingOut(
        price_per_server_rub=ps.price_per_server_rub,
        network3_rub=NETWORK3_RUB,
        unlimited_rub=UNLIMITED_RUB,
        billing_enabled=enabled,
        checkout_available=enabled,
    )


@tenant_router.post("/checkout", response_model=BillingCheckoutOut)
async def checkout(
    body: BillingCheckoutIn,
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> BillingCheckoutOut:
    settings = get_settings()
    ps = await get_platform_settings(session, settings)
    if not ps.billing_enabled:
        raise HTTPException(status_code=503, detail="Оплата временно недоступна")
    if not yookassa_configured(settings):
        raise HTTPException(status_code=503, detail="Платёжная система не настроена")
    if body.months not in ALLOWED_MONTHS:
        raise HTTPException(status_code=400, detail="months must be 1, 3 or 12")
    tenant = await _load_subscriber_tenant(session, user)
    _check_checkout_rate_limit(request, tenant.id)

    if body.payment_kind == PaymentKind.add_server.value and tenant.max_servers >= MAX_SERVERS:
        raise HTTPException(status_code=400, detail=f"Лимит серверов ({MAX_SERVERS}) достигнут")
    if body.payment_kind == PaymentKind.renewal_and_add_server.value and tenant.max_servers >= MAX_SERVERS:
        raise HTTPException(status_code=400, detail=f"Лимит серверов ({MAX_SERVERS}) достигнут")

    pending = await get_active_pending(session, tenant.id)
    if pending:
        raise HTTPException(
            status_code=409,
            detail="Уже есть незавершённый платёж. Завершите его или подождите 24 часа.",
        )

    price = ps.price_per_server_rub
    snapshot = tenant.max_servers
    target = resolve_payment_target(body.payment_kind, snapshot)
    amount_kopecks = calc_amount_kopecks(body.payment_kind, snapshot, body.months, price)
    if amount_kopecks <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    max_servers_delta = target - snapshot

    payment = BillingPayment(
        id=str(uuid.uuid4()),
        tenant_pk=tenant.id,
        payment_kind=body.payment_kind,
        months=body.months,
        max_servers_snapshot=snapshot,
        max_servers_delta=max_servers_delta,
        price_per_server_rub=price,
        amount_kopecks=amount_kopecks,
        status=BillingPaymentStatus.pending.value,
    )
    session.add(payment)
    await session.flush()

    try:
        confirmation_url = await create_yookassa_payment(payment, tenant, user.email, settings=settings)
    except YooKassaError as exc:
        payment.status = BillingPaymentStatus.failed.value
        await session.commit()
        raise HTTPException(status_code=502, detail="Ошибка платёжной системы") from exc

    await session.commit()
    return BillingCheckoutOut(confirmation_url=confirmation_url, payment_id=payment.id)


@tenant_router.post("/reconcile", response_model=BillingReconcileOut)
async def reconcile_billing(
    body: BillingReconcileIn,
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> BillingReconcileOut:
    settings = get_settings()
    if not yookassa_configured(settings):
        raise HTTPException(status_code=503, detail="Платёжная система не настроена")
    tenant = await _load_subscriber_tenant(session, user)
    _check_reconcile_rate_limit(request, tenant.id)
    loaded = await _load_payment_for_reconcile(session, tenant.id, body.payment_id)
    if isinstance(loaded, BillingReconcileOut):
        return loaded
    payment = loaded
    if not payment.yookassa_payment_id:
        raise HTTPException(status_code=409, detail="Платёж ещё не создан в ЮKassa")
    try:
        remote = await fetch_yookassa_payment(payment.yookassa_payment_id, settings=settings)
    except YooKassaError as exc:
        raise HTTPException(status_code=502, detail="Ошибка платёжной системы") from exc
    remote_status = remote.get("status")
    if remote_status in _RETRY_REMOTE_STATUSES:
        raise HTTPException(status_code=409, detail="Платёж ещё обрабатывается")
    if remote_status != "succeeded":
        raise HTTPException(status_code=409, detail="Платёж не завершён")
    try:
        result = await complete_yookassa_payment(session, payment, remote)
    except BillingCompleteError as exc:
        logger.warning("billing reconcile failed payment=%s: %s", payment.id, exc)
        raise HTTPException(status_code=400, detail="Не удалось зачислить платёж") from exc
    return BillingReconcileOut(status="ok", applied=result == "ok")


@tenant_router.post("/reduce-limit", response_model=BillingReduceLimitOut)
async def reduce_billing_limit(
    body: BillingReduceLimitIn,
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> BillingReduceLimitOut:
    tenant = await _load_subscriber_tenant(session, user)
    _check_reduce_limit_rate_limit(request, tenant.id)
    current = tenant.max_servers
    if body.max_servers >= current:
        raise HTTPException(status_code=400, detail="Новый лимит должен быть меньше текущего")
    try:
        await assert_max_servers_floor(session, tenant.id, body.max_servers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    tenant.max_servers = body.max_servers
    mark_deploy_pending(tenant)
    await log_admin_action(
        session,
        actor_user_id=user.id,
        action="billing_reduce_limit",
        target_type="tenant",
        target_id=tenant.tenant_id,
        meta={"from": current, "to": body.max_servers},
    )
    await session.commit()
    await maybe_auto_bridge_sync(session)
    await session.commit()
    return BillingReduceLimitOut(max_servers=tenant.max_servers)


@tenant_router.get("/payments", response_model=list[BillingPaymentOut])
async def tenant_payments(
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> list[BillingPaymentOut]:
    if not user.tenant_pk:
        return []
    result = await session.execute(
        select(BillingPayment)
        .where(BillingPayment.tenant_pk == user.tenant_pk)
        .order_by(BillingPayment.created_at.desc())
        .limit(20)
    )
    return [_payment_out(p) for p in result.scalars().all()]


@webhook_router.post("/yookassa/webhook")
async def yookassa_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON") from None

    event = body.get("event")
    obj = body.get("object") or {}
    payment_id = obj.get("id")
    if not payment_id:
        logger.info("YooKassa webhook: ignored (no payment id), event=%s", event)
        return {"status": "ignored"}

    logger.info("YooKassa webhook: event=%s payment_id=%s", event, payment_id)

    if event == "payment.canceled":
        result = await session.execute(
            select(BillingPayment).where(BillingPayment.yookassa_payment_id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if payment and payment.status == BillingPaymentStatus.pending.value:
            payment.status = BillingPaymentStatus.canceled.value
            await session.commit()
            logger.info("YooKassa webhook: canceled payment_db_id=%s", payment.id)
        return {"status": "ok"}

    if event != "payment.succeeded":
        logger.info("YooKassa webhook: ignored event=%s payment_id=%s", event, payment_id)
        return {"status": "ignored"}

    try:
        remote = await fetch_yookassa_payment(payment_id)
    except YooKassaError:
        logger.warning("YooKassa webhook: failed to fetch payment %s", payment_id)
        raise HTTPException(status_code=502, detail="Verification failed") from None

    remote_status = remote.get("status")
    if remote_status in _RETRY_REMOTE_STATUSES:
        logger.info(
            "YooKassa webhook: payment %s not ready (status=%s), retry requested",
            payment_id,
            remote_status,
        )
        raise HTTPException(status_code=503, detail="Payment not ready")

    if remote_status != "succeeded":
        logger.warning(
            "YooKassa webhook: ignored payment %s remote_status=%s",
            payment_id,
            remote_status,
        )
        return {"status": "ignored"}

    meta = remote.get("metadata") or {}
    payment_db_id = meta.get("payment_db_id")
    payment = await find_billing_payment_for_yookassa(
        session,
        yookassa_payment_id=payment_id,
        payment_db_id=str(payment_db_id) if payment_db_id else None,
    )
    if payment is None:
        logger.warning(
            "YooKassa webhook: unknown payment yk=%s payment_db_id=%s",
            payment_id,
            payment_db_id,
        )
        return {"status": "ignored"}

    if payment.status == BillingPaymentStatus.succeeded.value:
        logger.info("YooKassa webhook: already succeeded payment_db_id=%s", payment.id)
        return {"status": "ok"}

    try:
        await complete_yookassa_payment(session, payment, remote)
    except BillingCompleteError as exc:
        logger.warning("YooKassa webhook: complete failed yk=%s db=%s: %s", payment_id, payment.id, exc)
        if "amount mismatch" in str(exc):
            raise HTTPException(status_code=400, detail="Amount mismatch") from exc
        raise HTTPException(status_code=400, detail="Cannot complete payment") from exc

    logger.info("YooKassa webhook: applied payment_db_id=%s yk=%s", payment.id, payment_id)
    return {"status": "ok"}


@admin_router.get("/settings", response_model=BillingSettingsOut)
async def admin_billing_settings(
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> BillingSettingsOut:
    ps = await get_platform_settings(session)
    return BillingSettingsOut(
        price_per_server_rub=ps.price_per_server_rub,
        billing_enabled=ps.billing_enabled,
        yookassa_configured=yookassa_configured(),
    )


@admin_router.patch("/settings", response_model=BillingSettingsOut)
async def admin_update_billing_settings(
    body: BillingSettingsUpdate,
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> BillingSettingsOut:
    ps = await get_platform_settings(session)
    if body.price_per_server_rub is not None:
        if body.price_per_server_rub > NETWORK3_RUB:
            raise HTTPException(
                status_code=400,
                detail=f"Цена 1 карты не должна превышать сеть ({NETWORK3_RUB} ₽)",
            )
        ps.price_per_server_rub = body.price_per_server_rub
    if body.billing_enabled is not None:
        ps.billing_enabled = body.billing_enabled
    await log_admin_action(
        session,
        actor_user_id=admin.id,
        action="billing_settings_update",
        target_type="platform",
        target_id="settings",
        meta=body.model_dump(exclude_none=True),
    )
    await session.commit()
    return BillingSettingsOut(
        price_per_server_rub=ps.price_per_server_rub,
        billing_enabled=ps.billing_enabled,
        yookassa_configured=yookassa_configured(),
    )


@admin_router.get("/tenants/{tenant_slug}/payments", response_model=list[BillingPaymentOut])
async def admin_tenant_payments(
    tenant_slug: str,
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> list[BillingPaymentOut]:
    result = await session.execute(select(Tenant).where(Tenant.tenant_id == tenant_slug))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Not found")
    payments = await session.execute(
        select(BillingPayment)
        .where(BillingPayment.tenant_pk == tenant.id)
        .order_by(BillingPayment.created_at.desc())
        .limit(50)
    )
    return [_payment_out(p) for p in payments.scalars().all()]


@admin_router.post("/tenants/{tenant_slug}/extend")
async def admin_extend_subscription(
    tenant_slug: str,
    body: BillingExtendIn,
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if body.days not in (30, 365):
        raise HTTPException(status_code=400, detail="days must be 30 or 365")
    result = await session.execute(
        select(Tenant)
        .where(Tenant.tenant_id == tenant_slug)
        .options(selectinload(Tenant.sync_state))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Not found")
    base = max(date.today(), tenant.subscription_until)
    tenant.subscription_until = base + timedelta(days=body.days)
    mark_deploy_pending(tenant)
    await log_admin_action(
        session,
        actor_user_id=admin.id,
        action="billing_manual_extend",
        target_type="tenant",
        target_id=tenant_slug,
        meta={"days": body.days, "reason": body.reason},
    )
    await session.commit()
    await maybe_auto_bridge_sync(session)
    await session.commit()
    return {"status": "ok", "subscription_until": tenant.subscription_until.isoformat()}


def _payment_out(p: BillingPayment) -> BillingPaymentOut:
    return BillingPaymentOut(
        id=p.id,
        payment_kind=p.payment_kind,
        months=p.months,
        amount_rub=p.amount_kopecks // 100,
        price_per_server_rub=p.price_per_server_rub,
        status=p.status,
        created_at=p.created_at,
        paid_at=p.paid_at,
        yookassa_payment_id=p.yookassa_payment_id,
    )
