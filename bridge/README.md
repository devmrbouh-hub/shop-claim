# ShopClaim Bridge

Сервис между [wargm.ru](https://wargm.ru/docs_api) Shop API **v1.1** и DayZ server mod.

Каталог: [self-hosted-catalog-workflow.md](../docs/self-hosted-catalog-workflow.md).

## Конфигурация

| Формат | Файл | Назначение |
|--------|------|------------|
| Single-tenant | [bridge.example.json](../config/bridge.example.json) | Dev → `tenant_id: default` |
| Multi-tenant | [bridge-tenant.example.json](../config/bridge-tenant.example.json) | `tenants/demo/` |

## Локальный запуск

```powershell
cd bridge
py -3.12 -m pip install -e ".[dev]"
copy ..\config\bridge.example.json bridge.json
py -3.12 -m shop_claim_bridge.main
```

Тесты: `py -3.12 -m pytest -q`

## API mod

`GET /api/v1/servers/{server_id}/players/{steam}/pending` — Bearer `api_token` из конфига.

Dev: `POST /dev/mock-operation` с `offer_id` из `catalog/offers.yaml` (демо: `5001`, `5010`).
