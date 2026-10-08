"""Scrub secrets from ticket/log text."""

from __future__ import annotations

import re

API_TOKEN_RE = re.compile(r"api_token[=:][^\s&\"']+", re.IGNORECASE)


def scrub_secrets(text: str) -> str:
    return API_TOKEN_RE.sub("api_token=***", text)
