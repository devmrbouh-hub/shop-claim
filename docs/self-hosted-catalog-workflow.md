# Self-hosted catalog workflow

Редактируется **игровая выдача** (`offers.yaml`), не витрина wargm.

1. Создать товар в ЛК wargm, записать `offer_id`.
2. Добавить оффер в Excel (`catalog/import/build-offers-template.py`) или править YAML напрямую.
3. `python import-offers-from-xlsx.py --input offers-template.xlsx`
4. Скопировать YAML в `BridgeRoot/catalog/` или `tenants/demo/`.
5. `publish-catalog-to-bridge.ps1 -TenantId demo` + reload каталога.

См. [catalog/import/README.md](../catalog/import/README.md).
