# Portal local dev

```powershell
cd portal\backend
copy .env.example .env
py -3.12 -m pip install -e ".[dev]"
py -3.12 -m shop_claim_portal.main
```

```powershell
cd portal\frontend
npm install
npm run dev
```

## Каталог Bridge

`PORTAL_CATALOG_ROOT` — корень с `tenants/<tenant_id>/offers.yaml`.

Пример:

```text
catalog-root/
  tenants/
    demo/
      offers.yaml
      vehicle_profiles.yaml
```

Admin → tenant с `tenant_id` = `demo` (имя папки в `tenants/`).

См. [billing-overview.md](billing-overview.md).
