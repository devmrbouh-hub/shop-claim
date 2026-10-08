"""Dev-only mock endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from shop_claim_bridge.auth import get_app_state
from shop_claim_bridge.models import MockOperationRequest
from shop_claim_bridge.order_service import OrderService

router = APIRouter(prefix="/dev")


@router.post("/operations/{operation_id}/reset")
async def reset_operation(operation_id: str) -> dict[str, str]:
    app_state = get_app_state()
    if not app_state.config.dev_mode:
        raise HTTPException(status_code=404, detail="Not found")
    svc = OrderService(app_state)
    await svc.reset_mock_to_available(operation_id)
    return {"operation_id": operation_id, "local_status": "available"}


@router.post("/mock-operation")
async def mock_operation(body: MockOperationRequest) -> dict:
    app_state = get_app_state()
    if not app_state.config.dev_mode:
        raise HTTPException(status_code=404, detail="Not found")
    svc = OrderService(app_state)
    return await svc.create_mock(
        body.steam_id,
        body.offer_id,
        body.shop_server_id,
        body.server_id,
    )
