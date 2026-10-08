"""FastAPI application."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shop_claim_portal.bootstrap import ensure_bootstrap_admin
from shop_claim_portal.config import get_settings
from shop_claim_portal.db import create_tables, dispose_db, get_session, init_db
from shop_claim_portal.routes import admin, auth, billing, catalog, public, tenant

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db(settings, BASE_DIR)
    await create_tables()
    async for session in get_session():
        await ensure_bootstrap_admin(session, settings)
        break
    logger.info("Portal started (env=%s)", settings.env)
    yield
    await dispose_db()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ShopClaim Portal",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(public.router)
    app.include_router(billing.public_pricing_router)
    app.include_router(auth.router)
    app.include_router(tenant.router)
    app.include_router(billing.tenant_router)
    app.include_router(billing.webhook_router)
    app.include_router(admin.router)
    app.include_router(billing.admin_router)
    app.include_router(catalog.tenant_router)
    app.include_router(catalog.admin_router)

    static = settings.resolved_static_dir(BASE_DIR)
    if static and static.is_dir():
        app.mount("/", StaticFiles(directory=str(static), html=True), name="static")

    return app


def run() -> None:
    uvicorn.run(
        "shop_claim_portal.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=8790,
        reload=False,
    )


if __name__ == "__main__":
    run()
