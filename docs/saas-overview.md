# SaaS overview

ShopClaim может работать как **self-hosted** (один Bridge на хосте) или как **provider** (multi-tenant Bridge + Portal).

| Режим | Bridge | Portal |
|-------|--------|--------|
| Self-hosted | `config/bridge.example.json`, каталог в `catalog/` | опционально локально |
| SaaS | `config/bridge-tenant.example.json`, `tenants/{id}/` | подписка, ЛК, publish YAML |

Демо tenant id: `demo`. Пример shop server id: `10001`–`10003`.

См. [billing-overview.md](billing-overview.md), [portal-local-dev.md](portal-local-dev.md).
