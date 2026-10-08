"""Catalog unit tests."""

from pathlib import Path

from shop_claim_bridge.catalog import OfferCatalog


def _repo_catalog() -> Path:
    return Path(__file__).resolve().parents[1].parent / "catalog" / "offers.yaml"


def _repo_profiles() -> Path:
    return Path(__file__).resolve().parents[1].parent / "catalog" / "vehicle_profiles.yaml"


def test_resolve_container():
    catalog = OfferCatalog(_repo_catalog(), _repo_profiles())
    resolved = catalog.resolve_delivery(5001)
    assert resolved is not None
    assert resolved["type"] == "container"
    assert resolved["delivery"]["container"] == "SeaChest"
    assert len(resolved["delivery"]["items"]) == 2


def test_resolve_vehicle():
    catalog = OfferCatalog(_repo_catalog(), _repo_profiles())
    resolved = catalog.resolve_delivery(5010)
    assert resolved is not None
    assert resolved["type"] == "vehicle"
    assert resolved["delivery"]["class"] == "OffroadHatchback"
    attachments = resolved["delivery"]["spawn_attachments"]
    assert len(attachments) == 13
    assert attachments[0] == "HatchbackWheel"
    assert "HatchbackDoors_Driver" in attachments
    fluids = resolved["delivery"]["fluids"]
    assert fluids.get("fuel") == 1.0
    assert fluids.get("coolant") == 1.0
    cargo = resolved["delivery"]["cargo_items"]
    assert len(cargo) == 1
    assert cargo[0]["class"] == "ExpansionCarKey"
    assert cargo[0]["qty"] == 1
    assert "give_key" not in resolved["delivery"]


def test_missing_offer():
    catalog = OfferCatalog(_repo_catalog(), _repo_profiles())
    assert catalog.resolve_delivery(99999) is None


def test_applies_to_server():
    catalog = OfferCatalog(_repo_catalog(), _repo_profiles())
    assert catalog.applies_to_server(5001, 10001) is True
    assert catalog.applies_to_server(5001, 68109) is False
