"""HTTP client for Shop Claim API."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import httpx

from shop_claim_bridge.models import PollConfig, WargmShopCredentials

logger = logging.getLogger(__name__)


class WargmApiResponseError(Exception):
    """WarGM returned status=error in JSON envelope."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _pick_field(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return None


def _looks_like_operation_row(val: dict[str, Any]) -> bool:
    return _pick_field(val, "operation_id", "id", "operationId") is not None and _pick_field(
        val, "offer_id", "offerId", "offer"
    ) is not None


def _flatten_operations_dict(inner: dict[str, Any]) -> list[dict[str, Any]]:
    """v1 flat data[id] and v1.1 data[group].operations[]."""
    rows: list[dict[str, Any]] = []
    for _key, val in inner.items():
        if not isinstance(val, dict):
            continue
        nested = val.get("operations")
        if isinstance(nested, list):
            parent_server = _pick_field(val, "server_id", "serverId", "shop_server_id")
            for op in nested:
                if not isinstance(op, dict):
                    continue
                row = dict(op)
                if _pick_field(row, "server_id", "serverId", "shop_server_id") is None:
                    if parent_server is not None:
                        row["server_id"] = parent_server
                    elif str(_key).isdigit():
                        row["server_id"] = int(_key)
                rows.append(row)
            continue
        if _looks_like_operation_row(val):
            rows.append(val)
    return rows


def _response_envelope(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Inner response block for v1 (responce) and v1.1 (response)."""
    envelope = payload.get("response") or payload.get("responce")
    return envelope if isinstance(envelope, dict) else None


def check_wargm_envelope(payload: Any) -> None:
    """Raise WargmApiResponseError if API reports failure (v1 or v1.1)."""
    if not isinstance(payload, dict):
        return
    top = payload.get("status")
    if top == "error":
        envelope = _response_envelope(payload) or {}
        msg = envelope.get("msg") or payload.get("msg") or "WarGM API error"
        raise WargmApiResponseError(str(msg))
    if top == "ok":
        return
    envelope = _response_envelope(payload)
    if envelope and envelope.get("status") == "error":
        msg = envelope.get("msg") or "WarGM API error"
        raise WargmApiResponseError(str(msg))


def _extract_operations_payload(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        envelope = _response_envelope(data)
        if isinstance(envelope, dict):
            inner = envelope.get("data")
            if isinstance(inner, dict):
                flat = _flatten_operations_dict(inner)
                if flat:
                    return flat
                return [v for v in inner.values() if isinstance(v, dict)]
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
        for key in ("operations", "data", "items", "result"):
            val = data.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
            if isinstance(val, dict) and val:
                if all(isinstance(v, dict) for v in val.values()):
                    flat = _flatten_operations_dict(val)
                    if flat:
                        return flat
                    return list(val.values())
        if _looks_like_operation_row(data):
            return [data]
    return []


def parse_operation(row: dict[str, Any]) -> dict[str, Any] | None:
    operation_id = _pick_field(row, "operation_id", "id", "operationId")
    offer_id = _pick_field(row, "offer_id", "offerId", "offer")
    steam_id = _pick_field(row, "steam_id", "steamId", "user_steam_id")
    server_id = _pick_field(row, "server_id", "serverId", "shop_server_id")
    if operation_id is None or offer_id is None or steam_id is None:
        logger.debug("Skip operation row missing fields: %s", row)
        return None
    if server_id is None:
        server_id = 0
    return {
        "operation_id": str(operation_id),
        "offer_id": str(offer_id),
        "steam_id": str(steam_id),
        "shop_server_id": int(server_id),
    }


class WargmClient:
    def __init__(
        self,
        credentials: WargmShopCredentials,
        poll: PollConfig,
    ) -> None:
        self._credentials = credentials
        self._poll = poll
        self._client = httpx.AsyncClient(timeout=30.0, trust_env=False)

    async def close(self) -> None:
        await self._client.aclose()

    def _auth_params(self) -> dict[str, str]:
        w = self._credentials
        return {"client": f"{w.shop_id}:{w.api_key}"}

    async def fetch_operations(self, delivery: str, date_start: date) -> list[dict[str, Any]]:
        base = self._credentials.api_base.rstrip("/")
        params: dict[str, str | int] = {
            **self._auth_params(),
            "status": self._poll.operations_filters.status,
            "delivery": delivery,
            "date_start": date_start.isoformat(),
            "date_end": date.today().isoformat(),
            "numeric_string": "true",
        }
        claimed = self._poll.operations_filters.claimed
        if claimed is not None:
            params["claimed"] = claimed
        url = f"{base}/operations"
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        try:
            payload = resp.json()
            check_wargm_envelope(payload)
        except WargmApiResponseError as exc:
            logger.error("WarGM operations API error delivery=%s: %s", delivery, exc.message)
            return []
        rows = _extract_operations_payload(payload)
        parsed: list[dict[str, Any]] = []
        for row in rows:
            item = parse_operation(row)
            if item:
                parsed.append(item)
        return parsed

    async def fetch_all_pending_operations(self) -> list[dict[str, Any]]:
        lookback = self._poll.lookback_days
        date_start = date.today() - timedelta(days=lookback)
        deliveries = self._poll.operations_filters.delivery
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for delivery in deliveries:
            try:
                batch = await self.fetch_operations(delivery, date_start)
            except httpx.HTTPError as exc:
                logger.error("WarGM operations poll failed delivery=%s: %s", delivery, exc)
                continue
            for op in batch:
                oid = op["operation_id"]
                if oid not in seen:
                    seen.add(oid)
                    result.append(op)
        return result

    async def operation_success(self, operation_id: str) -> bool:
        base = self._credentials.api_base.rstrip("/")
        params = {**self._auth_params(), "operation_id": operation_id}
        url = f"{base}/operation_success"
        resp = await self._client.get(url, params=params)
        if resp.status_code >= 400:
            logger.error(
                "operation_success failed id=%s status=%s body=%s",
                operation_id,
                resp.status_code,
                resp.text[:500],
            )
            return False
        try:
            payload = resp.json()
            check_wargm_envelope(payload)
        except WargmApiResponseError as exc:
            logger.error("operation_success API error id=%s: %s", operation_id, exc.message)
            return False
        return True
