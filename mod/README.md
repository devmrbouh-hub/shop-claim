# ShopClaim server mod

Enforce Script mod: poll Bridge, spawn container/vehicle по каталогу.

## config.json

Скопировать [config/mod.example.json](../config/mod.example.json):

- `server_id`: `demo_server_alpha`
- `shop_server_id`: `10001`
- `bridge_url`: `http://127.0.0.1:8787/`

## Dev mock (Bridge `dev_mode: true`)

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8787/dev/mock-operation -Method Post -ContentType application/json `
  -Body '{"steam_id":"YOUR_STEAM64","offer_id":5001,"shop_server_id":10001,"server_id":"demo_server_alpha"}'
```

Демо офферы: `5001` container (`SeaChest`), `5010` vehicle (`OffroadHatchback`).

## Тесты

См. `bridge/tests` и [bridge/README.md](../bridge/README.md).
