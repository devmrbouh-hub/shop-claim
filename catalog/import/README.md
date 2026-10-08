# Импорт каталога (Excel → YAML)

Скрипты для офлайн-редактирования `offers.yaml` и `vehicle_profiles.yaml`.

## Быстрый старт

```powershell
cd catalog\import
py -3.12 build-offers-template.py -o offers-template.xlsx
py -3.12 import-offers-from-xlsx.py --input offers-template.xlsx
```

Демо offer id в шаблоне: `5001` (container), `5010` (vehicle). Shop server id в справочнике: `10001`–`10003`.

## publish-catalog-to-bridge.ps1

Копирует YAML в `BridgeRoot\catalog\` и `BridgeRoot\tenants\demo\`, затем `POST /admin/catalog/reload`.

```powershell
.\publish-catalog-to-bridge.ps1 -BridgeRoot C:\ShopClaim\Bridge -OffersYaml ..\..\catalog\offers.yaml -ProfilesYaml ..\..\catalog\vehicle_profiles.yaml -TenantId demo
```

## Тесты

`bridge/tests/test_import_catalog.py` — интеграционный импорт (требует `CHERNO_ROOT` с Expansion Market; иначе skip).
