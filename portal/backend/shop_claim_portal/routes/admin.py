"""Provider admin routes."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shop_claim_portal.auth.deps import SessionUser, require_provider
from shop_claim_portal.config import get_settings
from shop_claim_portal.db import get_session
from shop_claim_portal.models import (
    DeployStatus,
    GameServer,
    Lead,
    LeadStatus,
    Tenant,
    TenantPlan,
    DEFAULT_FREE_YEAR_DAYS,
    TenantSyncState,
    Ticket,
    TicketMessage,
    TokenPurpose,
    User,
    UserRole,
)
from shop_claim_portal.schemas import (
    BridgeSyncResult,
    LeadOut,
    ServerCreate,
    ServerCreatedOut,
    ServerOut,
    TenantCreate,
    TenantDetailOut,
    TenantOut,
    TenantUpdate,
    TenantUserOut,
    TicketDetailOut,
    TicketMessageCreate,
    TicketMessageOut,
    TicketOut,
    TicketStatusUpdate,
)
from shop_claim_portal.services.audit import log_admin_action
from shop_claim_portal.services.bridge_sync import (
    BridgeSyncError,
    _default_catalog_paths,
    sync_bridge,
)
from shop_claim_portal.services.crypto import decrypt_secret, encrypt_secret, mask_secret
from shop_claim_portal.services.email import send_invite_email
from shop_claim_portal.services.action_tokens import create_action_token
from shop_claim_portal.services.onboarding import (
    assert_max_servers_floor,
    create_game_server,
    maybe_auto_bridge_sync,
    tenant_wargm_configured,
)
from shop_claim_portal.services.password import hash_password
from shop_claim_portal.services.scrubber import scrub_secrets
from shop_claim_portal.services.validation import validate_email_no_crlf

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _tenant_out(t: Tenant) -> TenantOut:
    deploy = t.sync_state.deploy_status if t.sync_state else DeployStatus.pending.value
    return TenantOut(
        id=t.id,
        tenant_id=t.tenant_id,
        enabled=t.enabled,
        subscription_until=t.subscription_until,
        plan=t.plan,
        wargm_shop_id=t.wargm_shop_id,
        catalog_offers_path=t.catalog_offers_path,
        theme_prefix=t.theme_prefix,
        deploy_status=deploy,
        server_count=len(t.servers),
        max_servers=t.max_servers,
        wargm_configured=tenant_wargm_configured(t),
    )


async def _tenant_by_slug(session: AsyncSession, slug: str) -> Tenant:
    result = await session.execute(
        select(Tenant)
        .where(Tenant.tenant_id == slug)
        .options(
            selectinload(Tenant.servers),
            selectinload(Tenant.sync_state),
            selectinload(Tenant.users),
        )
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.get("/leads", response_model=list[LeadOut])
async def list_leads(
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[LeadOut]:
    q = select(Lead).order_by(Lead.id.desc())
    if status_filter:
        q = q.where(Lead.status == status_filter)
    result = await session.execute(q)
    return [
        LeadOut(
            id=l.id,
            project_name=l.project_name,
            email=l.email,
            telegram=l.telegram,
            instance_count=l.instance_count,
            comment=l.comment,
            status=l.status,
            created_at=l.created_at,
        )
        for l in result.scalars().all()
    ]


@router.patch("/leads/{lead_id}")
async def update_lead_status(
    lead_id: int,
    status_value: str = Query(alias="status"),
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> LeadOut:
    if status_value not in (LeadStatus.rejected.value, LeadStatus.new.value):
        raise HTTPException(status_code=400, detail="Invalid status")
    lead = await session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Not found")
    lead.status = status_value
    await log_admin_action(
        session, actor_user_id=admin.id, action="lead_status", target_type="lead", target_id=str(lead_id)
    )
    await session.commit()
    await session.refresh(lead)
    return LeadOut(
        id=lead.id,
        project_name=lead.project_name,
        email=lead.email,
        telegram=lead.telegram,
        instance_count=lead.instance_count,
        comment=lead.comment,
        status=lead.status,
        created_at=lead.created_at,
    )


@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> list[TenantOut]:
    result = await session.execute(
        select(Tenant).options(selectinload(Tenant.servers), selectinload(Tenant.sync_state))
    )
    out = []
    for t in result.scalars().all():
        out.append(_tenant_out(t))
    return out


@router.get("/tenants/{tenant_slug}", response_model=TenantDetailOut)
async def get_tenant(
    tenant_slug: str,
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> TenantDetailOut:
    tenant = await _tenant_by_slug(session, tenant_slug)
    servers = []
    for s in tenant.servers:
        token = decrypt_secret(s.api_token_enc)
        servers.append(
            ServerOut(
                server_id=s.server_id,
                shop_server_id=s.shop_server_id,
                api_token_masked=mask_secret(token),
                enabled=s.enabled,
                catalog_path=s.catalog_path,
            )
        )
    users = [
        TenantUserOut(
            id=u.id,
            email=u.email,
            is_active=u.is_active,
            has_password=bool(u.password_hash),
        )
        for u in tenant.users
        if u.role == UserRole.subscriber.value
    ]
    base = _tenant_out(tenant)
    return TenantDetailOut(**base.model_dump(), servers=servers, users=users)


@router.get("/tenants/{tenant_slug}/users", response_model=list[TenantUserOut])
async def list_tenant_users(
    tenant_slug: str,
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> list[TenantUserOut]:
    tenant = await _tenant_by_slug(session, tenant_slug)
    return [
        TenantUserOut(
            id=u.id,
            email=u.email,
            is_active=u.is_active,
            has_password=bool(u.password_hash),
        )
        for u in tenant.users
        if u.role == UserRole.subscriber.value
    ]


@router.post("/tenants", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate,
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> TenantOut:
    existing = await session.execute(select(Tenant).where(Tenant.tenant_id == body.tenant_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="tenant_id exists")

    offers, vehicle = _default_catalog_paths(body.tenant_id)
    wargm_key = body.wargm_api_key.strip()
    max_servers = body.max_servers
    if max_servers is None and body.lead_id:
        lead_row = await session.get(Lead, body.lead_id)
        if lead_row:
            max_servers = lead_row.instance_count
    if max_servers is None:
        max_servers = 1

    subscription_until = body.subscription_until or (
        date.today() + timedelta(days=DEFAULT_FREE_YEAR_DAYS)
    )
    plan = body.plan or TenantPlan.free_year.value

    tenant = Tenant(
        tenant_id=body.tenant_id,
        enabled=True,
        subscription_until=subscription_until,
        plan=plan,
        wargm_shop_id=body.wargm_shop_id.strip(),
        wargm_api_key_enc=encrypt_secret(wargm_key) if wargm_key else "",
        wargm_api_base=body.wargm_api_base,
        catalog_offers_path=body.catalog_offers_path or offers,
        catalog_vehicle_profiles_path=body.catalog_vehicle_profiles_path or vehicle,
        theme_prefix=body.theme_prefix,
        lead_id=body.lead_id,
        max_servers=max_servers,
    )
    session.add(tenant)
    await session.flush()
    tenant.sync_state = TenantSyncState(
        tenant_pk=tenant.id,
        deploy_status=DeployStatus.pending.value,
    )

    if body.lead_id:
        lead = await session.get(Lead, body.lead_id)
        if lead:
            lead.status = LeadStatus.converted.value

    if body.subscriber_email:
        email = validate_email_no_crlf(str(body.subscriber_email))
        user = User(
            email=email,
            password_hash="",
            role=UserRole.subscriber.value,
            tenant_pk=tenant.id,
            is_active=False,
        )
        session.add(user)

    await log_admin_action(
        session,
        actor_user_id=admin.id,
        action="tenant_create",
        target_type="tenant",
        target_id=body.tenant_id,
    )
    await session.commit()
    await session.refresh(tenant, ["servers", "sync_state"])
    return _tenant_out(tenant)


@router.patch("/tenants/{tenant_slug}", response_model=TenantOut)
async def update_tenant(
    tenant_slug: str,
    body: TenantUpdate,
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> TenantOut:
    result = await session.execute(
        select(Tenant)
        .where(Tenant.tenant_id == tenant_slug)
        .options(selectinload(Tenant.servers), selectinload(Tenant.sync_state))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Not found")
    if body.enabled is not None:
        tenant.enabled = body.enabled
    if body.subscription_until is not None:
        tenant.subscription_until = body.subscription_until
    if body.plan is not None:
        tenant.plan = body.plan
    if body.wargm_shop_id is not None:
        tenant.wargm_shop_id = body.wargm_shop_id
    if body.wargm_api_key is not None:
        tenant.wargm_api_key_enc = encrypt_secret(body.wargm_api_key)
    if body.theme_prefix is not None:
        tenant.theme_prefix = body.theme_prefix
    if body.max_servers is not None:
        try:
            await assert_max_servers_floor(session, tenant.id, body.max_servers)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        tenant.max_servers = body.max_servers
    if tenant.sync_state:
        tenant.sync_state.deploy_status = DeployStatus.pending.value
    await log_admin_action(
        session,
        actor_user_id=admin.id,
        action="tenant_update",
        target_type="tenant",
        target_id=tenant_slug,
    )
    await session.commit()
    await session.refresh(tenant, ["servers", "sync_state"])
    await maybe_auto_bridge_sync(session)
    await session.commit()
    return _tenant_out(tenant)


@router.post("/tenants/{tenant_slug}/servers", response_model=ServerCreatedOut, status_code=201)
async def add_server(
    tenant_slug: str,
    body: ServerCreate,
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> ServerCreatedOut:
    tenant = await _tenant_by_slug(session, tenant_slug)
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
    await log_admin_action(
        session,
        actor_user_id=admin.id,
        action="server_create",
        target_type="server",
        target_id=body.server_id,
    )
    await session.commit()
    await maybe_auto_bridge_sync(session)
    await session.commit()
    return ServerCreatedOut(
        server_id=server.server_id,
        shop_server_id=server.shop_server_id,
        api_token_masked=mask_secret(token),
        enabled=server.enabled,
        catalog_path=server.catalog_path,
        api_token_plain=token,
    )


@router.post("/users/{user_id}/invite")
async def send_invite(
    user_id: int,
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    user = await session.get(User, user_id)
    if not user or user.role != UserRole.subscriber.value:
        raise HTTPException(status_code=404, detail="Not found")

    code, _invite = await create_action_token(
        session, user_id=user_id, purpose=TokenPurpose.invite.value
    )
    await log_admin_action(
        session,
        actor_user_id=admin.id,
        action="invite_sent",
        target_type="user",
        target_id=str(user_id),
    )
    await session.commit()
    sent = send_invite_email(to_email=user.email, invite_code=code)
    return {"status": "ok", "email_sent": str(sent).lower(), "invite_code": code}


@router.post("/bridge/sync", response_model=BridgeSyncResult)
async def bridge_sync_endpoint(
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
    dry_run: bool = Query(default=False),
) -> BridgeSyncResult:
    settings = get_settings()
    bridge_path = settings.resolved_bridge_path()
    if not bridge_path:
        raise HTTPException(status_code=400, detail="PORTAL_BRIDGE_CONFIG_PATH not set")
    try:
        result = await sync_bridge(session, bridge_path, dry_run=dry_run)
    except BridgeSyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await log_admin_action(
        session,
        actor_user_id=admin.id,
        action="bridge_sync",
        target_type="bridge",
        target_id="bridge.json",
        meta={"dry_run": dry_run, "changed": result.get("changed")},
    )
    if not dry_run:
        await session.commit()
    else:
        await session.rollback()
    return BridgeSyncResult(**result)


@router.get("/tickets", response_model=list[TicketOut])
async def admin_list_tickets(
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> list[TicketOut]:
    result = await session.execute(select(Ticket).order_by(Ticket.updated_at.desc()))
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


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
async def admin_get_ticket(
    ticket_id: int,
    _: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> TicketDetailOut:
    result = await session.execute(
        select(Ticket).where(Ticket.id == ticket_id).options(selectinload(Ticket.messages))
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
            TicketMessageOut(id=m.id, body=m.body, is_provider=m.is_provider, created_at=m.created_at)
            for m in ticket.messages
        ],
    )


@router.patch("/tickets/{ticket_id}", response_model=TicketOut)
async def admin_update_ticket(
    ticket_id: int,
    body: TicketStatusUpdate,
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> TicketOut:
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Not found")
    ticket.status = body.status
    await log_admin_action(
        session,
        actor_user_id=admin.id,
        action="ticket_status",
        target_type="ticket",
        target_id=str(ticket_id),
    )
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


@router.post("/tickets/{ticket_id}/messages", response_model=TicketMessageOut, status_code=201)
async def admin_reply_ticket(
    ticket_id: int,
    body: TicketMessageCreate,
    admin: SessionUser = Depends(require_provider),
    session: AsyncSession = Depends(get_session),
) -> TicketMessageOut:
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Not found")
    msg = TicketMessage(
        ticket_id=ticket_id,
        author_user_id=admin.id,
        body=scrub_secrets(body.body),
        is_provider=True,
    )
    session.add(msg)
    ticket.status = "waiting_subscriber"
    await session.commit()
    await session.refresh(msg)
    return TicketMessageOut(
        id=msg.id,
        body=msg.body,
        is_provider=msg.is_provider,
        created_at=msg.created_at,
    )
