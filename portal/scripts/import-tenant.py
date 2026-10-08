"""Import tenant from bridge.json into Portal DB (one-way)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

# Run from repo: py -3.14 portal/scripts/import-tenant.py --bridge path --tenant demo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select

from shop_claim_portal.config import Settings, get_settings
from shop_claim_portal.db import create_tables, get_session, init_db
from shop_claim_portal.models import DeployStatus, GameServer, Tenant, TenantSyncState, User, UserRole
from shop_claim_portal.services.crypto import encrypt_secret


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge", required=True, help="Path to bridge.json")
    parser.add_argument("--tenant", required=True, help="tenant_id slug to import")
    parser.add_argument("--db", default="data/portal.db")
    args = parser.parse_args()

    raw = json.loads(Path(args.bridge).read_text(encoding="utf-8-sig"))
    tenant_raw = next((t for t in raw.get("tenants", []) if t["tenant_id"] == args.tenant), None)
    if not tenant_raw:
        raise SystemExit(f"tenant {args.tenant} not in bridge.json")

    import os

    os.environ["PORTAL_DATABASE_PATH"] = args.db
    get_settings.cache_clear()
    settings = Settings(database_path=args.db)
    init_db(settings, Path.cwd())
    await create_tables()

    async for session in get_session():
        existing = await session.execute(select(Tenant).where(Tenant.tenant_id == args.tenant))
        if existing.scalar_one_or_none():
            print("Tenant already in DB; skip")
            return

        wargm = tenant_raw["wargm"]
        catalog = tenant_raw.get("catalog", {})
        allowed_ips = tenant_raw.get("allowed_egress_ips")
        allowed_json = json.dumps(allowed_ips) if allowed_ips else None
        tenant = Tenant(
            tenant_id=args.tenant,
            enabled=tenant_raw.get("enabled", True),
            subscription_until=date.fromisoformat(tenant_raw["subscription_until"]),
            wargm_shop_id=str(wargm["shop_id"]),
            wargm_api_key_enc=encrypt_secret(wargm["api_key"]),
            wargm_api_base=wargm.get("api_base", "https://api.wargm.ru/v1.1/shop"),
            catalog_offers_path=catalog.get("offers_path", f"tenants/{args.tenant}/offers.yaml"),
            catalog_vehicle_profiles_path=catalog.get(
                "vehicle_profiles_path", f"tenants/{args.tenant}/vehicle_profiles.yaml"
            ),
            allowed_egress_ips_json=allowed_json,
            theme_prefix=tenant_raw.get("theme_prefix"),
        )
        session.add(tenant)
        await session.flush()
        tenant.sync_state = TenantSyncState(tenant_pk=tenant.id, deploy_status=DeployStatus.synced.value)

        for s in tenant_raw.get("servers", []):
            session.add(
                GameServer(
                    tenant_pk=tenant.id,
                    server_id=s["server_id"],
                    shop_server_id=int(s["shop_server_id"]),
                    api_token_enc=encrypt_secret(s["api_token"]),
                    enabled=s.get("enabled", True),
                    catalog_path=s.get("catalog_path") or tenant.catalog_offers_path,
                )
            )
        await session.commit()
        print(f"Imported tenant {args.tenant} with {len(tenant_raw.get('servers', []))} servers")
        break


if __name__ == "__main__":
    asyncio.run(main())
