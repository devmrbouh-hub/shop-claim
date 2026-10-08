"""Fernet encryption for secrets at rest."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from shop_claim_portal.config import get_settings


def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.fernet_key.strip()
    if not key:
        # Dev-only derived key from jwt_secret
        digest = hashlib.sha256(settings.jwt_secret.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    elif len(key) != 44:
        digest = hashlib.sha256(key.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def mask_secret(value: str, visible: int = 4) -> str:
    if len(value) <= visible:
        return "****"
    return f"****…{value[-visible:]}"
