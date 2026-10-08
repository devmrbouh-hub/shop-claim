"""Bootstrap provider admin on first start."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shop_claim_portal.config import Settings
from shop_claim_portal.models import User, UserRole
from shop_claim_portal.services.password import hash_password
from shop_claim_portal.services.validation import validate_email_no_crlf


async def ensure_bootstrap_admin(session: AsyncSession, settings: Settings) -> None:
    result = await session.execute(select(User).where(User.role == UserRole.provider.value))
    if result.scalar_one_or_none():
        return
    email = settings.bootstrap_admin_email.strip()
    password = settings.bootstrap_admin_password
    if not email or not password:
        return
    email = validate_email_no_crlf(email)
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=UserRole.provider.value,
        is_active=True,
    )
    session.add(user)
    await session.commit()
