Shop Claim — установка на VDS (Windows Server)
==================================================

Требования
----------
- Windows Server с DayZ Manager (батники не трогаем)
- Распаковать zip на хост (RDP)
- @ShopClaim подключаете в DayZ Manager вручную

Структура пакета
----------------
bridge\          shop-claim-bridge.exe + _internal
catalog\         offers.yaml, vehicle_profiles.yaml
mod\@ShopClaim\   PBO для serverMod
config\          шаблоны bridge/mod
tools\nssm.exe   служба Windows (NSSM 2.24-101 win64; см. tools\README.txt если нет в zip)
scripts\         install.ps1, upgrade.ps1, uninstall.ps1

Установка (первый раз)
----------------------
1. Распаковать ShopClaim-*.zip
2. PowerShell от администратора:
   cd <распакованный>\ShopClaim-release\scripts
   .\install.ps1
   или:
   .\install.ps1 -ConfigPath ..\install-config.example.json

3. Ответить на вопросы:
   - Путь Bridge (например D:\GameServices\ShopClaimBridge)
   - shop_id и api_key wargm (api_base: https://api.wargm.ru/v1.1/shop)
   - На каждый инстанс: server_id, shop_server_id, ServerRoot, ProfilesDir

4. В DayZ Manager:
   - Добавить @ShopClaim (путь = ServerRoot из install)
   - Profiles = ProfilesDir из install
   - Server mods: несколько через точку с запятой (;), НЕ запятую
     Пример: @Mod1;@Mod2;@ShopClaim
   - Перезапустить сервер

Bridge слушает только 127.0.0.1:8787 — порт в интернет не открывать.

Обновление
----------
Распаковать новый zip поверх или рядом, из scripts\:

  .\upgrade.ps1 -ModOnly      только PBO (Bridge не останавливается)
  .\upgrade.ps1 -BridgeOnly   exe + каталог (краткий stop службы)
  .\upgrade.ps1               всё

DayZ Manager сам перезапустит серверы при смене PBO.

Рестарт DayZ каждые 4 часа
---------------------------
Bridge работает как служба Windows (NSSM) отдельно от DayZ.
Рестарт серверов Manager не останавливает Bridge.

Каталог (Excel на ПК админа)
----------------------------
См. docs\self-hosted-catalog-workflow.md в этом пакете (папка docs\).
На VDS после копирования offers.yaml:
  scripts\publish-catalog-to-bridge.ps1 -BridgeRoot D:\GameServices\ShopClaimBridge ...
Требуется BRIDGE_ADMIN_SECRET в env службы NSSM.

Проверка
--------
  Invoke-RestMethod http://127.0.0.1:8787/health
  -> status=ok

Логи Bridge: <bridgePath>\logs\stdout.log

Удаление службы
---------------
  .\uninstall.ps1
  .\uninstall.ps1 -RemoveBridgeData   (опционально удалить папку Bridge)

Секреты
-------
bridge.json с ключами wargm не коммитить в git.
При повторном install.ps1 токены и bridge.json сохраняются.
-RegenerateTokens — новые api_token для модов.
