"""Shared application state."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from shop_claim_bridge.adapters.wargm_client import WargmClient
from shop_claim_bridge.config import default_tenant_id_for_migration, resolve_path
from shop_claim_bridge.db import Database
from shop_claim_bridge.models import BridgeConfig, tenant_wargm_enabled
from shop_claim_bridge.tenant_registry import TenantRegistry


class AppState:
    def __init__(self, config: BridgeConfig, base_dir: Path) -> None:
        self.config = config
        self.base_dir = base_dir
        self.registry = TenantRegistry(config, base_dir)
        db_path = resolve_path(base_dir, config.database.path)
        self.db = Database(db_path)
        self._default_tenant_id = default_tenant_id_for_migration(config)
        self._wargm_clients: dict[str, WargmClient] = {}
        self._wargm_sync_locks: dict[str, asyncio.Lock] = {}

    @asynccontextmanager
    async def wargm_sync_lock(self, operation_id: str) -> AsyncIterator[None]:
        lock = self._wargm_sync_locks.setdefault(operation_id, asyncio.Lock())
        await lock.acquire()
        try:
            yield
        finally:
            lock.release()
            if (
                operation_id in self._wargm_sync_locks
                and self._wargm_sync_locks.get(operation_id) is lock
                and not lock.locked()
            ):
                self._wargm_sync_locks.pop(operation_id, None)

    def get_wargm_client(self, tenant_id: str) -> WargmClient | None:
        tenant = self.registry.get_tenant(tenant_id)
        if not tenant or not tenant_wargm_enabled(tenant):
            return None
        if tenant_id not in self._wargm_clients:
            self._wargm_clients[tenant_id] = WargmClient(tenant.wargm, self.config.poll)
        return self._wargm_clients[tenant_id]

    async def close_wargm_clients(self) -> None:
        for client in self._wargm_clients.values():
            await client.close()
        self._wargm_clients.clear()
