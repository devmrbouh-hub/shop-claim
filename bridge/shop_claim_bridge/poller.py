"""Background WarGM poller and sync retry."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from shop_claim_bridge.models import TenantConfig
from shop_claim_bridge.order_service import OrderService

if TYPE_CHECKING:
    from shop_claim_bridge.app_state import AppState

logger = logging.getLogger(__name__)


class Poller:
    def __init__(self, state: AppState) -> None:
        self.state = state
        self._poll_task: asyncio.Task | None = None
        self._sync_task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._stop.clear()
        pollable = self.state.registry.list_pollable_tenants()
        if pollable:
            self._poll_task = asyncio.create_task(self._poll_loop())
            self._sync_task = asyncio.create_task(self._sync_loop())
            logger.info(
                "WarGM poller started for tenants: %s",
                ", ".join(t.tenant_id for t in pollable),
            )
        else:
            logger.info("WarGM poller disabled (no pollable tenants)")

    async def stop(self) -> None:
        self._stop.set()
        for task in (self._poll_task, self._sync_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def _poll_loop(self) -> None:
        interval = self.state.config.poll.interval_sec
        while not self._stop.is_set():
            for tenant in self.state.registry.list_pollable_tenants():
                try:
                    await self._poll_once(tenant)
                except Exception:
                    logger.exception("Poll failed tenant=%s", tenant.tenant_id)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    async def _sync_loop(self) -> None:
        interval = self.state.config.poll.sync_retry_sec
        while not self._stop.is_set():
            for tenant in self.state.registry.list_pollable_tenants():
                try:
                    await self._sync_once(tenant)
                except Exception:
                    logger.exception("WarGM sync failed tenant=%s", tenant.tenant_id)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    async def _poll_once(self, tenant: TenantConfig) -> None:
        client = self.state.get_wargm_client(tenant.tenant_id)
        if not client:
            return
        allowed_servers = self.state.registry.shop_server_ids_for(tenant.tenant_id)
        catalog = self.state.registry.get_catalog(tenant)
        operations = await client.fetch_all_pending_operations()
        for op in operations:
            shop_server_id = op["shop_server_id"]
            if shop_server_id not in allowed_servers:
                logger.debug(
                    "tenant=%s skip operation=%s shop_server_id=%s not in config",
                    tenant.tenant_id,
                    op["operation_id"],
                    shop_server_id,
                )
                continue
            offer_id = op["offer_id"]
            has_catalog = catalog.get(offer_id) is not None
            if not has_catalog:
                logger.warning(
                    "tenant=%s unmapped offer operation=%s offer=%s",
                    tenant.tenant_id,
                    op["operation_id"],
                    offer_id,
                )
            await self.state.db.upsert_from_wargm(
                op["operation_id"],
                offer_id,
                op["steam_id"],
                shop_server_id,
                tenant.tenant_id,
                has_catalog_entry=has_catalog,
            )

    async def _sync_once(self, tenant: TenantConfig) -> None:
        svc = OrderService(self.state)
        pending = await self.state.db.list_wargm_sync_pending(tenant.tenant_id)
        for order in pending:
            await svc.sync_wargm_if_needed(order["operation_id"])
            refreshed = await self.state.db.get_order(order["operation_id"])
            if refreshed and refreshed["wargm_confirmed"]:
                logger.info(
                    "tenant=%s WarGM confirmed operation %s",
                    tenant.tenant_id,
                    order["operation_id"],
                )
