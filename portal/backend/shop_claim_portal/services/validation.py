"""Input validation and sanitization."""

from __future__ import annotations

import re

from pydantic import EmailStr, field_validator

CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TENANT_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
SERVER_ID_RE = re.compile(r"^[a-zA-Z0-9_]{3,64}$")
INVITE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")


def strip_control_chars(value: str, allow_newline: bool = False) -> str:
    if allow_newline:
        return "".join(
            c for c in value if c == "\n" or (ord(c) >= 32 and ord(c) != 127)
        )
    return CONTROL_RE.sub("", value)


def validate_email_no_crlf(email: str) -> str:
    normalized = email.strip().lower()
    if "\r" in normalized or "\n" in normalized or "\0" in normalized:
        raise ValueError("Invalid email")
    return normalized


def validate_tenant_slug(tenant_id: str) -> str:
    tid = tenant_id.strip().lower()
    if not TENANT_ID_RE.match(tid):
        raise ValueError("Invalid tenant_id slug")
    return tid


def validate_server_id(server_id: str) -> str:
    sid = server_id.strip()
    if not SERVER_ID_RE.match(sid):
        raise ValueError("Invalid server_id")
    return sid


def validate_invite_token(token: str) -> str:
    t = token.strip()
    if not INVITE_TOKEN_RE.match(t):
        raise ValueError("Invalid token format")
    return t


def contains_forbidden_secret(text: str) -> bool:
    lower = text.lower()
    if "api_token" in lower and ("=" in text or ":" in text):
        return True
    if '"api_token"' in lower:
        return True
    return False
