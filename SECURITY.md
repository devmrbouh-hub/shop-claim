# Security

## Secrets

Never commit:

- `bridge/bridge.json` (WarGM API keys, tenant tokens)
- `portal/backend/data/portal.db` (encrypted shop keys)
- `PORTAL_YOOKASSA_SHOP_ID`, `PORTAL_YOOKASSA_SECRET_KEY`, `PORTAL_JWT_SECRET`, `PORTAL_FERNET_KEY`

Use [portal/backend/.env.example](portal/backend/.env.example) as a template.

## Defaults in code (development only)

- `jwt_secret` in `portal/backend/shop_claim_portal/config.py` is a **dev placeholder**. Set a strong `PORTAL_JWT_SECRET` before any internet-facing deploy.
- Empty `PORTAL_FERNET_KEY` means WarGM keys in the database are not encrypted at rest. Generate a Fernet key for production.

## Public snapshot

This repository intentionally excludes production hostnames, legal documents with personal data, and deployment runbooks. Do not push the private canonical repo history to GitHub.

## Reporting

For this demo snapshot, open a GitHub issue on the public repository.
