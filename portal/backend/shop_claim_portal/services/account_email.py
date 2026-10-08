"""Email availability checks for account flows."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shop_claim_portal.models import User


async def email_taken(session: AsyncSession, email: str, *, exclude_user_id: int | None = None) -> bool:
    q = select(User.id).where(or_(User.email == email, User.pending_email == email))
    if exclude_user_id is not None:
        q = q.where(User.id != exclude_user_id)
    result = await session.execute(q.limit(1))
    return result.scalar_one_or_none() is not None
