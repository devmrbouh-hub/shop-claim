"""Sync Portal tenants to bridge.json."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shop_claim_bridge.config import validate_config
from shop_claim_bridge.models import BridgeConfig, GameServerConfig, TenantCatalogConfig, TenantConfig, WargmShopCredentials

from shop_claim_portal.models import DeployStatus, GameServer, Tenant, TenantSyncState
from shop_claim_portal.services.crypto import decrypt_secret


class BridgeSyncError(Exception):
    def __init__(self, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.details = details or []


def _default_catalog_paths(tenant_slug: str) -> tuple[str, str]:
    base = f"tenants/{tenant_slug}"
    return f"{base}/offers.yaml", f"{base}/vehicle_profiles.yaml"


def tenant_to_bridge_dict(tenant: Tenant, servers: list[GameServer]) -> dict[str, Any]:
    offers_path = tenant.catalog_offers_path or _default_catalog_paths(tenant.tenant_id)[0]
    vehicle_path = tenant.catalog_vehicle_profiles_path or _default_catalog_paths(tenant.tenant_id)[1]
    allowed_ips = None
    if tenant.allowed_egress_ips_json:
        allowed_ips = json.loads(tenant.allowed_egress_ips_json)
    wargm_key = decrypt_secret(tenant.wargm_api_key_enc) if tenant.wargm_api_key_enc else ""
    server_dicts = []
    for s in servers:
        token = decrypt_secret(s.api_token_enc)
        catalog_path = s.catalog_path or offers_path
        server_dicts.append(
            {
                "server_id": s.server_id,
                "shop_server_id": s.shop_server_id,
                "api_token": token,
                "enabled": s.enabled,
                "catalog_path": catalog_path,
            }
        )
    return {
        "tenant_id": tenant.tenant_id,
        "enabled": tenant.enabled,
        "subscription_until": tenant.subscription_until.isoformat(),
        "wargm": {
            "shop_id": tenant.wargm_shop_id,
            "api_key": wargm_key,
            "api_base": tenant.wargm_api_base,
        },
        "catalog": {
            "offers_path": offers_path,
            "vehicle_profiles_path": vehicle_path,
        },
        "allowed_egress_ips": allowed_ips,
        "servers": server_dicts,
    }


async def load_all_tenant_dicts(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.execute(
        select(Tenant).options(selectinload(Tenant.servers)).order_by(Tenant.tenant_id)
    )
    tenants = result.scalars().all()
    return [tenant_to_bridge_dict(t, t.servers) for t in tenants]


def merge_bridge_config(bridge_path: Path, tenant_dicts: list[dict[str, Any]]) -> dict[str, Any]:
    raw = json.loads(bridge_path.read_text(encoding="utf-8-sig"))
    raw["tenants"] = tenant_dicts
    return raw


def validate_merged_config(raw: dict[str, Any]) -> BridgeConfig:
    config = BridgeConfig.model_validate(raw)
    validate_config(config)
    return config


def tenants_hash(tenant_dicts: list[dict[str, Any]]) -> str:
    payload = json.dumps(tenant_dicts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


async def sync_bridge(
    session: AsyncSession,
    bridge_path: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not bridge_path.is_file():
        raise BridgeSyncError(f"bridge.json not found: {bridge_path}")

    tenant_dicts = await load_all_tenant_dicts(session)
    merged = merge_bridge_config(bridge_path, tenant_dicts)
    try:
        validate_merged_config(merged)
    except Exception as exc:
        raise BridgeSyncError(str(exc)) from exc

    new_hash = tenants_hash(tenant_dicts)
    old_raw = json.loads(bridge_path.read_text(encoding="utf-8-sig"))
    old_hash = tenants_hash(old_raw.get("tenants") or [])

    result: dict[str, Any] = {
        "dry_run": dry_run,
        "changed": new_hash != old_hash,
        "tenant_count": len(tenant_dicts),
        "bridge_hash": new_hash,
    }

    if dry_run:
        result["message"] = "Validation OK (dry run, no write)"
        return result

    backup = bridge_path.with_suffix(f".json.bak.{secrets.token_hex(4)}")
    backup.write_text(bridge_path.read_text(encoding="utf-8-sig"), encoding="utf-8")
    os.chmod(backup, 0o600)

    fd, tmp_name = tempfile.mkstemp(dir=bridge_path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
            f.write("\n")
        tmp_path = Path(tmp_name)
        tmp_path.replace(bridge_path)
        os.chmod(bridge_path, 0o600)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise

    # Update sync state for all tenants
    t_result = await session.execute(select(Tenant).options(selectinload(Tenant.sync_state)))
    for tenant in t_result.scalars().all():
        if tenant.sync_state is None:
            tenant.sync_state = TenantSyncState(tenant_pk=tenant.id)
        tenant.sync_state.last_synced_at = datetime.now(timezone.utc)
        tenant.sync_state.bridge_hash = new_hash
        tenant.sync_state.deploy_status = DeployStatus.synced.value

    result["message"] = "bridge.json updated"
    result["backup"] = str(backup)
    return result


def generate_api_token() -> str:
    return secrets.token_hex(32)
