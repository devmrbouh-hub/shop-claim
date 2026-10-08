"""Audit logging for admin actions."""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from shop_claim_portal.models import AdminAuditLog


async def log_admin_action(
    session: AsyncSession,
    *,
    actor_user_id: int,
    action: str,
    target_type: str,
    target_id: str,
    meta: dict | None = None,
) -> None:
    entry = AdminAuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        meta_json=json.dumps(meta or {}, ensure_ascii=False),
    )
    session.add(entry)
