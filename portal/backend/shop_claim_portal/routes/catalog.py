"""Catalog editor API routes."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shop_claim_portal.auth.deps import SessionUser, require_provider, require_subscriber
from shop_claim_portal.config import get_settings
from shop_claim_portal.db import get_session
from shop_claim_portal.models import GameServer, Tenant, User
from shop_claim_portal.rate_limit import rate_limiter
from shop_claim_portal.schemas import (
    CatalogImportResultOut,
    CatalogImportWargmIn,
    CatalogMetaOut,
    CatalogOfferIn,
    CatalogOut,
    CatalogPublishIn,
    CatalogPublishOut,
    VehicleProfileIn,
)
from shop_claim_portal.services.audit import log_admin_action
from shop_claim_portal.services.step_up import verify_step_up_password
from shop_claim_portal.services.bridge_reload import reload_bridge_catalog
from shop_claim_portal.services.catalog_service import (
    CatalogError,
    CatalogReloadError,
    PublishConflictError,
    catalog_meta,
    delete_draft_offer,
    discard_draft,
    load_merged,
    merge_wargm_import,
    normalize_offer_dict,
    publish_catalog,
    save_draft_offer,
    save_draft_vehicle_profile,
)
from shop_claim_portal.services.crypto import decrypt_secret
from shop_claim_portal.services.wargm_client import (
    PortalWargmClient,
    WargmApiError,
    wargm_offer_to_draft,
)

tenant_router = APIRouter(prefix="/api/tenant/catalog", tags=["catalog"])
admin_router = APIRouter(prefix="/api/admin/tenants", tags=["catalog-admin"])

BASE_DIR = __import__("pathlib").Path(__file__).resolve().parents[2]


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _check_catalog_rate_limit(request: Request, user_id: int, prefix: str) -> None:
    ip = _client_ip(request)
    if not rate_limiter.allow(f"{prefix}:ip:{ip}", max_events=30, window_sec=60):
        raise HTTPException(status_code=429, detail="Слишком много запросов")
    if not rate_limiter.allow(f"{prefix}:user:{user_id}", max_events=20, window_sec=60):
        raise HTTPException(status_code=429, detail="Слишком много запросов")


async def _subscriber_tenant(
    session: AsyncSession,
    user: SessionUser,
    *,
    require_active: bool = False,
) -> Tenant:
    if user.role != "subscriber" or not user.tenant_pk:
        raise HTTPException(status_code=403, detail="Subscriber only")
    tenant = await session.get(Tenant, user.tenant_pk)
    if not tenant or not tenant.enabled:
        raise HTTPException(status_code=403, detail="Tenant disabled")
    if require_active and date.today() > tenant.subscription_until:
        raise HTTPException(status_code=403, detail="Подписка неактивна")
    return tenant


async def _require_subscriber_step_up(session: AsyncSession, user: SessionUser, password: str | None) -> None:
    if not password:
        raise HTTPException(status_code=401, detail="Неверный текущий пароль")
    db_user = await session.get(User, user.id)
    if not db_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    verify_step_up_password(db_user, password)


async def _tenant_by_slug(session: AsyncSession, slug: str) -> Tenant:
    result = await session.execute(select(Tenant).where(Tenant.tenant_id == slug))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _catalog_root():
    return get_settings().resolved_catalog_root(BASE_DIR)


def _offer_body(offer: CatalogOfferIn) -> dict:
    data = offer.model_dump(by_alias=True, exclude_none=True)
    return normalize_offer_dict(data)


def _catalog_response(tenant: Tenant, catalog_root) -> CatalogOut:
    offers, profiles = load_merged(tenant, catalog_root)
    return CatalogOut(
        offers=offers,
        vehicle_profiles=profiles,
        has_unpublished_changes=tenant.catalog_has_unpublished,
        catalog_published_at=tenant.catalog_published_at,
    )


def _handle_catalog_error(exc: CatalogError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


async def _do_publish(
    session: AsyncSession,
    tenant: Tenant,
    user: SessionUser,
    body: CatalogPublishIn,
    *,
    audit: bool,
) -> CatalogPublishOut:
    settings = get_settings()
    catalog_root = settings.resolved_catalog_root(BASE_DIR)
    try:
        offers, _profiles, count = publish_catalog(
            tenant,
            catalog_root,
            expected_published_at=body.expected_published_at,
        )
    except PublishConflictError as exc:
        raise _handle_catalog_error(exc) from exc
    except CatalogError as exc:
        raise _handle_catalog_error(exc) from exc

    reloaded = 0
    reload_error: str | None = None
    try:
        reloaded = await reload_bridge_catalog(
            base_url=settings.bridge_admin_url,
            secret=settings.bridge_admin_secret,
            tenant_id=tenant.tenant_id,
        )
    except CatalogReloadError as exc:
        reload_error = str(exc)

    if audit:
        await log_admin_action(
            session,
            actor_user_id=user.id,
            action="catalog_published",
            target_type="tenant",
            target_id=tenant.tenant_id,
            meta={"offer_count": count, "reloaded": reloaded},
        )
    await session.commit()
    await session.refresh(tenant)

    if reload_error:
        raise HTTPException(
            status_code=502,
            detail=reload_error,
        )

    return CatalogPublishOut(
        status="ok",
        offer_count=count,
        reloaded=reloaded,
        catalog_published_at=tenant.catalog_published_at or datetime.utcnow(),
    )


@tenant_router.get("", response_model=CatalogOut)
async def get_catalog(
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> CatalogOut:
    tenant = await _subscriber_tenant(session, user)
    return _catalog_response(tenant, _catalog_root())


@tenant_router.get("/meta", response_model=CatalogMetaOut)
async def get_catalog_meta(
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> CatalogMetaOut:
    tenant = await _subscriber_tenant(session, user)
    meta = catalog_meta(tenant, _catalog_root())
    return CatalogMetaOut(**meta)


@tenant_router.put("/offers/{offer_id}")
async def put_offer(
    offer_id: str,
    body: CatalogOfferIn,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> CatalogOut:
    tenant = await _subscriber_tenant(session, user)
    catalog_root = _catalog_root()
    merged_offers, _ = load_merged(tenant, catalog_root)
    try:
        save_draft_offer(
            tenant,
            offer_id,
            _offer_body(body),
            existing_merged=merged_offers,
        )
    except CatalogError as exc:
        raise _handle_catalog_error(exc) from exc
    await session.commit()
    await session.refresh(tenant)
    return _catalog_response(tenant, catalog_root)


@tenant_router.delete("/offers/{offer_id}")
async def remove_offer(
    offer_id: str,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> CatalogOut:
    tenant = await _subscriber_tenant(session, user)
    catalog_root = _catalog_root()
    delete_draft_offer(tenant, offer_id)
    await session.commit()
    await session.refresh(tenant)
    return _catalog_response(tenant, catalog_root)


@tenant_router.post("/publish", response_model=CatalogPublishOut)
async def publish(
    body: CatalogPublishIn,
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> CatalogPublishOut:
    _check_catalog_rate_limit(request, user.id, "catalog-publish")
    tenant = await _subscriber_tenant(session, user, require_active=True)
    await _require_subscriber_step_up(session, user, body.current_password)
    return await _do_publish(session, tenant, user, body, audit=True)


@tenant_router.post("/discard", response_model=CatalogOut)
async def discard(
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> CatalogOut:
    tenant = await _subscriber_tenant(session, user)
    catalog_root = _catalog_root()
    discard_draft(tenant)
    await session.commit()
    await session.refresh(tenant)
    return _catalog_response(tenant, catalog_root)


@tenant_router.put("/vehicle-profiles/{class_name}")
async def put_vehicle_profile(
    class_name: str,
    body: VehicleProfileIn,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> CatalogOut:
    tenant = await _subscriber_tenant(session, user)
    catalog_root = _catalog_root()
    try:
        save_draft_vehicle_profile(
            tenant,
            class_name,
            body.model_dump(exclude_none=True),
        )
    except CatalogError as exc:
        raise _handle_catalog_error(exc) from exc
    await session.commit()
    await session.refresh(tenant)
    return _catalog_response(tenant, catalog_root)


@tenant_router.get("/preview-wargm/{offer_id}")
async def preview_wargm(
    offer_id: str,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> dict:
    tenant = await _subscriber_tenant(session, user)
    if not tenant.wargm_shop_id or not tenant.wargm_api_key_enc:
        raise HTTPException(status_code=400, detail="wargm ключи не настроены")
    shop_ids = await _shop_server_ids(session, tenant)
    client = PortalWargmClient(
        tenant.wargm_shop_id,
        decrypt_secret(tenant.wargm_api_key_enc),
        tenant.wargm_api_base,
    )
    try:
        data = await client.fetch_offer(offer_id)
        offer, warnings = wargm_offer_to_draft(data, shop_ids)
        return {"offer_id": offer_id, "wargm": data, "draft": offer, "warnings": warnings}
    except WargmApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    finally:
        await client.close()


async def _run_import_wargm(
    tenant: Tenant,
    session: AsyncSession,
    body: CatalogImportWargmIn,
) -> CatalogImportResultOut:
    if not tenant.wargm_shop_id or not tenant.wargm_api_key_enc:
        raise HTTPException(status_code=400, detail="wargm ключи не настроены")
    catalog_root = _catalog_root()
    merged_offers, _ = load_merged(tenant, catalog_root)
    shop_ids = await _shop_server_ids(session, tenant)
    client = PortalWargmClient(
        tenant.wargm_shop_id,
        decrypt_secret(tenant.wargm_api_key_enc),
        tenant.wargm_api_base,
    )
    imported: list[str] = []
    skipped: list[str] = []
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    try:
        batch = await client.fetch_offers_batch(body.offer_ids)
        for oid, data, err in batch:
            if err or data is None:
                errors.append({"offer_id": oid, "error": err or "unknown"})
                continue
            draft_offer, offer_warnings = wargm_offer_to_draft(data, shop_ids)
            for w in offer_warnings:
                warnings.append({"offer_id": oid, "warning": w})
            existing = merged_offers.get(oid)
            if existing and existing.get("name") and existing.get("items"):
                skipped.append(oid)
                continue
            merged = merge_wargm_import(existing, draft_offer)
            save_draft_offer(tenant, oid, merged, existing_merged=merged_offers)
            merged_offers[oid] = merged
            imported.append(oid)
    except WargmApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    finally:
        await client.close()
    await session.commit()
    return CatalogImportResultOut(
        imported=imported,
        skipped=skipped,
        errors=errors,
        warnings=warnings,
    )


@tenant_router.post("/import-wargm", response_model=CatalogImportResultOut)
async def import_wargm(
    body: CatalogImportWargmIn,
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> CatalogImportResultOut:
    _check_catalog_rate_limit(request, user.id, "catalog-import")
    tenant = await _subscriber_tenant(session, user)
    await _require_subscriber_step_up(session, user, body.current_password)
    return await _run_import_wargm(tenant, session, body)


async def _shop_server_ids(session: AsyncSession, tenant: Tenant) -> set[int]:
    result = await session.execute(
        select(GameServer.shop_server_id).where(GameServer.tenant_pk == tenant.id)
    )
    return {row[0] for row in result.all()}


@admin_router.get("/{slug}/catalog", response_model=CatalogOut)
async def admin_get_catalog(
    slug: str,
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> CatalogOut:
    tenant = await _tenant_by_slug(session, slug)
    return _catalog_response(tenant, _catalog_root())


@admin_router.get("/{slug}/catalog/meta", response_model=CatalogMetaOut)
async def admin_get_catalog_meta(
    slug: str,
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> CatalogMetaOut:
    tenant = await _tenant_by_slug(session, slug)
    return CatalogMetaOut(**catalog_meta(tenant, _catalog_root()))


@admin_router.put("/{slug}/catalog/offers/{offer_id}")
async def admin_put_offer(
    slug: str,
    offer_id: str,
    body: CatalogOfferIn,
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> CatalogOut:
    tenant = await _tenant_by_slug(session, slug)
    catalog_root = _catalog_root()
    merged_offers, _ = load_merged(tenant, catalog_root)
    try:
        save_draft_offer(tenant, offer_id, _offer_body(body), existing_merged=merged_offers)
    except CatalogError as exc:
        raise _handle_catalog_error(exc) from exc
    await session.commit()
    await session.refresh(tenant)
    return _catalog_response(tenant, catalog_root)


@admin_router.delete("/{slug}/catalog/offers/{offer_id}")
async def admin_delete_offer(
    slug: str,
    offer_id: str,
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> CatalogOut:
    tenant = await _tenant_by_slug(session, slug)
    catalog_root = _catalog_root()
    delete_draft_offer(tenant, offer_id)
    await session.commit()
    await session.refresh(tenant)
    return _catalog_response(tenant, catalog_root)


@admin_router.post("/{slug}/catalog/publish", response_model=CatalogPublishOut)
async def admin_publish(
    slug: str,
    body: CatalogPublishIn,
    request: Request,
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> CatalogPublishOut:
    _check_catalog_rate_limit(request, admin.id, "catalog-publish")
    tenant = await _tenant_by_slug(session, slug)
    return await _do_publish(session, tenant, admin, body, audit=True)


@admin_router.post("/{slug}/catalog/discard", response_model=CatalogOut)
async def admin_discard(
    slug: str,
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> CatalogOut:
    tenant = await _tenant_by_slug(session, slug)
    catalog_root = _catalog_root()
    discard_draft(tenant)
    await session.commit()
    await session.refresh(tenant)
    return _catalog_response(tenant, catalog_root)


@admin_router.put("/{slug}/catalog/vehicle-profiles/{class_name}")
async def admin_put_vehicle_profile(
    slug: str,
    class_name: str,
    body: VehicleProfileIn,
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> CatalogOut:
    tenant = await _tenant_by_slug(session, slug)
    catalog_root = _catalog_root()
    try:
        save_draft_vehicle_profile(tenant, class_name, body.model_dump(exclude_none=True))
    except CatalogError as exc:
        raise _handle_catalog_error(exc) from exc
    await session.commit()
    await session.refresh(tenant)
    return _catalog_response(tenant, catalog_root)


@admin_router.post("/{slug}/catalog/import-wargm", response_model=CatalogImportResultOut)
async def admin_import_wargm(
    slug: str,
    body: CatalogImportWargmIn,
    request: Request,
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> CatalogImportResultOut:
    _check_catalog_rate_limit(request, admin.id, "catalog-import")
    tenant = await _tenant_by_slug(session, slug)
    return await _run_import_wargm(tenant, session, body)
