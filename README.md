# ShopClaim (public snapshot)

SaaS для автовыдачи покупок с [wargm.ru](https://wargm.ru) на сервер DayZ: **Bridge** (очередь заказов, API), **server mod** + **client GUI**, **Portal** (личные кабинеты, подписка, интеграция с ЮKassa).

Это open-source снимок без прод-хостинга и без персональных данных оператора. Каноническая разработка ведётся в приватном репозитории; сюда попадают ручные релизы.

## Схема

```
wargm.ru (покупка) → Bridge (poll/API) → Server mod → игрок в игре
                              ↑
                    Portal (ЛК, каталог, биллинг)
```

## Стек

- Python 3.12+, FastAPI, SQLite
- React + Vite (Portal UI и лендинг)
- DayZ server/client mods (Enforce Script)

## Быстрый старт

**Bridge**

```powershell
cd bridge
py -3.12 -m pip install -e ".[dev]"
py -3.12 -m pytest -q
```

Скопируйте `config/bridge.example.json` → `bridge/bridge.json` (файл в gitignore).

**Portal**

```powershell
cd portal\backend
py -3.12 -m pip install -e ".[dev]"
copy .env.example .env
py -3.12 -m pytest tests -q
py -3.12 -m shop_claim_portal.main
```

```powershell
cd portal\frontend
npm install
npm run build
```

Подробнее: [docs/portal-local-dev.md](docs/portal-local-dev.md).

**Mod** — см. [mod/README.md](mod/README.md) (нужен `CHERNO_ROOT` или свой инстанс DayZ).

## Документация

| Файл | Содержание |
|------|------------|
| [docs/architecture.md](docs/architecture.md) | Bridge + mod, статусы заказов |
| [docs/saas-overview.md](docs/saas-overview.md) | Модель SaaS |
| [docs/billing-overview.md](docs/billing-overview.md) | Биллинг и ЮKassa (sandbox) |
| [bridge/README.md](bridge/README.md) | Запуск Bridge |
| [portal/README.md](portal/README.md) | Portal API + UI |

## Безопасность

См. [SECURITY.md](SECURITY.md). Платёжные и API-ключи — только через переменные окружения.

## Лицензия

MIT — см. [LICENSE](LICENSE).
