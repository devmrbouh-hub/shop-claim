"""Tenant (subscriber) routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shop_claim_portal.auth.deps import SessionUser, require_subscriber
from shop_claim_portal.config import get_settings
from shop_claim_portal.db import get_session
from shop_claim_portal.models import DeployStatus, GameServer, Tenant, Ticket, TicketMessage, TicketStatus, User
from shop_claim_portal.rate_limit import rate_limiter
from shop_claim_portal.schemas import (
    ServerCreate,
    ServerOut,
    ServerUpdate,
    SubscriptionOut,
    TicketCreate,
    TicketDetailOut,
    TicketMessageCreate,
    TicketMessageOut,
    TicketOut,
    UserOut,
    WargmCredentialsIn,
)
from shop_claim_portal.services.config_export import build_mod_config
from shop_claim_portal.services.crypto import decrypt_secret, encrypt_secret, mask_secret
from shop_claim_portal.services.billing_pricing import (
    MAX_SERVERS,
    NETWORK3_RUB,
    UNLIMITED_RUB,
    get_platform_settings,
    monthly_fee_rub,
    pricing_tier,
    resolve_add_target,
    yookassa_configured,
)
from shop_claim_portal.services.onboarding import (
    create_game_server,
    maybe_auto_bridge_sync,
    mark_deploy_pending,
    tenant_wargm_configured,
)
from shop_claim_portal.services.scrubber import scrub_secrets
from shop_claim_portal.services.step_up import verify_step_up_password

router = APIRouter(prefix="/api/tenant", tags=["tenant"])


def _bridge_url() -> str:
    url = get_settings().bridge_public_url
    return url if url.endswith("/") else url + "/"


def _check_setup_rate_limit(request: Request, user_id: int, prefix: str) -> None:
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"{prefix}:ip:{ip}", max_events=30, window_sec=60):
        raise HTTPException(status_code=429, detail="Слишком много запросов")
    if not rate_limiter.allow(f"{prefix}:user:{user_id}", max_events=20, window_sec=60):
        raise HTTPException(status_code=429, detail="Слишком много запросов")


async def _load_tenant(session: AsyncSession, user: SessionUser) -> Tenant:
    if not user.tenant_pk:
        raise HTTPException(status_code=404, detail="Not found")
    result = await session.execute(
        select(Tenant)
        .where(Tenant.id == user.tenant_pk)
        .options(selectinload(Tenant.sync_state), selectinload(Tenant.servers))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Not found")
    return tenant


@router.get("/me", response_model=UserOut)
async def tenant_me(user: SessionUser = Depends(require_subscriber)) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        tenant_id=user.tenant_slug,
        is_active=True,
    )


@router.get("/subscription", response_model=SubscriptionOut)
async def subscription(
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionOut:
    tenant = await _load_tenant(session, user)
    deploy = tenant.sync_state.deploy_status if tenant.sync_state else DeployStatus.pending.value
    active = tenant.enabled and date.today() <= tenant.subscription_until
    server_count = len(tenant.servers)
    days_remaining = (tenant.subscription_until - date.today()).days
    ps = await get_platform_settings(session)
    checkout_ok = ps.billing_enabled and yookassa_configured()
    price_1 = ps.price_per_server_rub
    next_add_target: int | None = None
    next_add_fee: int | None = None
    if tenant.max_servers < MAX_SERVERS:
        next_add_target = resolve_add_target(tenant.max_servers)
        next_add_fee = monthly_fee_rub(next_add_target, price_1)
    return SubscriptionOut(
        tenant_id=tenant.tenant_id,
        enabled=tenant.enabled,
        subscription_until=tenant.subscription_until,
        active=active,
        deploy_status=deploy,
        bridge_url=_bridge_url(),
        max_servers=tenant.max_servers,
        server_count=server_count,
        wargm_configured=tenant_wargm_configured(tenant),
        plan=tenant.plan,
        days_remaining=days_remaining,
        price_per_server_rub=price_1,
        billing_enabled=ps.billing_enabled,
        checkout_available=checkout_ok,
        monthly_fee_rub=monthly_fee_rub(tenant.max_servers, price_1),
        tier=pricing_tier(tenant.max_servers),
        network3_rub=NETWORK3_RUB,
        unlimited_rub=UNLIMITED_RUB,
        next_add_target_max=next_add_target,
        next_add_monthly_fee_rub=next_add_fee,
    )


@router.put("/wargm")
async def update_wargm(
    body: WargmCredentialsIn,
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    _check_setup_rate_limit(request, user.id, "tenant-wargm")
    tenant = await _load_tenant(session, user)
    db_user = await session.get(User, user.id)
    if not db_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    verify_step_up_password(db_user, body.current_password)
    tenant.wargm_shop_id = body.wargm_shop_id.strip()
    tenant.wargm_api_key_enc = encrypt_secret(body.wargm_api_key.strip())
    mark_deploy_pending(tenant)
    await maybe_auto_bridge_sync(session)
    await session.commit()
    return {"status": "ok"}


@router.post("/servers", response_model=ServerOut, status_code=status.HTTP_201_CREATED)
async def create_server(
    body: ServerCreate,
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> ServerOut:
    _check_setup_rate_limit(request, user.id, "tenant-server")
    tenant = await _load_tenant(session, user)
    try:
        server, token = await create_game_server(
            session,
            tenant,
            server_id=body.server_id,
            shop_server_id=body.shop_server_id,
            catalog_path=body.catalog_path,
            enabled=body.enabled,
        )
    except ValueError as exc:
        msg = str(exc)
        code = 409 if "exists" in msg else 400
        raise HTTPException(status_code=code, detail=msg) from exc
    await maybe_auto_bridge_sync(session)
    await session.commit()
    return ServerOut(
        server_id=server.server_id,
        shop_server_id=server.shop_server_id,
        api_token_masked=mask_secret(token),
        enabled=server.enabled,
        catalog_path=server.catalog_path,
    )


@router.patch("/servers/{server_id}", response_model=ServerOut)
async def update_server(
    server_id: str,
    body: ServerUpdate,
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> ServerOut:
    _check_setup_rate_limit(request, user.id, "tenant-server")
    tenant = await _load_tenant(session, user)
    result = await session.execute(
        select(GameServer).where(
            GameServer.tenant_pk == user.tenant_pk,
            GameServer.server_id == server_id,
        )
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Not found")
    if body.shop_server_id is not None:
        server.shop_server_id = body.shop_server_id
    if body.enabled is not None:
        server.enabled = body.enabled
    mark_deploy_pending(tenant)
    await maybe_auto_bridge_sync(session)
    await session.commit()
    token = decrypt_secret(server.api_token_enc)
    return ServerOut(
        server_id=server.server_id,
        shop_server_id=server.shop_server_id,
        api_token_masked=mask_secret(token),
        enabled=server.enabled,
        catalog_path=server.catalog_path,
    )


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: str,
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> Response:
    _check_setup_rate_limit(request, user.id, "tenant-server")
    tenant = await _load_tenant(session, user)
    result = await session.execute(
        select(GameServer).where(
            GameServer.tenant_pk == user.tenant_pk,
            GameServer.server_id == server_id,
        )
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Not found")
    await session.delete(server)
    mark_deploy_pending(tenant)
    await maybe_auto_bridge_sync(session)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/activate")
async def activate_tenant(
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> dict:
    _check_setup_rate_limit(request, user.id, "tenant-activate")
    tenant = await _load_tenant(session, user)
    if not tenant_wargm_configured(tenant):
        raise HTTPException(status_code=400, detail="Сначала укажите wargm shop_id и api_key")
    if not tenant.servers:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы один сервер")
    mark_deploy_pending(tenant)
    result = await maybe_auto_bridge_sync(session)
    if result is None:
        settings = get_settings()
        bridge_path = settings.resolved_bridge_path()
        if not bridge_path:
            raise HTTPException(status_code=400, detail="Синхронизация Bridge не настроена")
        from shop_claim_portal.services.bridge_sync import BridgeSyncError, sync_bridge

        try:
            result = await sync_bridge(session, bridge_path, dry_run=False)
        except BridgeSyncError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    deploy = tenant.sync_state.deploy_status if tenant.sync_state else DeployStatus.pending.value
    return {"status": "ok", "deploy_status": deploy, "sync": result}


@router.get("/servers", response_model=list[ServerOut])
async def list_servers(
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> list[ServerOut]:
    result = await session.execute(
        select(GameServer).where(GameServer.tenant_pk == user.tenant_pk)
    )
    servers = result.scalars().all()
    out = []
    for s in servers:
        token = decrypt_secret(s.api_token_enc)
        out.append(
            ServerOut(
                server_id=s.server_id,
                shop_server_id=s.shop_server_id,
                api_token_masked=mask_secret(token),
                enabled=s.enabled,
                catalog_path=s.catalog_path,
            )
        )
    return out


@router.get("/servers/{server_id}/config.json")
async def download_config(
    server_id: str,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    result = await session.execute(
        select(GameServer).where(
            GameServer.tenant_pk == user.tenant_pk,
            GameServer.server_id == server_id,
        )
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Not found")
    tenant = await session.get(Tenant, user.tenant_pk)
    token = decrypt_secret(server.api_token_enc)
    config = build_mod_config(
        server_id=server.server_id,
        shop_server_id=server.shop_server_id,
        api_token=token,
        theme_prefix=tenant.theme_prefix if tenant else None,
    )
    return JSONResponse(
        content=config,
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="config_{server_id}.json"',
        },
    )


@router.get("/tickets", response_model=list[TicketOut])
async def list_tickets(
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> list[TicketOut]:
    result = await session.execute(
        select(Ticket).where(Ticket.tenant_pk == user.tenant_pk).order_by(Ticket.id.desc())
    )
    return [
        TicketOut(
            id=t.id,
            subject=t.subject,
            status=t.status,
            server_id=t.server_id,
            operation_id=t.operation_id,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in result.scalars().all()
    ]


@router.post("/tickets", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    body: TicketCreate,
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> TicketOut:
    _check_setup_rate_limit(request, user.id, "ticket_create")
    ticket = Ticket(
        tenant_pk=user.tenant_pk,
        server_id=body.server_id,
        subject=body.subject,
        operation_id=body.operation_id,
        status=TicketStatus.open.value,
    )
    session.add(ticket)
    await session.flush()
    msg = TicketMessage(
        ticket_id=ticket.id,
        author_user_id=user.id,
        body=scrub_secrets(body.body),
        is_provider=False,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(ticket)
    return TicketOut(
        id=ticket.id,
        subject=ticket.subject,
        status=ticket.status,
        server_id=ticket.server_id,
        operation_id=ticket.operation_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
async def get_ticket(
    ticket_id: int,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> TicketDetailOut:
    result = await session.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id, Ticket.tenant_pk == user.tenant_pk)
        .options(selectinload(Ticket.messages))
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Not found")
    return TicketDetailOut(
        id=ticket.id,
        subject=ticket.subject,
        status=ticket.status,
        server_id=ticket.server_id,
        operation_id=ticket.operation_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        messages=[
            TicketMessageOut(
                id=m.id,
                body=m.body,
                is_provider=m.is_provider,
                created_at=m.created_at,
            )
            for m in ticket.messages
        ],
    )


@router.post("/tickets/{ticket_id}/messages", response_model=TicketMessageOut, status_code=201)
async def reply_ticket(
    ticket_id: int,
    body: TicketMessageCreate,
    request: Request,
    user: SessionUser = Depends(require_subscriber),
    session: AsyncSession = Depends(get_session),
) -> TicketMessageOut:
    _check_setup_rate_limit(request, user.id, "tenant-ticket")
    result = await session.execute(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_pk == user.tenant_pk)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Not found")
    if ticket.status == TicketStatus.resolved.value:
        raise HTTPException(status_code=409, detail="Ticket is resolved")
    msg = TicketMessage(
        ticket_id=ticket_id,
        author_user_id=user.id,
        body=scrub_secrets(body.body),
        is_provider=False,
    )
    session.add(msg)
    ticket.status = TicketStatus.waiting_provider.value
    await session.commit()
    await session.refresh(msg)
    return TicketMessageOut(
        id=msg.id,
        body=msg.body,
        is_provider=msg.is_provider,
        created_at=msg.created_at,
    )
