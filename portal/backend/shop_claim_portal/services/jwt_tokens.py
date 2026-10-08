"""JWT session cookies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from shop_claim_portal.config import get_settings

ALGORITHM = "HS256"
COOKIE_NAME = "shop_claim_portal_session"


def create_access_token(payload: dict[str, Any]) -> str:
    settings = get_settings()
    data = payload.copy()
    data["exp"] = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_ttl_hours)
    return jwt.encode(data, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
