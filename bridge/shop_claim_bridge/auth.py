"""Bearer token authentication."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query

from shop_claim_bridge.app_state import AppState
from shop_claim_bridge.models import GameServerConfig


def get_app_state() -> AppState:
    from shop_claim_bridge.main import state

    if state is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return state


def _resolve_api_token(
    authorization: str | None,
    api_token: str | None,
) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    if api_token and api_token.strip():
        return api_token.strip()
    return None


def require_server_auth(
    server_id: str,
    authorization: Annotated[str | None, Header()] = None,
    api_token: Annotated[str | None, Query(alias="api_token")] = None,
    app_state: AppState = Depends(get_app_state),
) -> GameServerConfig:
    token = _resolve_api_token(authorization, api_token)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    resolved = app_state.registry.get_by_token(token)
    if not resolved:
        raise HTTPException(status_code=401, detail="Invalid token")
    tenant, gs = resolved
    if gs.server_id != server_id:
        raise HTTPException(status_code=403, detail="Token does not match server_id")
    if not tenant.enabled:
        raise HTTPException(status_code=403, detail="Tenant disabled")
    if date.today() > tenant.subscription_until:
        raise HTTPException(status_code=403, detail="Subscription expired")
    return gs
