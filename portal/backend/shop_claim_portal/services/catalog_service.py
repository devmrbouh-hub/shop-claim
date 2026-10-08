"""Catalog draft/publish service."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from shop_claim_portal.models import Tenant
from shop_claim_portal.services.bridge_sync import _default_catalog_paths

CLASSNAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
MAX_OFFERS = 500
MAX_ITEMS = 50
MAX_ATTACHMENTS = 20
MAX_CLASSNAME_LEN = 128

EMPTY_DRAFT: dict[str, Any] = {
    "offers": {},
    "deleted_offer_ids": [],
    "vehicle_profiles": {},
}


class CatalogError(Exception):
    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.status_code = status_code


class PublishConflictError(CatalogError):
    def __init__(self) -> None:
        super().__init__("Каталог изменён другим пользователем. Обновите страницу.", 409)


class CatalogReloadError(CatalogError):
    def __init__(self, message: str = "Файл сохранён, reload Bridge не удался") -> None:
        super().__init__(message, 502)


def resolve_catalog_path(root: Path, relative: str) -> Path:
    root_resolved = root.resolve()
    rel = Path(relative)
    if rel.is_absolute():
        resolved = rel.resolve()
    else:
        if ".." in rel.parts:
            raise CatalogError("Некорректный путь каталога", 400)
        resolved = (root_resolved / rel).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise CatalogError("Некорректный путь каталога", 400) from exc
    return resolved


def catalog_paths_for_tenant(tenant: Tenant, catalog_root: Path) -> tuple[Path, Path]:
    offers_rel = tenant.catalog_offers_path or _default_catalog_paths(tenant.tenant_id)[0]
    profiles_rel = (
        tenant.catalog_vehicle_profiles_path or _default_catalog_paths(tenant.tenant_id)[1]
    )
    return (
        resolve_catalog_path(catalog_root, offers_rel),
        resolve_catalog_path(catalog_root, profiles_rel),
    )


def parse_draft(raw: str | None) -> dict[str, Any]:
    if not raw:
        return json.loads(json.dumps(EMPTY_DRAFT))
    data = json.loads(raw)
    return {
        "offers": {str(k): v for k, v in (data.get("offers") or {}).items()},
        "deleted_offer_ids": [str(x) for x in (data.get("deleted_offer_ids") or [])],
        "vehicle_profiles": {
            str(k): v for k, v in (data.get("vehicle_profiles") or {}).items()
        },
    }


def draft_to_json(draft: dict[str, Any]) -> str:
    return json.dumps(draft, ensure_ascii=False)


def normalize_item_dict(item: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "class": str(item.get("class", "")),
        "qty": int(item.get("qty", 1) or 1),
    }
    attachments = item.get("attachments")
    if attachments:
        out["attachments"] = list(attachments)
    return out


def normalize_offer_dict(offer: dict[str, Any]) -> dict[str, Any]:
    """Legacy YAML keys (wargm_server_ids, give_key) → canonical editor shape."""
    o = dict(offer)
    wargm_ids = o.pop("wargm_server_ids", None)
    if wargm_ids is not None and "shop_server_ids" not in o:
        o["shop_server_ids"] = [int(x) for x in wargm_ids]
    o.pop("give_key", None)
    if o.get("items"):
        o["items"] = [normalize_item_dict(i) for i in o["items"] if isinstance(i, dict)]
    return o


def load_yaml_offers(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = data.get("offers") or {}
    return {str(k): normalize_offer_dict(v) for k, v in raw.items()}


def load_yaml_profiles(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = data.get("profiles") or {}
    return {str(k): v for k, v in raw.items()}


def merge_catalog(
    published_offers: dict[str, Any],
    published_profiles: dict[str, Any],
    draft: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    offers = dict(published_offers)
    for oid in draft.get("deleted_offer_ids") or []:
        offers.pop(str(oid), None)
    for oid, offer in (draft.get("offers") or {}).items():
        offers[str(oid)] = offer
    profiles = dict(published_profiles)
    for cls_name, prof in (draft.get("vehicle_profiles") or {}).items():
        profiles[str(cls_name)] = prof
    return offers, profiles


def validate_classname(class_name: str) -> None:
    if not class_name or len(class_name) > MAX_CLASSNAME_LEN:
        raise CatalogError("Некорректный classname")
    if not CLASSNAME_RE.match(class_name):
        raise CatalogError(f"Некорректный classname: {class_name}")


def validate_offer(offer_id: str, offer: dict[str, Any]) -> None:
    dtype = offer.get("type", "container")
    name = (offer.get("name") or "").strip()
    if not name:
        raise CatalogError("Укажите название для игрового меню")
    if dtype == "container":
        items = offer.get("items") or []
        if not items:
            raise CatalogError("Укажите хотя бы один предмет в ящике")
        container = offer.get("container", "SeaChest")
        validate_classname(container)
        if len(items) > MAX_ITEMS:
            raise CatalogError(f"Максимум {MAX_ITEMS} предметов в offer")
        for item in items:
            validate_classname(str(item.get("class", "")))
            attachments = item.get("attachments") or []
            if len(attachments) > MAX_ATTACHMENTS:
                raise CatalogError(f"Максимум {MAX_ATTACHMENTS} attachments")
            for att in attachments:
                validate_classname(str(att))
    elif dtype == "vehicle":
        vclass = offer.get("class", "")
        if not vclass:
            raise CatalogError("Укажите class для техники")
        validate_classname(str(vclass))
    else:
        raise CatalogError(f"Неизвестный тип offer: {dtype}")


def validate_all(offers: dict[str, Any], _profiles: dict[str, Any]) -> None:
    if len(offers) > MAX_OFFERS:
        raise CatalogError(f"Максимум {MAX_OFFERS} offers в каталоге")
    for oid, offer in offers.items():
        validate_offer(str(oid), offer)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.with_suffix(path.suffix + ".bak")
    if path.is_file():
        shutil.copy2(path, backup)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def write_offers_yaml(path: Path, offers: dict[str, Any]) -> None:
    sorted_offers: dict[str, Any] = {}
    for key in sorted(offers.keys(), key=lambda x: int(x) if str(x).isdigit() else x):
        sorted_offers[key] = normalize_offer_dict(offers[key])
    content = yaml.dump(
        {"offers": sorted_offers},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    _atomic_write_text(path, content)


def write_profiles_yaml(path: Path, profiles: dict[str, Any]) -> None:
    content = yaml.dump(
        {"profiles": profiles},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    _atomic_write_text(path, content)


def load_published(tenant: Tenant, catalog_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    offers_path, profiles_path = catalog_paths_for_tenant(tenant, catalog_root)
    return load_yaml_offers(offers_path), load_yaml_profiles(profiles_path)


def load_merged(tenant: Tenant, catalog_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    published_offers, published_profiles = load_published(tenant, catalog_root)
    draft = parse_draft(tenant.catalog_draft_json)
    return merge_catalog(published_offers, published_profiles, draft)


def catalog_meta(tenant: Tenant, catalog_root: Path) -> dict[str, Any]:
    offers_path, profiles_path = catalog_paths_for_tenant(tenant, catalog_root)
    published_offers, _ = load_published(tenant, catalog_root)
    merged_offers, _ = load_merged(tenant, catalog_root)
    return {
        "has_unpublished_changes": tenant.catalog_has_unpublished,
        "catalog_published_at": tenant.catalog_published_at,
        "offers_path": str(offers_path),
        "vehicle_profiles_path": str(profiles_path),
        "published_offer_count": len(published_offers),
        "merged_offer_count": len(merged_offers),
    }


def save_draft_offer(
    tenant: Tenant,
    offer_id: str,
    offer: dict[str, Any],
    *,
    existing_merged: dict[str, Any] | None = None,
) -> dict[str, Any]:
    oid = str(offer_id).strip()
    if not oid or not oid.isdigit():
        raise CatalogError("offer_id должен быть числом wargm", 400)
    draft = parse_draft(tenant.catalog_draft_json)
    deleted = draft.get("deleted_offer_ids") or []
    if oid in deleted:
        deleted = [x for x in deleted if x != oid]
        draft["deleted_offer_ids"] = deleted
    if existing_merged and oid in existing_merged and oid not in (draft.get("offers") or {}):
        if existing_merged[oid] == offer:
            return draft
    draft_offers = draft.setdefault("offers", {})
    draft_offers[oid] = normalize_offer_dict(offer)
    tenant.catalog_draft_json = draft_to_json(draft)
    tenant.catalog_has_unpublished = True
    return draft


def delete_draft_offer(tenant: Tenant, offer_id: str) -> dict[str, Any]:
    oid = str(offer_id).strip()
    draft = parse_draft(tenant.catalog_draft_json)
    draft_offers = draft.setdefault("offers", {})
    draft_offers.pop(oid, None)
    deleted = set(draft.get("deleted_offer_ids") or [])
    deleted.add(oid)
    draft["deleted_offer_ids"] = sorted(deleted)
    tenant.catalog_draft_json = draft_to_json(draft)
    tenant.catalog_has_unpublished = True
    return draft


def discard_draft(tenant: Tenant) -> None:
    tenant.catalog_draft_json = draft_to_json(EMPTY_DRAFT)
    tenant.catalog_has_unpublished = False


def save_draft_vehicle_profile(
    tenant: Tenant, class_name: str, profile: dict[str, Any]
) -> dict[str, Any]:
    validate_classname(class_name)
    draft = parse_draft(tenant.catalog_draft_json)
    profiles = draft.setdefault("vehicle_profiles", {})
    profiles[class_name] = profile
    tenant.catalog_draft_json = draft_to_json(draft)
    tenant.catalog_has_unpublished = True
    return draft


def _normalize_dt(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def check_publish_conflict_with_root(
    tenant: Tenant,
    catalog_root: Path,
    expected_published_at: datetime | None,
) -> None:
    if expected_published_at is None:
        return
    current = tenant.catalog_published_at
    offers_path, _ = catalog_paths_for_tenant(tenant, catalog_root)
    if current is None and not offers_path.is_file() and expected_published_at is None:
        return
    if current is None and expected_published_at is not None:
        if not offers_path.is_file():
            return
        raise PublishConflictError()
    if current is not None and expected_published_at is not None:
        if _normalize_dt(current) != _normalize_dt(expected_published_at):
            raise PublishConflictError()


def publish_catalog(
    tenant: Tenant,
    catalog_root: Path,
    *,
    expected_published_at: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    check_publish_conflict_with_root(tenant, catalog_root, expected_published_at)
    offers, profiles = load_merged(tenant, catalog_root)
    validate_all(offers, profiles)
    offers_path, profiles_path = catalog_paths_for_tenant(tenant, catalog_root)
    write_offers_yaml(offers_path, offers)
    write_profiles_yaml(profiles_path, profiles)
    tenant.catalog_draft_json = draft_to_json(EMPTY_DRAFT)
    tenant.catalog_has_unpublished = False
    tenant.catalog_published_at = datetime.now(timezone.utc)
    return offers, profiles, len(offers)


def merge_wargm_import(
    existing: dict[str, Any] | None,
    imported: dict[str, Any],
) -> dict[str, Any]:
    if not existing:
        return imported
    merged = dict(existing)
    if not merged.get("name"):
        merged["name"] = imported.get("name")
    if not merged.get("items"):
        merged["items"] = imported.get("items", [])
    if "shop_server_ids" not in merged and imported.get("shop_server_ids"):
        merged["shop_server_ids"] = imported["shop_server_ids"]
    if merged.get("type") is None:
        merged["type"] = imported.get("type", "container")
    if not merged.get("container"):
        merged["container"] = imported.get("container", "SeaChest")
    return merged
