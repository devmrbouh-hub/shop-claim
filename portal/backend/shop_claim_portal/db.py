"""Database session and lifecycle."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shop_claim_portal.config import Settings, get_settings
from shop_claim_portal.models import Base, PLATFORM_SETTINGS_ID, PlatformSettings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings | None = None, base_dir: Path | None = None) -> None:
    global _engine, _session_factory
    s = settings or get_settings()
    db_path = s.resolved_db_path(base_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    _engine = create_async_engine(url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def create_tables() -> None:
    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await migrate_schema()


async def migrate_schema() -> None:
    """Add columns to existing SQLite DBs without Alembic."""
    assert _engine is not None
    async with _engine.begin() as conn:
        def _migrate(sync_conn) -> None:
            import sqlalchemy as sa

            insp = sa.inspect(sync_conn)
            if "tenants" not in insp.get_table_names():
                return
            cols = {c["name"] for c in insp.get_columns("tenants")}
            if "catalog_draft_json" not in cols:
                sync_conn.execute(
                    sa.text("ALTER TABLE tenants ADD COLUMN catalog_draft_json TEXT DEFAULT ''")
                )
            if "catalog_has_unpublished" not in cols:
                sync_conn.execute(
                    sa.text(
                        "ALTER TABLE tenants ADD COLUMN catalog_has_unpublished "
                        "BOOLEAN DEFAULT 0 NOT NULL"
                    )
                )
            if "catalog_published_at" not in cols:
                sync_conn.execute(
                    sa.text("ALTER TABLE tenants ADD COLUMN catalog_published_at DATETIME")
                )
            if "max_servers" not in cols:
                sync_conn.execute(
                    sa.text("ALTER TABLE tenants ADD COLUMN max_servers INTEGER DEFAULT 1 NOT NULL")
                )
            if "plan" not in cols:
                sync_conn.execute(
                    sa.text(
                        "ALTER TABLE tenants ADD COLUMN plan VARCHAR(32) "
                        "DEFAULT 'free_year' NOT NULL"
                    )
                )

            if "users" in insp.get_table_names():
                user_cols = {c["name"] for c in insp.get_columns("users")}
                if "pending_email" not in user_cols:
                    sync_conn.execute(sa.text("ALTER TABLE users ADD COLUMN pending_email VARCHAR(254)"))

            if "invite_tokens" in insp.get_table_names():
                token_cols = {c["name"] for c in insp.get_columns("invite_tokens")}
                if "purpose" not in token_cols:
                    sync_conn.execute(
                        sa.text(
                            "ALTER TABLE invite_tokens ADD COLUMN purpose VARCHAR(32) "
                            "DEFAULT 'invite' NOT NULL"
                        )
                    )

            if "platform_settings" in insp.get_table_names():
                count = sync_conn.execute(sa.text("SELECT COUNT(*) FROM platform_settings")).scalar()
                if count == 0:
                    from shop_claim_portal.config import get_settings

                    seed_price = get_settings().billing_price_per_server_rub
                    sync_conn.execute(
                        sa.text(
                            "INSERT INTO platform_settings (id, price_per_server_rub, billing_enabled) "
                            "VALUES (:id, :price, 1)"
                        ),
                        {"id": PLATFORM_SETTINGS_ID, "price": seed_price},
                    )

        await conn.run_sync(_migrate)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session


async def dispose_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
