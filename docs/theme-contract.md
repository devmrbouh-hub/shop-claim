# Theme PBO contract

Theme mod содержит только ресурсы GUI (`.edds`), без логики.

## Пути

- Исходники: `client-mod/ShopClaimTheme/gui/textures/`
- `config.json` server mod: `gui.theme_prefix` = `ShopClaimTheme`

## Сборка подложки

`client-mod/scripts/build-store-menu-texture.ps1` → `store_menu.edds` (нужен `CHERNO_ROOT` или свой путь к `store_menu.png`).

Затем:

```powershell
.\client-mod\scripts\deploy-theme.ps1 -ThemeName ShopClaimTheme
```

| Имя | Папка в репо | В mod list |
|-----|--------------|------------|
| ShopClaimTheme | `client-mod/ShopClaimTheme` | опционально `-mod=@ShopClaimTheme` |
