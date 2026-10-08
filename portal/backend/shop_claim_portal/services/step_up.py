"""Step-up authentication (re-verify password)."""

from __future__ import annotations

from fastapi import HTTPException, status

from shop_claim_portal.models import User
from shop_claim_portal.services.password import verify_password

WRONG_CURRENT_PASSWORD = "Неверный текущий пароль"
PASSWORD_NOT_SET = "Пароль ещё не установлен"


def verify_step_up_password(user: User, password: str) -> None:
    if not user.password_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_NOT_SET)
    if not verify_password(user.password_hash, password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=WRONG_CURRENT_PASSWORD)
