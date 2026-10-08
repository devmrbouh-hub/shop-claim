"""FastAPI application entry."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from shop_claim_bridge.middleware import ApiRateLimitMiddleware, HealthCorsMiddleware
from shop_claim_bridge.api import admin as admin_api
from shop_claim_bridge.api import dev as dev_api
from shop_claim_bridge.api import mod as mod_api
from shop_claim_bridge.app_state import AppState
from shop_claim_bridge.config import find_config_path, load_config, tenant_is_pollable
from shop_claim_bridge.models import HealthResponse, TenantHealthInfo
from shop_claim_bridge.poller import Poller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

state: AppState | None = None
poller: Poller | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global state, poller
    config_path = find_config_path()
    config, base_dir = load_config(config_path)
    logger.info("Config: %s, base_dir: %s", config_path, base_dir)
    state = AppState(config, base_dir)
    await state.db.connect(state._default_tenant_id)
    poller = Poller(state)
    await poller.start()
    yield
    if poller:
        await poller.stop()
    await state.close_wargm_clients()
    await state.db.close()
    state = None


def create_app() -> FastAPI:
    config, _ = load_config()
    app = FastAPI(title="WarGM Bridge", version="0.1.0", lifespan=lifespan)
    app.add_middleware(ApiRateLimitMiddleware)
    # Outer: status page may read /health only (not /api/v1/*).
    app.add_middleware(HealthCorsMiddleware)
    app.include_router(mod_api.router)
    app.include_router(admin_api.router)
    if config.dev_mode:
        app.include_router(dev_api.router)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        if state is None:
            return HealthResponse(shop_poll=False, dev_mode=False, tenant_count=0)
        tenants_info: list[TenantHealthInfo] = []
        for tenant in state.registry.list_tenants():
            tenants_info.append(
                TenantHealthInfo(
                    tenant_id=tenant.tenant_id,
                    enabled=tenant.enabled,
                    poll=tenant_is_pollable(tenant),
                )
            )
        return HealthResponse(
            shop_poll=any(t.poll for t in tenants_info),
            dev_mode=state.config.dev_mode,
            tenant_count=len(tenants_info),
            tenants=tenants_info,
        )

    return app


def run() -> None:
    config, _ = load_config()
    host = config.server.host
    if host not in ("127.0.0.1", "localhost", "::1"):
        logger.warning("Binding to non-localhost %s — use only on trusted networks", host)
    uvicorn.run(
        "shop_claim_bridge.main:create_app",
        factory=True,
        host=host,
        port=config.server.port,
        log_level="info",
    )


if __name__ == "__main__":
    run()
