"""WarGM Shop API client for catalog import (Portal only)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

WARGM_API_HOST = "api.wargm.ru"
MAX_IMPORT_IDS = 50
IMPORT_DELAY_SEC = 0.2


class WargmApiError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def _parse_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    top = payload.get("status")
    if top == "error":
        inner = payload.get("response") or payload.get("responce") or {}
        msg = inner.get("msg") if isinstance(inner, dict) else None
        raise WargmApiError(str(msg or "wargm error"))
    if top == "ok":
        envelope = payload.get("response") or payload.get("responce")
    else:
        envelope = payload.get("responce") or payload.get("response")
    if not isinstance(envelope, dict):
        raise WargmApiError("Некорректный ответ wargm")
    if top not in ("ok", "error") and envelope.get("status") != "ok":
        msg = envelope.get("msg") or "wargm error"
        raise WargmApiError(str(msg))
    data = envelope.get("data")
    if not isinstance(data, dict):
        raise WargmApiError("Пустой ответ wargm")
    return data


def wargm_offer_to_draft(data: dict[str, Any], shop_server_ids: set[int] | None = None) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    delivery = str(data.get("delivery", ""))
    if delivery == "admin":
        warnings.append("delivery=admin — автовыдача через API невозможна")
    elif delivery not in ("api", "online", ""):
        warnings.append(f"delivery={delivery} — проверьте настройки wargm")
    if data.get("active") is False:
        warnings.append("Товар неактивен на wargm")
    offer_id = str(data.get("id", ""))
    offer: dict[str, Any] = {
        "type": "container",
        "name": f"Товар {offer_id}",
        "container": "SeaChest",
        "items": [],
    }
    servers = data.get("servers")
    if isinstance(servers, list) and servers:
        offer["shop_server_ids"] = [int(s) for s in servers]
        if shop_server_ids is not None:
            unknown = [s for s in offer["shop_server_ids"] if s not in shop_server_ids]
            if unknown:
                warnings.append(
                    f"Серверы wargm {unknown} не привязаны в ShopClaim"
                )
    return offer, warnings


class PortalWargmClient:
    def __init__(self, shop_id: str, api_key: str, api_base: str) -> None:
        self._shop_id = shop_id
        self._api_key = api_key
        base = api_base.rstrip("/")
        if WARGM_API_HOST not in base:
            raise WargmApiError("Разрешён только api.wargm.ru", 400)
        self._api_base = base
        self._client = httpx.AsyncClient(timeout=30.0, trust_env=False)

    async def close(self) -> None:
        await self._client.aclose()

    def _auth_params(self) -> dict[str, str]:
        return {"client": f"{self._shop_id}:{self._api_key}"}

    async def fetch_offer(self, offer_id: str) -> dict[str, Any]:
        url = f"{self._api_base}/offer"
        params = {**self._auth_params(), "offer_id": offer_id}
        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise WargmApiError(f"wargm недоступен: {exc}") from exc
        return _parse_envelope(resp.json())

    async def fetch_offers_batch(
        self, offer_ids: list[str]
    ) -> list[tuple[str, dict[str, Any] | None, str | None]]:
        if len(offer_ids) > MAX_IMPORT_IDS:
            raise WargmApiError(f"Максимум {MAX_IMPORT_IDS} offer_id за запрос", 400)
        results: list[tuple[str, dict[str, Any] | None, str | None]] = []
        for i, oid in enumerate(offer_ids):
            if i > 0:
                await asyncio.sleep(IMPORT_DELAY_SEC)
            try:
                data = await self.fetch_offer(oid)
                results.append((oid, data, None))
            except WargmApiError as exc:
                results.append((oid, None, str(exc)))
        return results
