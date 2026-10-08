"""Mod distribution manifest for roadmap 8.2."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shop_claim_portal.config import Settings


def resolved_mods_dir(settings: Settings, base: Path) -> Path:
    if settings.mods_dir:
        p = Path(settings.mods_dir)
        if p.is_absolute():
            return p.resolve()
        return (base / p).resolve()
    return (base / "static" / "mods").resolve()


def resolved_manifest_path(settings: Settings, base: Path) -> Path:
    if settings.mods_manifest_path:
        p = Path(settings.mods_manifest_path)
        if p.is_absolute():
            return p.resolve()
        return (base / p).resolve()
    primary = resolved_mods_dir(settings, base) / "manifest.json"
    if primary.is_file():
        return primary
    repo_fallback = base.parent.parent / "config" / "mods.manifest.json"
    if repo_fallback.is_file():
        return repo_fallback
    return primary


def _load_raw_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": "0.0.0-dev", "updated_at": "", "artifacts": []}
    # utf-8-sig: tolerate BOM from PowerShell Set-Content -Encoding UTF8 (legacy manifests)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_mods_response(settings: Settings, base: Path) -> dict[str, Any]:
    mods_dir = resolved_mods_dir(settings, base)
    manifest_path = resolved_manifest_path(settings, base)
    raw = _load_raw_manifest(manifest_path)
    artifacts: list[dict[str, Any]] = []
    for item in raw.get("artifacts") or []:
        if not isinstance(item, dict):
            continue
        artifact_id = str(item.get("id") or "")
        if not artifact_id:
            continue
        filename = str(item.get("filename") or "")
        file_path = mods_dir / filename if filename else None
        download_url = f"/api/public/mods/{artifact_id}/download"
        workshop_url = item.get("workshop_url") or ""
        if artifact_id == "shopclaim_gui" and settings.workshop_gui_url:
            workshop_url = settings.workshop_gui_url
        entry: dict[str, Any] = {
            "id": artifact_id,
            "name": item.get("name") or artifact_id,
            "description": item.get("description") or "",
            "kind": item.get("kind") or "other",
            "required": bool(item.get("required")),
            "download_url": download_url,
            "download_available": bool(file_path and file_path.is_file()),
            "workshop_url": workshop_url or None,
        }
        if file_path and file_path.is_file():
            entry["size_bytes"] = file_path.stat().st_size
            entry["filename"] = filename
        artifacts.append(entry)
    return {
        "version": raw.get("version") or "0.0.0-dev",
        "updated_at": raw.get("updated_at") or "",
        "status_page_url": settings.status_page_url or None,
        "artifacts": artifacts,
    }


def resolve_artifact_file(
    settings: Settings, base: Path, artifact_id: str
) -> Path | None:
    manifest_path = resolved_manifest_path(settings, base)
    raw = _load_raw_manifest(manifest_path)
    mods_dir = resolved_mods_dir(settings, base)
    for item in raw.get("artifacts") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("id")) != artifact_id:
            continue
        filename = str(item.get("filename") or "")
        if not filename:
            return None
        path = mods_dir / filename
        return path if path.is_file() else None
    return None


def write_manifest(
    mods_dir: Path,
    *,
    version: str,
    artifacts: list[dict[str, Any]],
) -> Path:
    mods_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": version,
        "updated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "artifacts": artifacts,
    }
    path = mods_dir / "manifest.json"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path
