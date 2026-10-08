"""Portal configuration from environment."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PORTAL_", extra="ignore")

    env: str = "development"
    public_url: str = "http://127.0.0.1:8790"
    bridge_public_url: str = "http://127.0.0.1:8787/"
    database_path: str = "data/portal.db"
    jwt_secret: str = Field(default="dev-change-me-in-production-32bytes!!")
    jwt_ttl_hours: int = 8
    fernet_key: str = Field(default="")
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    bridge_config_path: str = ""
    catalog_root: str = ""
    bridge_admin_url: str = "http://127.0.0.1:8787"
    bridge_admin_secret: str = ""
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = "noreply@example.com"
    invite_ttl_hours: int = 72
    action_token_ttl_hours: int = 24
    static_dir: str = ""
    auto_bridge_sync: bool = True
    mods_dir: str = ""
    mods_manifest_path: str = ""
    workshop_gui_url: str = ""
    status_page_url: str = "http://127.0.0.1:8790/status"
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    billing_price_per_server_rub: int = 299
    yookassa_api_base: str = "https://api.yookassa.ru/v3"

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolved_db_path(self, base: Path | None = None) -> Path:
        p = Path(self.database_path)
        if p.is_absolute():
            return p
        root = base or Path.cwd()
        return (root / p).resolve()

    def resolved_bridge_path(self) -> Path | None:
        if not self.bridge_config_path:
            return None
        return Path(self.bridge_config_path).resolve()

    def resolved_catalog_root(self, base: Path | None = None) -> Path:
        if self.catalog_root:
            p = Path(self.catalog_root)
            if p.is_absolute():
                return p.resolve()
            return (base or Path.cwd()) / p
        bridge = self.resolved_bridge_path()
        if bridge and bridge.is_file():
            return bridge.parent.resolve()
        return (base or Path.cwd()).resolve()

    def resolved_static_dir(self, base: Path | None = None) -> Path | None:
        if not self.static_dir:
            return None
        p = Path(self.static_dir)
        if p.is_absolute():
            return p
        return (base or Path.cwd()) / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
