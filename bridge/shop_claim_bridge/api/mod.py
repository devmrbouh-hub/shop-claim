"""REST API for DayZ server mod."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from shop_claim_bridge.auth import require_server_auth
from shop_claim_bridge.models import GameServerConfig, PendingOrderResponse
from shop_claim_bridge.order_service import OrderService
from shop_claim_bridge.auth import get_app_state

router = APIRouter(prefix="/api/v1")


@router.get(
    "/servers/{server_id}/players/{steam_id}/pending",
    response_model=list[PendingOrderResponse],
)
async def get_pending(
    server_id: str,
    steam_id: str,
    _gs: GameServerConfig = Depends(require_server_auth),
) -> list[PendingOrderResponse]:
    svc = OrderService(get_app_state())
    return await svc.list_pending(server_id, steam_id)


@router.post("/servers/{server_id}/operations/{operation_id}/spawned")
async def post_spawned(
    server_id: str,
    operation_id: str,
    _gs: GameServerConfig = Depends(require_server_auth),
) -> dict[str, str]:
    svc = OrderService(get_app_state())
    await svc.mark_spawned(server_id, operation_id)
    return {"status": "spawned"}


@router.post("/servers/{server_id}/operations/{operation_id}/delivered")
async def post_delivered(
    server_id: str,
    operation_id: str,
    _gs: GameServerConfig = Depends(require_server_auth),
) -> dict[str, str]:
    svc = OrderService(get_app_state())
    await svc.mark_delivered(server_id, operation_id)
    return {"status": "delivered"}
