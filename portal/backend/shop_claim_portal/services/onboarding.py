"""Onboarding helpers: servers, deploy pending, auto bridge sync."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shop_claim_portal.config import get_settings
from shop_claim_portal.models import DeployStatus, GameServer, Tenant, TenantSyncState
from shop_claim_portal.services.bridge_sync import BridgeSyncError, generate_api_token, sync_bridge
from shop_claim_portal.services.crypto import encrypt_secret

logger = logging.getLogger(__name__)


def tenant_wargm_configured(tenant: Tenant) -> bool:
    return bool(tenant.wargm_shop_id.strip() and tenant.wargm_api_key_enc.strip())


def mark_deploy_pending(tenant: Tenant) -> None:
    if tenant.sync_state is None:
        tenant.sync_state = TenantSyncState(
            tenant_pk=tenant.id,
            deploy_status=DeployStatus.pending.value,
        )
    else:
        tenant.sync_state.deploy_status = DeployStatus.pending.value


async def count_tenant_servers(session: AsyncSession, tenant_pk: int) -> int:
    result = await session.execute(
        select(func.count()).select_from(GameServer).where(GameServer.tenant_pk == tenant_pk)
    )
    return int(result.scalar_one())


async def assert_max_servers_floor(session: AsyncSession, tenant_pk: int, new_max: int) -> int:
    """Return server count; raise ValueError if new_max is below active server records."""
    count = await count_tenant_servers(session, tenant_pk)
    if new_max < count:
        raise ValueError(f"Лимит не может быть меньше числа серверов ({count})")
    return count


async def create_game_server(
    session: AsyncSession,
    tenant: Tenant,
    *,
    server_id: str,
    shop_server_id: int,
    catalog_path: str | None = None,
    enabled: bool = True,
) -> tuple[GameServer, str]:
    dup = await session.execute(select(GameServer).where(GameServer.server_id == server_id))
    if dup.scalar_one_or_none():
        raise ValueError("server_id exists")

    current = await count_tenant_servers(session, tenant.id)
    if current >= tenant.max_servers:
        raise ValueError(f"Достигнут лимит серверов ({tenant.max_servers})")

    token = generate_api_token()
    catalog = catalog_path or tenant.catalog_offers_path
    server = GameServer(
        tenant_pk=tenant.id,
        server_id=server_id,
        shop_server_id=shop_server_id,
        api_token_enc=encrypt_secret(token),
        enabled=enabled,
        catalog_path=catalog,
    )
    session.add(server)
    mark_deploy_pending(tenant)
    return server, token


async def maybe_auto_bridge_sync(session: AsyncSession) -> dict | None:
    settings = get_settings()
    if not settings.auto_bridge_sync:
        return None
    bridge_path = settings.resolved_bridge_path()
    if not bridge_path:
        logger.warning("auto_bridge_sync skipped: PORTAL_BRIDGE_CONFIG_PATH not set")
        return None
    try:
        return await sync_bridge(session, bridge_path, dry_run=False)
    except BridgeSyncError as exc:
        logger.warning("auto_bridge_sync failed: %s", exc)
        result = await session.execute(select(Tenant).options(selectinload(Tenant.sync_state)))
        for tenant in result.scalars().all():
            if tenant.sync_state:
                tenant.sync_state.deploy_status = DeployStatus.error.value
        return {"error": str(exc)}
