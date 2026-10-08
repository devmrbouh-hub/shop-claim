"""Bridge admin API (Portal / provider only — not mod api_token)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query

router = APIRouter(prefix="/admin", tags=["admin"])


def _admin_secret() -> str:
    return os.environ.get("BRIDGE_ADMIN_SECRET", "").strip()


def require_admin_secret(
    x_bridge_admin_secret: str | None = Header(default=None, alias="X-Bridge-Admin-Secret"),
) -> None:
    expected = _admin_secret()
    if not expected:
        raise HTTPException(status_code=503, detail="Admin API not configured")
    if not x_bridge_admin_secret or x_bridge_admin_secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/catalog/reload")
async def catalog_reload(
    tenant_id: str | None = Query(default=None),
    _: None = Depends(require_admin_secret),
) -> dict:
    from shop_claim_bridge.main import state

    if state is None:
        raise HTTPException(status_code=503, detail="Bridge not ready")
    if tenant_id:
        tenant = state.registry.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        reloaded = state.registry.reload_catalog(tenant_id)
    else:
        reloaded = state.registry.reload_all_catalogs()
    return {"status": "ok", "reloaded": reloaded}
