# Billing overview (Portal)

Tenant subscription for ShopClaim (Bridge access, catalog editor, support). **Not** the same as player payments on wargm.ru.

## Flow

1. Tenant chooses plan in the cabinet (server slots / unlimited tier).
2. `POST /api/tenant/billing/checkout` creates a YooKassa payment (sandbox or live via env).
3. Webhook `POST /api/billing/yookassa/webhook` verifies payment via YooKassa API and extends subscription.
4. Optional `POST /api/tenant/billing/reconcile` after return URL.

## Environment

| Variable | Purpose |
|----------|---------|
| `PORTAL_YOOKASSA_SHOP_ID` | Shop ID |
| `PORTAL_YOOKASSA_SECRET_KEY` | Secret key |
| `PORTAL_BILLING_PRICE_PER_SERVER_RUB` | Seed price for first DB init |

Configure webhook URL in your YooKassa cabinet to match your deployed `public_url` (not included in this repo).

## Local development

Use YooKassa test keys. Do not enable billing on a public host without TLS, CORS lockdown, and rotated secrets.
