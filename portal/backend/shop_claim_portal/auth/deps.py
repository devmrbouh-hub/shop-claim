"""Auth dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shop_claim_portal.db import get_session
from shop_claim_portal.models import Tenant, User, UserRole
from shop_claim_portal.services.jwt_tokens import COOKIE_NAME, decode_access_token


@dataclass
class SessionUser:
    id: int
    email: str
    role: str
    tenant_pk: int | None
    tenant_slug: str | None
    token_version: int


async def get_current_user_optional(
    session: AsyncSession = Depends(get_session),
    cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> SessionUser | None:
    if not cookie:
        return None
    payload = decode_access_token(cookie)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    result = await session.execute(
        select(User).where(User.id == int(user_id)).options(selectinload(User.tenant))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    if int(payload.get("tv", 0)) != user.token_version:
        return None
    tenant_slug = user.tenant.tenant_id if user.tenant else None
    return SessionUser(
        id=user.id,
        email=user.email,
        role=user.role,
        tenant_pk=user.tenant_pk,
        tenant_slug=tenant_slug,
        token_version=user.token_version,
    )


async def require_user(
    user: SessionUser | None = Depends(get_current_user_optional),
) -> SessionUser:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


async def require_provider(user: SessionUser = Depends(require_user)) -> SessionUser:
    if user.role != UserRole.provider.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Provider only")
    return user


async def require_subscriber(
    session: AsyncSession = Depends(get_session),
    user: SessionUser = Depends(require_user),
) -> SessionUser:
    if user.role != UserRole.subscriber.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subscriber only")
    if not user.tenant_pk:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant")
    result = await session.execute(select(Tenant).where(Tenant.id == user.tenant_pk))
    tenant = result.scalar_one_or_none()
    if not tenant or not tenant.enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant disabled")
    return user
