"""Public mod distribution API tests (8.2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient

BASE_DIR = Path(__file__).resolve().parents[1]
MODS_DIR = BASE_DIR / "static" / "mods"


@pytest.mark.asyncio
async def test_public_mods_manifest(client: AsyncClient):
    r = await client.get("/api/public/mods")
    assert r.status_code == 200
    data = r.json()
    assert "version" in data
    assert "artifacts" in data
    assert isinstance(data["artifacts"], list)
    assert len(data["artifacts"]) >= 3
    server = next(a for a in data["artifacts"] if a["id"] == "shopclaim_server")
    assert server["name"] == "@ShopClaim"
    assert server["download_url"].endswith("/shopclaim_server/download")


@pytest.mark.asyncio
async def test_public_mod_download_missing_file(client: AsyncClient):
    r = await client.get("/api/public/mods/shopclaim_server/download")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_public_mod_download_ok(client: AsyncClient, tmp_path: Path, monkeypatch):
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir()
    zip_path = mods_dir / "ShopClaim-server-mod.zip"
    zip_path.write_bytes(b"PK\x03\x04test")
    manifest = {
        "version": "test",
        "updated_at": "",
        "artifacts": [
            {
                "id": "shopclaim_server",
                "name": "@ShopClaim",
                "description": "x",
                "kind": "server_mod",
                "required": True,
                "filename": "ShopClaim-server-mod.zip",
            }
        ],
    }
    (mods_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    from shop_claim_portal.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("PORTAL_MODS_DIR", str(mods_dir))
    monkeypatch.setenv("PORTAL_MODS_MANIFEST_PATH", str(mods_dir / "manifest.json"))

    r = await client.get("/api/public/mods/shopclaim_server/download")
    assert r.status_code == 200
    assert r.content.startswith(b"PK")
    get_settings.cache_clear()


def test_manifest_with_utf8_bom(tmp_path: Path, monkeypatch):
    """PowerShell Set-Content -Encoding UTF8 adds BOM; loader must tolerate it."""
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir()
    bom_manifest = mods_dir / "manifest.json"
    bom_manifest.write_bytes(
        b"\xef\xbb\xbf"
        + json.dumps(
            {
                "version": "bom-test",
                "updated_at": "",
                "artifacts": [
                    {
                        "id": "shopclaim_server",
                        "name": "@ShopClaim",
                        "description": "x",
                        "kind": "server_mod",
                        "required": True,
                        "filename": "missing.zip",
                    }
                ],
            }
        ).encode("utf-8")
    )

    from shop_claim_portal.config import get_settings
    from shop_claim_portal.services.mods import build_mods_response

    get_settings.cache_clear()
    monkeypatch.setenv("PORTAL_MODS_DIR", str(mods_dir))
    monkeypatch.setenv("PORTAL_MODS_MANIFEST_PATH", str(bom_manifest))

    settings = get_settings()
    data = build_mods_response(settings, Path(__file__).resolve().parents[1])
    assert data["version"] == "bom-test"
    assert len(data["artifacts"]) == 1
    get_settings.cache_clear()
