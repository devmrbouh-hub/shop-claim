"""Authentication routes."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shop_claim_portal.auth.deps import SessionUser, get_current_user_optional, require_user
from shop_claim_portal.config import get_settings
from shop_claim_portal.db import get_session
from shop_claim_portal.models import InviteToken, TokenPurpose, User, UserRole
from shop_claim_portal.rate_limit import rate_limiter
from shop_claim_portal.schemas import (
    ChangeEmailRequest,
    ChangeEmailResponse,
    ChangePasswordRequest,
    ConfirmEmailChangeRequest,
    ConfirmEmailChangeResponse,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SetPasswordRequest,
    UserOut,
)
from shop_claim_portal.services.account_email import email_taken
from shop_claim_portal.services.action_tokens import create_action_token, find_valid_token, invalidate_tokens
from shop_claim_portal.services.audit import log_admin_action
from shop_claim_portal.services.email import (
    send_email_change_confirm,
    send_email_change_requested_notice,
    send_email_changed_notice,
    send_password_reset_email,
)
from shop_claim_portal.services.jwt_tokens import COOKIE_NAME, create_access_token
from shop_claim_portal.services.password import hash_password, verify_password
from shop_claim_portal.services.step_up import verify_step_up_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

GENERIC_AUTH_ERROR = "Неверный email или пароль"
GENERIC_SET_PASSWORD_ERROR = "Неверный или просроченный код"
WRONG_CURRENT_PASSWORD = "Неверный текущий пароль"
PASSWORD_NOT_SET = "Пароль ещё не установлен"
SAME_PASSWORD = "Новый пароль должен отличаться от текущего"
SAME_EMAIL = "Новый email совпадает с текущим"
EMAIL_TAKEN = "Email уже используется"
SMTP_UNAVAILABLE = "Не удалось отправить письмо. Попробуйте позже или обратитесь к оператору."


def _set_session_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    token = create_access_token(
        {
            "sub": str(user.id),
            "role": user.role,
            "tv": user.token_version,
        }
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.jwt_ttl_hours * 3600,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )


def _user_out(user: User) -> UserOut:
    tenant_slug = user.tenant.tenant_id if user.tenant else None
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        tenant_id=tenant_slug,
        is_active=user.is_active,
        pending_email=user.pending_email,
    )


def _verify_current_password(user: User, password: str) -> None:
    verify_step_up_password(user, password)


def _check_dual_rate_limit(
    request: Request,
    *,
    ip_prefix: str,
    user_prefix: str,
    user_id: int,
    ip_max: int,
    user_max: int,
    error_detail: str,
) -> None:
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"{ip_prefix}:ip:{ip}", max_events=ip_max, window_sec=60):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_detail)
    if not rate_limiter.allow(f"{user_prefix}:user:{user_id}", max_events=user_max, window_sec=60):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_detail)


async def _load_user(session: AsyncSession, user_id: int) -> User:
    result = await session.execute(
        select(User).where(User.id == user_id).options(selectinload(User.tenant))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"login:{ip}", max_events=30, window_sec=60):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=GENERIC_AUTH_ERROR)

    result = await session.execute(
        select(User).where(User.email == body.email).options(selectinload(User.tenant))
    )
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(user.password_hash, body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_ERROR)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_ERROR)

    user.token_version += 1
    await session.commit()
    await session.refresh(user)
    _set_session_cookie(response, user)
    return _user_out(user)


@router.post("/logout")
async def logout(
    response: Response,
    user: SessionUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    result = await session.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one()
    db_user.token_version += 1
    await session.commit()
    _clear_session_cookie(response)
    return {"status": "ok"}


@router.post("/set-password")
async def set_password(
    body: SetPasswordRequest,
    response: Response,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"setpw:{ip}", max_events=20, window_sec=60):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=GENERIC_SET_PASSWORD_ERROR)

    invite = await find_valid_token(session, code=body.code, purpose=TokenPurpose.invite.value)
    if not invite:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_SET_PASSWORD_ERROR)

    user_result = await session.execute(
        select(User).where(User.id == invite.user_id).options(selectinload(User.tenant))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_SET_PASSWORD_ERROR)

    now = datetime.now(timezone.utc)
    invite.used_at = now
    user.password_hash = hash_password(body.password)
    user.is_active = True
    user.token_version += 1
    await session.commit()
    await session.refresh(user)

    _set_session_cookie(response, user)
    return _user_out(user)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    request: Request,
    session_user: SessionUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    _check_dual_rate_limit(
        request,
        ip_prefix="changepw",
        user_prefix="changepw",
        user_id=session_user.id,
        ip_max=20,
        user_max=10,
        error_detail=WRONG_CURRENT_PASSWORD,
    )

    user = await _load_user(session, session_user.id)
    _verify_current_password(user, body.current_password)
    if body.new_password == body.current_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=SAME_PASSWORD)

    user.password_hash = hash_password(body.new_password)
    user.token_version += 1

    await log_admin_action(
        session,
        actor_user_id=user.id,
        action="password_changed",
        target_type="user",
        target_id=str(user.id),
        meta={"role": user.role},
    )

    await session.commit()
    await session.refresh(user)
    _set_session_cookie(response, user)
    return _user_out(user)


@router.post("/change-email", response_model=ChangeEmailResponse)
async def change_email(
    body: ChangeEmailRequest,
    request: Request,
    session_user: SessionUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ChangeEmailResponse:
    _check_dual_rate_limit(
        request,
        ip_prefix="changeemail",
        user_prefix="changeemail",
        user_id=session_user.id,
        ip_max=10,
        user_max=5,
        error_detail=WRONG_CURRENT_PASSWORD,
    )

    user = await _load_user(session, session_user.id)
    _verify_current_password(user, body.current_password)

    new_email = body.new_email
    if new_email == user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=SAME_EMAIL)
    if new_email == user.pending_email:
        pass  # idempotent re-request
    elif await email_taken(session, new_email, exclude_user_id=user.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN)

    old_email = user.email
    code, _token = await create_action_token(
        session, user_id=user.id, purpose=TokenPurpose.email_change.value
    )
    user.pending_email = new_email

    sent = send_email_change_confirm(to_email=new_email, code=code)
    if not sent:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=SMTP_UNAVAILABLE)

    send_email_change_requested_notice(to_email=old_email, new_email=new_email)

    await session.commit()
    return ChangeEmailResponse(
        status="ok",
        email=user.email,
        pending_email=new_email,
        email_sent=True,
    )


@router.post("/confirm-email-change", response_model=ConfirmEmailChangeResponse)
async def confirm_email_change(
    body: ConfirmEmailChangeRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ConfirmEmailChangeResponse:
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"confirmemail:{ip}", max_events=20, window_sec=60):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=GENERIC_SET_PASSWORD_ERROR)

    invite = await find_valid_token(session, code=body.code, purpose=TokenPurpose.email_change.value)
    if not invite:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_SET_PASSWORD_ERROR)

    user_result = await session.execute(
        select(User).where(User.id == invite.user_id).options(selectinload(User.tenant))
    )
    user = user_result.scalar_one_or_none()
    if not user or not user.pending_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_SET_PASSWORD_ERROR)

    new_email = user.pending_email
    if await email_taken(session, new_email, exclude_user_id=user.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN)

    old_email = user.email
    now = datetime.now(timezone.utc)
    invite.used_at = now
    user.email = new_email
    user.pending_email = None
    user.token_version += 1

    await log_admin_action(
        session,
        actor_user_id=user.id,
        action="email_changed",
        target_type="user",
        target_id=str(user.id),
        meta={"old_email": old_email, "new_email": new_email, "role": user.role},
    )

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN) from None

    send_email_changed_notice(to_email=old_email, new_email=new_email)
    return ConfirmEmailChangeResponse(status="ok", email=new_email)


@router.post("/cancel-email-change")
async def cancel_email_change(
    session_user: SessionUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    user = await _load_user(session, session_user.id)
    if not user.pending_email:
        return {"status": "ok"}
    await invalidate_tokens(session, user_id=user.id, purpose=TokenPurpose.email_change.value)
    user.pending_email = None
    await session.commit()
    return {"status": "ok"}


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if body.website:
        return {"status": "ok"}

    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"forgotpw:ip:{ip}", max_events=5, window_sec=60):
        return {"status": "ok"}

    email_key = hashlib.sha256(body.email.encode()).hexdigest()[:16]
    if not rate_limiter.allow(f"forgotpw:email:{email_key}", max_events=3, window_sec=3600):
        return {"status": "ok"}

    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not user.password_hash:
        return {"status": "ok"}

    code, _token = await create_action_token(
        session, user_id=user.id, purpose=TokenPurpose.password_reset.value
    )
    await session.commit()
    send_password_reset_email(to_email=user.email, code=code)
    return {"status": "ok"}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"resetpw:{ip}", max_events=20, window_sec=60):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=GENERIC_SET_PASSWORD_ERROR)

    invite = await find_valid_token(session, code=body.code, purpose=TokenPurpose.password_reset.value)
    if not invite:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_SET_PASSWORD_ERROR)

    user_result = await session.execute(select(User).where(User.id == invite.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENERIC_SET_PASSWORD_ERROR)

    if user.password_hash and verify_password(user.password_hash, body.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=SAME_PASSWORD)

    now = datetime.now(timezone.utc)
    invite.used_at = now
    user.password_hash = hash_password(body.password)
    user.token_version += 1

    await log_admin_action(
        session,
        actor_user_id=user.id,
        action="password_reset",
        target_type="user",
        target_id=str(user.id),
        meta={"role": user.role},
    )

    await session.commit()
    return {"status": "ok"}


@router.get("/me")
async def me(
    user: SessionUser | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> UserOut | None:
    if not user:
        return None
    db_user = await _load_user(session, user.id)
    return UserOut(
        id=db_user.id,
        email=db_user.email,
        role=db_user.role,
        tenant_id=user.tenant_slug,
        is_active=True,
        pending_email=db_user.pending_email,
    )
