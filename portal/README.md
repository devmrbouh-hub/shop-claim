# ShopClaim Portal

Tenant LK, Provider Admin, and landing for ShopClaim SaaS.

## Structure

- `backend/` — FastAPI (`shop-claim-portal`), port **8790**
- `frontend/` — React + Vite SPA and landing build

## Local dev

**Полный гайд:** [docs/portal-local-dev.md](../docs/portal-local-dev.md) (каталог 7.2, Bridge reload, env, workflow).

```powershell
# Bridge (optional — sync tests, catalog reload)
cd ..\bridge
py -3.12 -m pip install -e ".[dev]"

# Portal API
cd portal\backend
py -3.12 -m pip install -e ".[dev]"
$env:PORTAL_BOOTSTRAP_ADMIN_EMAIL = "admin@example.com"
$env:PORTAL_BOOTSTRAP_ADMIN_PASSWORD = "changeme12345"
$env:PORTAL_BRIDGE_CONFIG_PATH = "D:\path\to\bridge.json"
# Каталог (опционально): $env:PORTAL_CATALOG_ROOT = "D:\Cherno\_local\shop-claim-bridge"
py -3.12 -m shop_claim_portal.main

# Frontend
cd ..\frontend
npm install
npm run dev
```

API: http://127.0.0.1:8790 — UI: http://127.0.0.1:5173 (proxies `/api`).

Итерации локально → `pytest` → деплой на VPS по срезу (не на каждый save). См. [portal-local-dev.md](../docs/portal-local-dev.md).

## Tests

```powershell
cd portal\backend
py -3.12 -m pytest tests -q
```

## Production

See [docs/portal-deployment.md](../docs/portal-deployment.md).

## Landing design

Контент, wireframe, copy deck, дизайн-токены: [docs/landing-spec.md](../docs/landing-spec.md).

## Frontend design stack

- **Tailwind CSS v4** + **shadcn/ui** (New York, dark-only)
- Токены ShopClaim: [`frontend/src/index.css`](frontend/src/index.css)
- Entry HTML (`index.html`, `landing.html`): обязателен `<meta name="viewport" content="width=device-width, initial-scale=1" />` — без него мобильные браузеры рисуют ~980px desktop
- Layouts: `LandingLayout`, `AuthLayout`, `TenantLayout`, `AdminLayout` + `AppShell`
- Toast: sonner · Icons: lucide-react

```powershell
cd frontend
npx shadcn@latest add button   # пример добавления компонента
npm run build                  # SPA → dist/
npm run build:landing          # лендинг → dist-landing/
```
