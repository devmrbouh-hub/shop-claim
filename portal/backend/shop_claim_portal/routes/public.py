"""Public endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shop_claim_portal.config import get_settings
from shop_claim_portal.db import get_session
from shop_claim_portal.models import Lead, LeadStatus
from shop_claim_portal.rate_limit import rate_limiter
from shop_claim_portal.schemas import LeadCreate, ModsManifestOut
from shop_claim_portal.services.mods import build_mods_response, resolve_artifact_file
from shop_claim_portal.services.validation import strip_control_chars

router = APIRouter(prefix="/api/public", tags=["public"])

BASE_DIR = Path(__file__).resolve().parents[2]


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/mods", response_model=ModsManifestOut)
async def list_mods() -> dict:
    settings = get_settings()
    return build_mods_response(settings, BASE_DIR)


@router.get("/mods/{artifact_id}/download")
async def download_mod(artifact_id: str) -> FileResponse:
    settings = get_settings()
    path = resolve_artifact_file(settings, BASE_DIR, artifact_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(
        path,
        media_type="application/zip",
        filename=path.name,
    )


@router.post("/leads")
async def create_lead(
    body: LeadCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    client_ip = _client_ip(request)
    if not rate_limiter.allow(f"lead:{client_ip}", max_events=5, window_sec=60):
        return {"status": "accepted", "message": "Спасибо за заявку"}

    if body.website:
        return {"status": "accepted", "message": "Спасибо за заявку"}

    lead = Lead(
        project_name=strip_control_chars(body.project_name),
        email=body.email,
        telegram=strip_control_chars(body.telegram) if body.telegram else None,
        instance_count=body.instance_count,
        comment=strip_control_chars(body.comment, allow_newline=True) if body.comment else None,
        status=LeadStatus.new.value,
    )
    session.add(lead)
    await session.commit()
    return {"status": "accepted", "message": "Спасибо за заявку"}
