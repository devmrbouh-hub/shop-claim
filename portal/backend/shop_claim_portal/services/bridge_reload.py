"""Trigger Bridge catalog reload (localhost admin API)."""

from __future__ import annotations

import httpx

from shop_claim_portal.services.catalog_service import CatalogReloadError


async def reload_bridge_catalog(
    *,
    base_url: str,
    secret: str,
    tenant_id: str,
) -> int:
    if not secret:
        raise CatalogReloadError("Bridge admin secret не настроен")
    url = base_url.rstrip("/") + "/admin/catalog/reload"
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            resp = await client.post(
                url,
                params={"tenant_id": tenant_id},
                headers={"X-Bridge-Admin-Secret": secret},
            )
    except httpx.HTTPError as exc:
        raise CatalogReloadError(f"Bridge недоступен: {exc}") from exc
    if resp.status_code != 200:
        detail = resp.text[:200] if resp.text else resp.status_code
        raise CatalogReloadError(f"Reload failed ({resp.status_code}): {detail}")
    data = resp.json()
    return int(data.get("reloaded", 0))
