"""SQLite persistence for orders."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import aiosqlite

from shop_claim_bridge.models import LocalStatus

logger = logging.getLogger(__name__)

TransitionResult = Literal["applied", "already_in_target", "not_found", "invalid_state"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    operation_id TEXT PRIMARY KEY,
    offer_id TEXT NOT NULL,
    steam_id TEXT NOT NULL,
    shop_server_id INTEGER NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    local_status TEXT NOT NULL,
    source TEXT NOT NULL,
    wargm_confirmed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_orders_pending
    ON orders (tenant_id, shop_server_id, steam_id, local_status);
CREATE INDEX IF NOT EXISTS idx_orders_wargm_sync
    ON orders (wargm_confirmed, local_status, source, tenant_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self, default_tenant_id: str = "default") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._migrate_schema(default_tenant_id)
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def _migrate_schema(self, default_tenant_id: str) -> None:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='orders'"
        ) as cur:
            if not await cur.fetchone():
                return
        async with self._conn.execute("PRAGMA table_info(orders)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
        if "wargm_server_id" in cols and "shop_server_id" not in cols:
            await self._conn.execute(
                "ALTER TABLE orders RENAME COLUMN wargm_server_id TO shop_server_id"
            )
            await self._conn.commit()
            async with self._conn.execute("PRAGMA table_info(orders)") as cur:
                cols = {row[1] for row in await cur.fetchall()}
        if "tenant_id" not in cols:
            await self._conn.execute("ALTER TABLE orders ADD COLUMN tenant_id TEXT")
            await self._conn.execute(
                "UPDATE orders SET tenant_id = ? WHERE tenant_id IS NULL",
                (default_tenant_id,),
            )
            await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database not connected")
        return self._conn

    async def upsert_from_wargm(
        self,
        operation_id: str,
        offer_id: str,
        steam_id: str,
        shop_server_id: int,
        tenant_id: str,
        *,
        has_catalog_entry: bool,
    ) -> None:
        existing = await self.get_order(operation_id)
        now = _now()
        if existing is None:
            status: LocalStatus = "available" if has_catalog_entry else "unmapped"
            await self.conn.execute(
                """
                INSERT INTO orders (
                    operation_id, offer_id, steam_id, shop_server_id, tenant_id,
                    local_status, source, wargm_confirmed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'wargm', 0, ?, ?)
                """,
                (
                    operation_id,
                    offer_id,
                    steam_id,
                    shop_server_id,
                    tenant_id,
                    status,
                    now,
                    now,
                ),
            )
            await self.conn.commit()
            return
        if existing["tenant_id"] != tenant_id:
            logger.error(
                "operation_id=%s already owned by tenant=%s, skip upsert for tenant=%s",
                operation_id,
                existing["tenant_id"],
                tenant_id,
            )
            return
        if existing["local_status"] != "available":
            return
        status = "available" if has_catalog_entry else "unmapped"
        await self.conn.execute(
            """
            UPDATE orders SET offer_id=?, steam_id=?, shop_server_id=?,
                local_status=?, updated_at=?
            WHERE operation_id=? AND local_status='available'
            """,
            (offer_id, steam_id, shop_server_id, status, now, operation_id),
        )
        await self.conn.commit()

    async def insert_mock(
        self,
        operation_id: str,
        offer_id: str,
        steam_id: str,
        shop_server_id: int,
        tenant_id: str,
        *,
        has_catalog_entry: bool,
    ) -> None:
        if not has_catalog_entry:
            raise ValueError(f"Unknown offer_id in catalog: {offer_id}")
        now = _now()
        await self.conn.execute(
            """
            INSERT INTO orders (
                operation_id, offer_id, steam_id, shop_server_id, tenant_id,
                local_status, source, wargm_confirmed, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'available', 'mock', 1, ?, ?)
            """,
            (
                operation_id,
                str(offer_id),
                steam_id,
                shop_server_id,
                tenant_id,
                now,
                now,
            ),
        )
        await self.conn.commit()

    async def get_order(self, operation_id: str) -> dict[str, Any] | None:
        async with self.conn.execute(
            "SELECT * FROM orders WHERE operation_id = ?", (operation_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def list_pending(
        self, tenant_id: str, shop_server_id: int, steam_id: str
    ) -> list[dict[str, Any]]:
        async with self.conn.execute(
            """
            SELECT * FROM orders
            WHERE tenant_id = ? AND shop_server_id = ? AND steam_id = ?
              AND local_status IN ('available', 'spawned')
            ORDER BY created_at ASC
            """,
            (tenant_id, shop_server_id, steam_id),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def set_status(
        self,
        operation_id: str,
        local_status: LocalStatus,
        *,
        wargm_confirmed: bool | None = None,
    ) -> bool:
        now = _now()
        if wargm_confirmed is None:
            await self.conn.execute(
                "UPDATE orders SET local_status=?, updated_at=? WHERE operation_id=?",
                (local_status, now, operation_id),
            )
        else:
            await self.conn.execute(
                """
                UPDATE orders SET local_status=?, wargm_confirmed=?, updated_at=?
                WHERE operation_id=?
                """,
                (local_status, 1 if wargm_confirmed else 0, now, operation_id),
            )
        await self.conn.commit()
        async with self.conn.execute("SELECT changes()") as cur:
            row = await cur.fetchone()
            return bool(row and row[0] > 0)

    async def _classify_transition(
        self,
        operation_id: str,
        target: LocalStatus,
    ) -> TransitionResult:
        order = await self.get_order(operation_id)
        if order is None:
            return "not_found"
        if order["local_status"] == target:
            return "already_in_target"
        return "invalid_state"

    async def transition_status(
        self,
        operation_id: str,
        to: LocalStatus,
        *,
        allowed_from: tuple[LocalStatus, ...],
    ) -> TransitionResult:
        if not allowed_from:
            raise ValueError("allowed_from required")
        now = _now()
        placeholders = ",".join("?" for _ in allowed_from)
        await self.conn.execute(
            f"""
            UPDATE orders SET local_status=?, updated_at=?
            WHERE operation_id=? AND local_status IN ({placeholders})
            """,
            (to, now, operation_id, *allowed_from),
        )
        await self.conn.commit()
        async with self.conn.execute("SELECT changes()") as cur:
            row = await cur.fetchone()
            if row and row[0] > 0:
                return "applied"
        return await self._classify_transition(operation_id, to)

    async def transition_to_done(
        self,
        operation_id: str,
        *,
        allowed_from: tuple[LocalStatus, ...],
        wargm_confirmed: bool,
    ) -> TransitionResult:
        if not allowed_from:
            raise ValueError("allowed_from required")
        now = _now()
        placeholders = ",".join("?" for _ in allowed_from)
        confirmed = 1 if wargm_confirmed else 0
        await self.conn.execute(
            f"""
            UPDATE orders SET local_status='done', wargm_confirmed=?, updated_at=?
            WHERE operation_id=? AND local_status IN ({placeholders})
            """,
            (confirmed, now, operation_id, *allowed_from),
        )
        await self.conn.commit()
        async with self.conn.execute("SELECT changes()") as cur:
            row = await cur.fetchone()
            if row and row[0] > 0:
                return "applied"
        return await self._classify_transition(operation_id, "done")

    async def list_wargm_sync_pending(self, tenant_id: str) -> list[dict[str, Any]]:
        async with self.conn.execute(
            """
            SELECT * FROM orders
            WHERE tenant_id = ? AND source = 'wargm'
              AND local_status = 'done' AND wargm_confirmed = 0
            ORDER BY updated_at ASC
            """,
            (tenant_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def mark_wargm_confirmed(self, operation_id: str) -> bool:
        now = _now()
        await self.conn.execute(
            """
            UPDATE orders SET wargm_confirmed=1, updated_at=?
            WHERE operation_id=? AND local_status='done' AND wargm_confirmed=0
            """,
            (now, operation_id),
        )
        await self.conn.commit()
        async with self.conn.execute("SELECT changes()") as cur:
            row = await cur.fetchone()
            return bool(row and row[0] > 0)
