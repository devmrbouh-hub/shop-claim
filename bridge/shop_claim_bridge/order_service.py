"""Order lifecycle business rules."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from shop_claim_bridge.models import PendingOrderResponse

if TYPE_CHECKING:
    from shop_claim_bridge.app_state import AppState

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, state: AppState) -> None:
        self.state = state

    def _catalog_for_server(self, server_id: str):
        catalog = self.state.registry.get_catalog_for_server(server_id)
        if not catalog:
            raise HTTPException(status_code=404, detail="Server not found")
        return catalog

    async def list_pending(
        self, server_id: str, steam_id: str
    ) -> list[PendingOrderResponse]:
        gs = self.state.registry.get_server(server_id)
        if not gs:
            raise HTTPException(status_code=404, detail="Server not found")
        catalog = self._catalog_for_server(server_id)
        rows = await self.state.db.list_pending(
            gs.tenant_id, gs.shop_server_id, steam_id
        )
        out: list[PendingOrderResponse] = []
        for row in rows:
            resolved = catalog.resolve_delivery(row["offer_id"])
            if not resolved:
                logger.warning(
                    "unknown_offer operation=%s offer=%s",
                    row["operation_id"],
                    row["offer_id"],
                )
                continue
            if not catalog.applies_to_server(row["offer_id"], gs.shop_server_id):
                continue
            out.append(
                PendingOrderResponse(
                    operation_id=row["operation_id"],
                    offer_id=row["offer_id"],
                    name=resolved["name"],
                    type=resolved["type"],
                    status=row["local_status"],
                    delivery=resolved["delivery"],
                )
            )
        return out

    async def mark_spawned(self, server_id: str, operation_id: str) -> None:
        gs = self.state.registry.get_server(server_id)
        if not gs:
            raise HTTPException(status_code=404, detail="Server not found")
        order = await self.state.db.get_order(operation_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order["tenant_id"] != gs.tenant_id:
            raise HTTPException(status_code=403, detail="Order belongs to another tenant")
        if order["shop_server_id"] != gs.shop_server_id:
            raise HTTPException(status_code=403, detail="Order belongs to another server")
        if order["local_status"] == "done":
            raise HTTPException(status_code=409, detail="Order already delivered")

        catalog = self._catalog_for_server(server_id)
        resolved = catalog.resolve_delivery(order["offer_id"])
        if not resolved:
            raise HTTPException(status_code=422, detail="Offer not in catalog")
        if resolved["type"] != "container":
            raise HTTPException(status_code=422, detail="spawned only for container type")

        result = await self.state.db.transition_status(
            operation_id, "spawned", allowed_from=("available",)
        )
        if result == "already_in_target":
            return
        if result == "not_found":
            raise HTTPException(status_code=404, detail="Order not found")
        if result == "invalid_state":
            raise HTTPException(status_code=409, detail="Invalid order state for spawned")

    async def mark_delivered(self, server_id: str, operation_id: str) -> None:
        gs = self.state.registry.get_server(server_id)
        if not gs:
            raise HTTPException(status_code=404, detail="Server not found")
        order = await self.state.db.get_order(operation_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order["tenant_id"] != gs.tenant_id:
            raise HTTPException(status_code=403, detail="Order belongs to another tenant")
        if order["shop_server_id"] != gs.shop_server_id:
            raise HTTPException(status_code=403, detail="Order belongs to another server")

        if order["local_status"] == "done":
            await self.sync_wargm_if_needed(operation_id)
            return

        catalog = self._catalog_for_server(server_id)
        resolved = catalog.resolve_delivery(order["offer_id"])
        if not resolved:
            raise HTTPException(status_code=422, detail="Offer not in catalog")

        dtype = resolved["type"]
        if dtype == "container":
            allowed_from: tuple[str, ...] = ("spawned",)
            if order["local_status"] != "spawned":
                raise HTTPException(
                    status_code=409,
                    detail="Container must be spawned before delivered",
                )
        elif dtype == "vehicle":
            allowed_from = ("available",)
            if order["local_status"] != "available":
                raise HTTPException(
                    status_code=409,
                    detail="Vehicle delivery requires available state",
                )
        else:
            raise HTTPException(status_code=422, detail="Unsupported delivery type")

        wargm_confirmed = order["source"] == "mock"
        result = await self.state.db.transition_to_done(
            operation_id,
            allowed_from=allowed_from,  # type: ignore[arg-type]
            wargm_confirmed=wargm_confirmed,
        )
        if result == "not_found":
            raise HTTPException(status_code=404, detail="Order not found")
        if result == "invalid_state":
            raise HTTPException(status_code=409, detail="Invalid order state for delivered")

        if not wargm_confirmed and result in ("applied", "already_in_target"):
            await self.sync_wargm_if_needed(operation_id)

    async def sync_wargm_if_needed(self, operation_id: str) -> None:
        async with self.state.wargm_sync_lock(operation_id):
            order = await self.state.db.get_order(operation_id)
            if not order:
                return
            if order["source"] == "mock":
                return
            if order["local_status"] != "done":
                return
            if order["wargm_confirmed"]:
                return

            wargm_client = self.state.get_wargm_client(order["tenant_id"])
            if not wargm_client:
                return

            ok = await wargm_client.operation_success(operation_id)
            if ok:
                await self.state.db.mark_wargm_confirmed(operation_id)
            else:
                logger.warning("wargm operation_success pending retry: %s", operation_id)

    async def reset_mock_to_available(self, operation_id: str) -> None:
        order = await self.state.db.get_order(operation_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order["source"] != "mock":
            raise HTTPException(status_code=403, detail="Only mock orders can be reset")
        if order["local_status"] == "done":
            raise HTTPException(status_code=409, detail="Order already delivered")
        await self.state.db.set_status(operation_id, "available")

    async def create_mock(
        self,
        steam_id: str,
        offer_id: str | int,
        shop_server_id: int,
        server_id: str | None,
    ) -> dict[str, Any]:
        tenant_id = "default"
        if server_id:
            gs = self.state.registry.get_server(server_id)
            if not gs:
                raise HTTPException(status_code=404, detail="Server not found")
            shop_server_id = gs.shop_server_id
            tenant_id = gs.tenant_id
            catalog = self._catalog_for_server(server_id)
        else:
            catalog = None
            for gs in self.state.registry.list_servers():
                if gs.shop_server_id == shop_server_id:
                    tenant_id = gs.tenant_id
                    catalog = self._catalog_for_server(gs.server_id)
                    break
            if catalog is None:
                raise HTTPException(status_code=404, detail="Server not found for shop_server_id")
        has_entry = catalog.get(offer_id) is not None
        operation_id = f"mock-{uuid.uuid4()}"
        try:
            await self.state.db.insert_mock(
                operation_id,
                str(offer_id),
                steam_id,
                shop_server_id,
                tenant_id,
                has_catalog_entry=has_entry,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"operation_id": operation_id, "local_status": "available"}
