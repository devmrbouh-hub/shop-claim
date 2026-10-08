"""Create and invalidate purpose-scoped action tokens."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shop_claim_portal.config import get_settings
from shop_claim_portal.models import InviteToken, TokenPurpose


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def ttl_hours_for(purpose: str) -> int:
    settings = get_settings()
    if purpose == TokenPurpose.invite.value:
        return settings.invite_ttl_hours
    return settings.action_token_ttl_hours


async def invalidate_tokens(
    session: AsyncSession,
    *,
    user_id: int,
    purpose: str,
) -> None:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(InviteToken).where(
            InviteToken.user_id == user_id,
            InviteToken.purpose == purpose,
            InviteToken.used_at.is_(None),
        )
    )
    for token in result.scalars().all():
        token.used_at = now


async def create_action_token(
    session: AsyncSession,
    *,
    user_id: int,
    purpose: str,
) -> tuple[str, InviteToken]:
    await invalidate_tokens(session, user_id=user_id, purpose=purpose)
    code = secrets.token_urlsafe(32)
    token = InviteToken(
        user_id=user_id,
        purpose=purpose,
        token_hash=_hash_code(code),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours_for(purpose)),
    )
    session.add(token)
    return code, token


async def find_valid_token(
    session: AsyncSession,
    *,
    code: str,
    purpose: str,
) -> InviteToken | None:
    code_hash = _hash_code(code)
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(InviteToken).where(
            InviteToken.token_hash == code_hash,
            InviteToken.purpose == purpose,
            InviteToken.used_at.is_(None),
            InviteToken.expires_at > now,
        )
    )
    return result.scalar_one_or_none()
