Shop Claim — Bridge only (self-hosted)
======================================

Без server mod на этом хосте: только Bridge + каталог YAML.

Содержимое
----------
bridge\              Python Bridge (или собранный exe)
config\bridge.json   ваш конфиг (скопируйте из config/bridge.example.json)
tenants\demo\        пример каталога per-tenant (offers.yaml, vehicle_profiles.yaml)
catalog\             общий каталог для single-tenant режима
data\orders.db       создаётся при первом запуске
scripts\             установка службы Windows (см. bridge/README.md)

Установка
---------
1. Распаковать на game VDS или отдельный хост рядом с DayZ.
2. Настроить bridge.json и catalog/offers.yaml.
3. Запустить Bridge на 127.0.0.1:8787 (или за reverse proxy).
4. В config.json server mod указать bridge_url и api_token.

См. docs/architecture.md и bridge/README.md.
