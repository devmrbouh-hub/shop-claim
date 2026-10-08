"""Offer catalog from YAML."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from shop_claim_bridge.models import DeliveryType

logger = logging.getLogger(__name__)


class OfferCatalog:
    def __init__(self, path: Path, profiles_path: Path | None = None) -> None:
        self.path = path
        self._offers: dict[str, dict[str, Any]] = {}
        self._vehicle_profiles: dict[str, dict[str, Any]] = {}
        if profiles_path is None:
            profiles_path = path.parent / "vehicle_profiles.yaml"
        self._profiles_path = profiles_path
        self.reload()

    def reload(self) -> None:
        if not self.path.is_file():
            logger.warning("Catalog file missing: %s", self.path)
            self._offers = {}
        else:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
            raw = data.get("offers") or {}
            self._offers = {str(k): v for k, v in raw.items()}
            logger.info("Loaded %d offers from %s", len(self._offers), self.path)

        if not self._profiles_path.is_file():
            logger.warning("Vehicle profiles file missing: %s", self._profiles_path)
            self._vehicle_profiles = {}
        else:
            pdata = yaml.safe_load(self._profiles_path.read_text(encoding="utf-8")) or {}
            raw_profiles = pdata.get("profiles") or {}
            self._vehicle_profiles = {str(k): v for k, v in raw_profiles.items()}
            logger.info(
                "Loaded %d vehicle profiles from %s",
                len(self._vehicle_profiles),
                self._profiles_path,
            )

    def get(self, offer_id: str | int) -> dict[str, Any] | None:
        return self._offers.get(str(offer_id))

    def _resolve_spawn_attachments(
        self, offer: dict[str, Any], class_name: str | None
    ) -> list[str]:
        if offer.get("spawn_attachments"):
            return list(offer["spawn_attachments"])
        if offer.get("attachments"):
            return list(offer["attachments"])
        if class_name and class_name in self._vehicle_profiles:
            profile = self._vehicle_profiles[class_name]
            return list(profile.get("spawn_attachments") or [])
        return []

    def _resolve_fluids(
        self, offer: dict[str, Any], class_name: str | None
    ) -> dict[str, Any]:
        offer_fluids = offer.get("fluids") or {}
        if offer_fluids:
            return dict(offer_fluids)
        if class_name and class_name in self._vehicle_profiles:
            profile = self._vehicle_profiles[class_name]
            profile_fluids = profile.get("fluids") or {}
            return dict(profile_fluids)
        return {}

    def _resolve_cargo_items(
        self, offer: dict[str, Any], class_name: str | None
    ) -> list[dict[str, Any]]:
        if offer.get("cargo_items"):
            return list(offer["cargo_items"])
        if class_name and class_name in self._vehicle_profiles:
            profile = self._vehicle_profiles[class_name]
            return list(profile.get("cargo_items") or [])
        return []

    def resolve_delivery(self, offer_id: str | int) -> dict[str, Any] | None:
        offer = self.get(offer_id)
        if not offer:
            return None
        dtype: DeliveryType = offer.get("type", "container")
        name = offer.get("name", f"Offer {offer_id}")
        result: dict[str, Any] = {
            "name": name,
            "type": dtype,
            "delivery": {},
        }
        if dtype == "container":
            result["delivery"] = {
                "container": offer.get("container", "SeaChest"),
                "items": offer.get("items", []),
            }
        elif dtype == "vehicle":
            class_name = offer.get("class")
            if offer.get("give_key"):
                logger.warning(
                    "offer %s: give_key deprecated — use cargo_items in vehicle_profiles.yaml",
                    offer_id,
                )
            spawn_attachments = self._resolve_spawn_attachments(offer, class_name)
            fluids = self._resolve_fluids(offer, class_name)
            cargo_items = self._resolve_cargo_items(offer, class_name)
            result["delivery"] = {
                "class": class_name,
                "spawn_attachments": spawn_attachments,
                "cargo_items": cargo_items,
                "fluids": fluids,
                "spawn": offer.get("spawn", {}),
            }
        return result

    def applies_to_server(self, offer_id: str | int, shop_server_id: int) -> bool:
        offer = self.get(offer_id)
        if not offer:
            return False
        allowed = offer.get("shop_server_ids")
        if allowed is None:
            allowed = offer.get("wargm_server_ids")
        if allowed is None:
            return True
        return shop_server_id in allowed
