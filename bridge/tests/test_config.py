"""Multi-tenant config and registry tests."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from shop_claim_bridge.config import load_config, normalize_config, validate_config
from shop_claim_bridge.models import BridgeConfig


def test_normalize_legacy_bridge_json():
    raw = {
        "wargm": {"shop_id": "1", "api_key": "key"},
        "servers": [{"server_id": "s1", "shop_server_id": 1, "api_token": "t1"}],
        "catalog": {"path": "catalog/offers.yaml"},
        "dev_mode": True,
    }
    normalized = normalize_config(raw)
    assert len(normalized["tenants"]) == 1
    assert normalized["tenants"][0]["tenant_id"] == "default"
    assert normalized["tenants"][0]["wargm"]["shop_id"] == "1"
    assert normalized["tenants"][0]["catalog"]["offers_path"] == "catalog/offers.yaml"


def test_validate_duplicate_api_token_fails():
    config = BridgeConfig.model_validate(
        {
            "tenants": [
                {
                    "tenant_id": "a",
                    "enabled": True,
                    "subscription_until": "2099-01-01",
                    "wargm": {"shop_id": "1", "api_key": "k1"},
                    "servers": [
                        {
                            "server_id": "s1",
                            "shop_server_id": 1,
                            "api_token": "same-token",
                        }
                    ],
                },
                {
                    "tenant_id": "b",
                    "enabled": True,
                    "subscription_until": "2099-01-01",
                    "wargm": {"shop_id": "2", "api_key": "k2"},
                    "servers": [
                        {
                            "server_id": "s2",
                            "shop_server_id": 2,
                            "api_token": "same-token",
                        }
                    ],
                },
            ]
        }
    )
    with pytest.raises(ValueError, match="Duplicate api_token"):
        validate_config(config)


def test_validate_duplicate_shop_id_fails():
    config = BridgeConfig.model_validate(
        {
            "tenants": [
                {
                    "tenant_id": "a",
                    "enabled": True,
                    "subscription_until": "2099-01-01",
                    "wargm": {"shop_id": "shop-1", "api_key": "k1"},
                    "servers": [
                        {
                            "server_id": "s1",
                            "shop_server_id": 1,
                            "api_token": "t1",
                        }
                    ],
                },
                {
                    "tenant_id": "b",
                    "enabled": True,
                    "subscription_until": "2099-01-01",
                    "wargm": {"shop_id": "shop-1", "api_key": "k2"},
                    "servers": [
                        {
                            "server_id": "s2",
                            "shop_server_id": 2,
                            "api_token": "t2",
                        }
                    ],
                },
            ]
        }
    )
    with pytest.raises(ValueError, match="Duplicate wargm shop_id"):
        validate_config(config)


def test_load_config_legacy_file(tmp_path: Path):
    cfg = {
        "wargm": {"shop_id": "YOUR_SHOP_ID", "api_key": "YOUR_SHOP_API_KEY"},
        "servers": [
            {
                "server_id": "demo_map_1",
                "shop_server_id": 10001,
                "api_token": "tok",
            }
        ],
        "catalog": {"path": "catalog/offers.yaml"},
        "dev_mode": True,
    }
    path = tmp_path / "bridge.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    config, _ = load_config(path)
    assert len(config.tenants) == 1
    assert config.tenants[0].tenant_id == "default"


def test_tenant_subscription_inclusive_boundary():
    from shop_claim_bridge.models import TenantConfig, tenant_subscription_active

    tenant = TenantConfig(
        tenant_id="t",
        subscription_until=date.today(),
        wargm={"shop_id": "1", "api_key": "k"},
        servers=[],
    )
    assert tenant_subscription_active(tenant) is True
    assert tenant_subscription_active(
        tenant, today=date.today() + timedelta(days=1)
    ) is False
