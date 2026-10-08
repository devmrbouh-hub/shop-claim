# Shop Claim — release package

Сборка и установка на VDS (Windows Server + DayZ Manager).

| Документ | Описание |
|----------|----------|
| [README-INSTALL.txt](README-INSTALL.txt) | Инструкция для админа на хосте |
| [install-config.example.json](install-config.example.json) | Пример конфига install |
| [tools/README.txt](tools/README.txt) | nssm.exe вручную |
| [../docs/deployment.md](../docs/deployment.md) | Полный деплой |

## Dev: собрать zip

```powershell
cd services\shop-claim\release\scripts
.\build-release.ps1
```

**Для VDS-zip всегда полная сборка** — без `-SkipExe` / `-SkipMod`. Skip-флаги оставляют пустые `bridge\` / `mod\` (только dev-итерации). Скрипт проверяет пакет через `Assert-ReleasePackage` перед zip.

Артефакт: `release/dist/ShopClaim-<date>.zip`

Перед сборкой: NSSM 2.24-101 win64 → `tools/nssm.exe` (см. [tools/README.txt](tools/README.txt); `build-release.ps1` скачивает CI zip с retry).

## VDS: установить

```powershell
cd ShopClaim-release\scripts
.\install.ps1 -ConfigPath ..\install-config.example.json
```

DayZ Manager: добавить `@ShopClaim` вручную (батники не меняем).
