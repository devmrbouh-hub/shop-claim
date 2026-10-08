# Типы выдачи: контейнер и техника

В каталоге [`offers.yaml`](../catalog/offers.example.yaml) у каждого `offer_id` задаётся поле `type`.

## container — предметы в ящике

Подходит для: наборов, оружия, денег (`Money_Ruble*`), расходников.

### Поведение

1. Игрок выбирает покупку (GUI или `/wargm <номер>`).
2. Сервер проверяет **поверхность** перед spawn (`ShopClaimSpawnSurface`: raycast, `SurfaceIsSea`, уклон, радиус) — параметры в `config.json` (`container_spawn_*`). При отказе — сообщение `container_bad_surface`.
3. Сервер спавнит **личный** контейнер **перед игроком**. Класс задаётся в каталоге (`container:`), иначе — `container_class` в `config.json`, иначе `SeaChest`. Поддерживаются наследники `Container_Base` (`SeaChest`, `Barrel_Green`, `LA_SeaChest_camo` и т.д.).
4. Предметы кладутся в cargo по **ledger** (`fulfillment.json`): при первом claim — init из каталога; при recovery / respawn — только строки с `qty_remaining > 0`.
5. **Один активный ящик** на игрока — пока не опустошён, новый `container` не выдаётся. При блокировке — кнопка **«Пересоздать»** в GUI или `/wargm respawn` (dev).
6. При снятии предмета из WarGM-ящика — `qty_remaining--` в ledger (`EEItemDetached` + reconcile при respawn / `RegisterSelf`).
7. Когда cargo **пуст** — контейнер удаляется, ledger очищается.
8. Bridge вызывает wargm **`operation_success`**.

### Приоритет класса контейнера

1. `container` в [`offers.yaml`](../catalog/offers.yaml) для данного `offer_id`
2. `container_class` в `profiles/ShopClaim/config.json`
3. `SeaChest`

### Ограничения

- Если инвентарь игрока полон — предметы остаются в ящике, ящик не удаляется.
- Ящик магазина (`modded class Container_Base` с маркером WarGM): **нельзя поднять** в руки, **нельзя положить** предметы из инвентаря (только забрать выданный лут).
- Класс из каталога должен наследовать `Container_Base`; иначе spawn пройдёт, но защиты и persistence не сработают (ошибка в `mod.log`).
- Spawn перед игроком через `ShopClaimSpawnSurface` (raycast, `SurfaceIsSea`, уклон, радиус) — см. `container_spawn_*` в `config.json`. 100% гарантии на понтонах нет; при проблеме — **пересоздать ящик** на суше.
- При рестарте сервера — восстановление через `active_containers.json` + self-register ящика из `storage_*`; **reconcile** cargo → ledger в `RegisterSelf`.

### Ledger частичной выдачи (`fulfillment.json`)

Путь: `$profile:ShopClaim/fulfillment.json`.

- Ключ — `operation_id`; строки: `class`, `qty_total`, `qty_remaining`, `attachments[]`.
- Init при первом успешном fill из каталога Bridge.
- Decrement при снятии предмета игроком; reconcile `min(qty_remaining, countInCargo)` при respawn и после рестарта.
- **Учёт единиц каталога:** для большинства предметов **1 entity в cargo = 1** в ledger (бинты, магазины, оружие). `GetQuantity()` у расходников — **остаток использований**, не штуки из каталога; у магазинов — **патроны в обойме**, не число магазинов.
- **Исключение — деньги:** только `Money_Ruble*` учитываются по `GetQuantity()` (число купюр в стаке / снятой порции). Номинал в classname (`500`, `5000`) не используется как quantity.
- Россыпь `Ammo_*` в v1 — **entity**, не quantity (отдельный E2E перед whitelist).
- Удаление записи при `delivered`.
- Recovery `alreadySpawned` **без** ledger — отказ (admin: [admin-bridge-order-reset.md](admin-bridge-order-reset.md)), **не** полный re-fill.

### Пересоздание ящика (respawn)

- GUI: кнопка **«Пересоздать»** (видна при активном ящике; RPC `RespawnContainer`).
- Dev-чат: `/wargm respawn` / `/wargm пересоздать` при `enable_chat_commands: true`.
- Cooldown `container_respawn_cooldown_sec` (по умолчанию 30 с).
- Публичный `/wargm cancel` **отключён** (сообщение с подсказкой на respawn).

### Persistence (`active_containers.json`)

Путь: `$profile:ShopClaim/active_containers.json` (рядом с `config.json`).

```json
{
  "version": 1,
  "containers": [
    {
      "steam_id": "76561198036072127",
      "operation_id": "mock-…",
      "container_class": "SeaChest",
      "pid1": 0,
      "pid2": 0,
      "pid3": 0,
      "pid4": 0,
      "spawned_at": "2026-06-24T12:00:00Z",
      "spawned_minutes": 0
    }
  ]
}
```

- При старте миссии мод **сразу** загружает JSON → `HasActiveContainer` блокирует повторный claim.
- Ящик с маркером после загрузки мира вызывает `RegisterSelf` в трекере.
- Через 10 мин без привязки entity — запись удаляется из JSON (recovery через `/wargm N` при статусе `spawned` в Bridge).

**Проверено на Instance_1 (2026-06-24):** рестарт с неопустошённым SeaChest, `RegisterSelf` в `mod.log`, блок повторного claim, опустошение → `delivered`.

**Проверено на Instance_1 (2026-06-24):** per-offer контейнеры `Barrel_Green` (`5020`) и `LA_SeaChest_camo` (`5021`) — класс из каталога, защиты WarGM, `delivered`.

- Пример пустого файла: [`config/active_containers.example.json`](../config/active_containers.example.json).

### Пример в каталоге

```yaml
5001:
  type: container
  name: "Стартовый набор"
  container: SeaChest
  items:
    - class: AKM
      qty: 1
      attachments: [Mag_AKM_30Rnd]
    - class: Money_Ruble500
      qty: 2

5020:
  type: container
  name: "Тест: бочка"
  container: Barrel_Green
  items:
    - class: BandageDressing
      qty: 3
```

## vehicle — техника по взгляду

Подходит для: машин, лодок, вертолётов (например `RFFSHeli_*` на Cherno).

Контейнер **не подходит** — техника спавнится как entity в мире.

### Поведение

1. Игрок выбирает покупку с типом `vehicle`.
2. Сервер вычисляет точку: **позиция глаз + направление взгляда × distance_m**.
3. Ориентация: yaw игрока (машина смотрит туда же).
4. Проверки (все должны пройти):
   - raycast — нет препятствия на пути;
   - поверхность — не вода (если не лодка), допустимый склон;
   - нет объектов в радиусе `check_radius_m`;
   - не внутри постройки / зелёной зоны торговца (опционально, настраивается).
5. **Успех** → spawn vehicle, attachments, `cargo_items` (ключи и лут из каталога) → **сразу** `operation_success`.
6. **Неудача** → сообщение игроку («Отойдите в открытое место»), покупка **остаётся** в очереди.

### Когда закрывать покупку

Для техники: **`operation_success` сразу после успешного spawn**, не после посадки в салон. Повторный claim по тому же `operation_id` запрещён.

### Пример в каталоге

Комплектация (`spawn_attachments`) — в [`vehicle_profiles.yaml`](../catalog/vehicle_profiles.yaml) (копия `SpawnAttachments` из Expansion Market `Cars.json`).

```yaml
5010:
  type: vehicle
  name: "ADA 4x4"
  class: OffroadHatchback
  spawn:
    distance_m: 6
    max_slope_deg: 15
    check_radius_m: 2.5
```

Ключ и прочий лут — в [`vehicle_profiles.yaml`](../catalog/vehicle_profiles.yaml) → `cargo_items` (например `ExpansionCarKey`); mod кладёт в cargo техники, при неудаче — в инвентарь игрока (`ApplyCargoItems`). Поле `give_key` в offer **deprecated**.

**Топливо и радиатор:** по умолчанию **полный** бак и радиатор (мод заливает 100%, если в каталоге не задано иное). Переопределение — `fluids` в offer или в `vehicle_profiles.yaml` (коэффициент 0..1, например `fuel: 0.5`).

Для вертолётов — увеличить `distance_m`, `check_radius_m`, добавить `min_clearance_above_m`.

## Выбор покупки (не FIFO)

Если у игрока несколько покупок, он **сам выбирает**, что забрать сейчас:

```
/wargm        → список с номерами
/wargm 2      → забрать покупку №2
```

Причины:

- технику нельзя заспавнить в лесу — игрок забирает её в поле;
- предметы и машину удобно забирать в разное время.

В списке помечать тип: `[Предметы]` / `[Техника]`.

## ClassName

Перед добавлением в каталог проверять:

- [`content/_shared/classnames-catalog.yaml`](../../../content/_shared/classnames-catalog.yaml)
- [`content/economy/market-notes.md`](../../../content/economy/market-notes.md) — валюта только `Money_Ruble*`

При невалидном ClassName — `operation_cancel` на wargm, статус `failed` в Bridge, лог для админа.
