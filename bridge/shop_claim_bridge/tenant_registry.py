"""Multi-tenant registry: servers, tokens, per-tenant catalogs."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from shop_claim_bridge.catalog import OfferCatalog
from shop_claim_bridge.config import resolve_path, tenant_is_pollable
from shop_claim_bridge.models import (
    BridgeConfig,
    GameServerConfig,
    TenantConfig,
    tenant_subscription_active,
)


class TenantRegistry:
    def __init__(self, config: BridgeConfig, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._tenants: dict[str, TenantConfig] = {}
        self._servers_by_id: dict[str, GameServerConfig] = {}
        self._by_token: dict[str, tuple[TenantConfig, GameServerConfig]] = {}
        self._shop_server_ids: dict[str, set[int]] = {}
        self._catalog_cache: dict[str, OfferCatalog] = {}

        for tenant in config.tenants:
            self._tenants[tenant.tenant_id] = tenant
            shop_ids: set[int] = set()
            for server in tenant.servers:
                if not server.enabled:
                    continue
                gs = server.model_copy(update={"tenant_id": tenant.tenant_id})
                if gs.catalog_path:
                    gs = gs.model_copy(
                        update={
                            "catalog_path": str(
                                resolve_path(base_dir, gs.catalog_path)
                            )
                        }
                    )
                self._servers_by_id[gs.server_id] = gs
                self._by_token[gs.api_token] = (tenant, gs)
                shop_ids.add(gs.shop_server_id)
            self._shop_server_ids[tenant.tenant_id] = shop_ids

    def get_tenant(self, tenant_id: str) -> TenantConfig | None:
        return self._tenants.get(tenant_id)

    def get_server(self, server_id: str) -> GameServerConfig | None:
        return self._servers_by_id.get(server_id)

    def get_by_token(self, token: str) -> tuple[TenantConfig, GameServerConfig] | None:
        return self._by_token.get(token)

    def list_servers(self) -> list[GameServerConfig]:
        return list(self._servers_by_id.values())

    def list_tenants(self) -> list[TenantConfig]:
        return list(self._tenants.values())

    def list_pollable_tenants(self) -> list[TenantConfig]:
        return [t for t in self._tenants.values() if tenant_is_pollable(t)]

    def shop_server_ids_for(self, tenant_id: str) -> set[int]:
        return self._shop_server_ids.get(tenant_id, set())

    def _profiles_path_for_tenant(self, tenant: TenantConfig) -> Path:
        if tenant.catalog.vehicle_profiles_path:
            return resolve_path(self._base_dir, tenant.catalog.vehicle_profiles_path)
        offers = resolve_path(self._base_dir, tenant.catalog.offers_path)
        return offers.parent / "vehicle_profiles.yaml"

    def get_catalog(
        self,
        tenant: TenantConfig,
        server: GameServerConfig | None = None,
    ) -> OfferCatalog:
        if server and server.catalog_path:
            offers_path = Path(server.catalog_path)
            profiles_path = offers_path.parent / "vehicle_profiles.yaml"
        else:
            offers_path = resolve_path(self._base_dir, tenant.catalog.offers_path)
            profiles_path = self._profiles_path_for_tenant(tenant)

        key = f"{offers_path}|{profiles_path}"
        if key not in self._catalog_cache:
            self._catalog_cache[key] = OfferCatalog(offers_path, profiles_path)
        return self._catalog_cache[key]

    def get_catalog_for_server(self, server_id: str) -> OfferCatalog | None:
        gs = self.get_server(server_id)
        if not gs:
            return None
        tenant = self.get_tenant(gs.tenant_id)
        if not tenant:
            return None
        return self.get_catalog(tenant, gs)

    def _catalog_paths_for_tenant(self, tenant_id: str) -> list[tuple[Path, Path]]:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return []
        paths: set[tuple[str, str]] = set()
        offers_path = resolve_path(self._base_dir, tenant.catalog.offers_path)
        profiles_path = self._profiles_path_for_tenant(tenant)
        paths.add((str(offers_path), str(profiles_path)))
        for server in tenant.servers:
            if server.catalog_path:
                sp = Path(server.catalog_path)
                if not sp.is_absolute():
                    sp = resolve_path(self._base_dir, server.catalog_path)
                pp = sp.parent / "vehicle_profiles.yaml"
                paths.add((str(sp), str(pp)))
        return [(Path(o), Path(p)) for o, p in paths]

    def reload_catalog(self, tenant_id: str) -> int:
        """Invalidate cache and reload YAML for all catalog paths of tenant."""
        keys_to_reload: list[str] = []
        for offers_path, profiles_path in self._catalog_paths_for_tenant(tenant_id):
            key = f"{offers_path}|{profiles_path}"
            keys_to_reload.append(key)
        count = 0
        for key in keys_to_reload:
            if key in self._catalog_cache:
                self._catalog_cache[key].reload()
                count += 1
            else:
                parts = key.split("|", 1)
                if len(parts) == 2:
                    self._catalog_cache[key] = OfferCatalog(Path(parts[0]), Path(parts[1]))
                    count += 1
        return count

    def reload_all_catalogs(self) -> int:
        total = 0
        for tenant in self._tenants.values():
            total += self.reload_catalog(tenant.tenant_id)
        return total

    def tenant_api_allowed(self, tenant: TenantConfig, *, today: date | None = None) -> bool:
        if not tenant.enabled:
            return False
        return tenant_subscription_active(tenant, today=today)
