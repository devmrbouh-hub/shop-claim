"""Pydantic models for config and API."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class WargmShopCredentials(BaseModel):
    shop_id: str
    api_key: str
    api_base: str = "https://api.wargm.ru/v1.1/shop"


class ServerListenConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8787


class PollFiltersConfig(BaseModel):
    claimed: int = 0
    status: str = "pending"
    delivery: list[str] = Field(default_factory=lambda: ["online", "api"])


class PollConfig(BaseModel):
    interval_sec: int = 45
    sync_retry_sec: int = 60
    operations_filters: PollFiltersConfig = Field(default_factory=PollFiltersConfig)
    lookback_days: int = 7


class DatabaseConfig(BaseModel):
    path: str = "data/orders.db"


class CatalogConfig(BaseModel):
    """Legacy single-tenant catalog path (offers.yaml only)."""

    path: str = "catalog/offers.yaml"


class TenantCatalogConfig(BaseModel):
    offers_path: str = "catalog/offers.yaml"
    vehicle_profiles_path: str | None = None


class GameServerConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    server_id: str
    shop_server_id: int = Field(validation_alias=AliasChoices("shop_server_id", "wargm_server_id"))
    api_token: str
    enabled: bool = True
    catalog_path: str | None = None
    tenant_id: str = ""


class TenantConfig(BaseModel):
    tenant_id: str
    enabled: bool = True
    subscription_until: date
    wargm: WargmShopCredentials
    catalog: TenantCatalogConfig = Field(default_factory=TenantCatalogConfig)
    servers: list[GameServerConfig] = Field(default_factory=list)
    allowed_egress_ips: list[str] | None = None


class BridgeConfig(BaseModel):
    server: ServerListenConfig = Field(default_factory=ServerListenConfig)
    poll: PollConfig = Field(default_factory=PollConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    tenants: list[TenantConfig] = Field(default_factory=list)
    dev_mode: bool = False

    # Legacy single-tenant fields (normalized away at load time)
    wargm: WargmShopCredentials | None = None
    catalog: CatalogConfig | None = None
    servers: list[GameServerConfig] | None = None

    def any_wargm_poll_enabled(self) -> bool:
        return any(tenant_wargm_enabled(t) for t in self.tenants)


def tenant_wargm_enabled(tenant: TenantConfig) -> bool:
    key = tenant.wargm.api_key
    return (
        bool(key)
        and key != "YOUR_SHOP_API_KEY"
        and tenant.wargm.shop_id != "YOUR_SHOP_ID"
    )


def tenant_subscription_active(tenant: TenantConfig, *, today: date | None = None) -> bool:
    ref = today or date.today()
    return ref <= tenant.subscription_until


LocalStatus = Literal["available", "spawned", "done", "failed", "unmapped"]
OrderSource = Literal["wargm", "mock"]
DeliveryType = Literal["container", "vehicle"]


class MockOperationRequest(BaseModel):
    steam_id: str
    offer_id: str | int
    shop_server_id: int
    server_id: str | None = None


class PendingOrderResponse(BaseModel):
    operation_id: str
    offer_id: str
    name: str
    type: DeliveryType
    status: LocalStatus
    delivery: dict[str, Any]


class TenantHealthInfo(BaseModel):
    tenant_id: str
    enabled: bool
    poll: bool


class HealthResponse(BaseModel):
    status: str = "ok"
    shop_poll: bool
    dev_mode: bool
    tenant_count: int = 0
    tenants: list[TenantHealthInfo] = Field(default_factory=list)
