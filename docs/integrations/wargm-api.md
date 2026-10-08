# WarGM Shop API (справка)

Bridge использует [wargm.ru](https://wargm.ru) Shop API v1.1.

Фикстуры для тестов: [wargm_shop_info.json](../../bridge/tests/fixtures/wargm_shop_info.json), [wargm_shop_offer.json](../../bridge/tests/fixtures/wargm_shop_offer.json).

## shop/info (пример)

```json
{
  "responce": {
    "status": "ok",
    "data": {
      "id": 900001,
      "name": "Demo Shop",
      "servers": [10001, 10002, 10003],
      "active_servers": [10001, 10002, 10003]
    }
  }
}
```

## shop/offer

Offer `5002` — пример container; поле `servers` — shop server id из ЛК wargm.

## operations

Ответ — словарь операций в `responce.data`. Bridge парсит `offer_id`, `server_id` (shop server), `user_steam_id`.

После `delivered` от мода — `operation_success` (идемпотентно в SQLite).
