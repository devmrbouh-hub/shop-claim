"""Load bridge.json and resolve relative paths."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from shop_claim_bridge.models import (
    BridgeConfig,
    tenant_subscription_active,
    tenant_wargm_enabled,
)


def find_config_path() -> Path:
    env = os.environ.get("SHOP_CLAIM_BRIDGE_CONFIG") or os.environ.get("WARGM_BRIDGE_CONFIG")
    if env:
        return Path(env).resolve()
    cwd = Path.cwd() / "bridge.json"
    if cwd.is_file():
        return cwd.resolve()
    # repo layout: bridge/ vs services/shop-claim/
    parent = Path(__file__).resolve().parents[2]
    candidate = parent.parent / "config" / "bridge.example.json"
    if candidate.is_file():
        return candidate.resolve()
    return cwd.resolve()


def _default_vehicle_profiles_path(offers_path: str) -> str:
    parent = Path(offers_path).parent
    return str(parent / "vehicle_profiles.yaml")


def normalize_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert legacy single-tenant bridge.json to tenants[] runtime shape."""
    tenants = raw.get("tenants")
    if tenants:
        return raw

    wargm = raw.get("wargm")
    servers = raw.get("servers") or []
    if not wargm:
        raise ValueError("bridge.json must contain tenants[] or legacy wargm + servers")

    catalog = raw.get("catalog") or {}
    offers_path = catalog.get("path", "catalog/offers.yaml")
    out = {
        k: v
        for k, v in raw.items()
        if k not in ("wargm", "servers", "catalog")
    }
    out["tenants"] = [
        {
            "tenant_id": "default",
            "enabled": True,
            "subscription_until": "2099-12-31",
            "wargm": wargm,
            "catalog": {
                "offers_path": offers_path,
                "vehicle_profiles_path": _default_vehicle_profiles_path(offers_path),
            },
            "servers": servers,
        }
    ]
    return out


def validate_config(config: BridgeConfig) -> None:
    if not config.tenants:
        raise ValueError("bridge.json: tenants[] must not be empty")

    tenant_ids: set[str] = set()
    shop_ids: set[str] = set()
    api_tokens: set[str] = set()
    server_ids: set[str] = set()

    for tenant in config.tenants:
        if tenant.tenant_id in tenant_ids:
            raise ValueError(f"Duplicate tenant_id: {tenant.tenant_id}")
        tenant_ids.add(tenant.tenant_id)

        if tenant.enabled and tenant_wargm_enabled(tenant):
            if tenant.wargm.shop_id in shop_ids:
                raise ValueError(
                    f"Duplicate wargm shop_id {tenant.wargm.shop_id!r} "
                    f"(tenant {tenant.tenant_id})"
                )
            shop_ids.add(tenant.wargm.shop_id)

        for server in tenant.servers:
            if not server.enabled:
                continue
            if server.server_id in server_ids:
                raise ValueError(f"Duplicate server_id: {server.server_id}")
            server_ids.add(server.server_id)

            if server.api_token in api_tokens:
                raise ValueError(f"Duplicate api_token for server {server.server_id}")
            api_tokens.add(server.api_token)


def default_tenant_id_for_migration(config: BridgeConfig) -> str:
    """Backfill tenant_id for legacy orders rows during schema migration."""
    if not config.tenants:
        raise ValueError("bridge.json: tenants[] must not be empty")
    if len(config.tenants) > 1:
        import logging

        logging.getLogger(__name__).warning(
            "Multi-tenant config: legacy orders without tenant_id will backfill "
            "to %s; run UPDATE if needed",
            config.tenants[0].tenant_id,
        )
    return config.tenants[0].tenant_id


def load_config(path: Path | None = None) -> tuple[BridgeConfig, Path]:
    config_path = path or find_config_path()
    if not config_path.is_file():
        raise FileNotFoundError(f"Config not found: {config_path}")
    raw = json.loads(config_path.read_text(encoding="utf-8-sig"))
    normalized = normalize_config(raw)
    config = BridgeConfig.model_validate(normalized)
    validate_config(config)
    return config, config_path.parent.resolve()


def resolve_path(base_dir: Path, relative: str) -> Path:
    p = Path(relative)
    if p.is_absolute():
        return p
    return (base_dir / p).resolve()


def tenant_is_pollable(tenant: Any) -> bool:
    from shop_claim_bridge.models import TenantConfig

    assert isinstance(tenant, TenantConfig)
    return (
        tenant.enabled
        and tenant_subscription_active(tenant)
        and tenant_wargm_enabled(tenant)
    )
