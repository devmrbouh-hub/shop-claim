# Client UI (DayZ)

Окно магазина: отдельный client PBO `@ShopClaim_GUI` в разработке, опциональный theme PBO `@ShopClaimTheme` (текстуры `.edds`).

| Артефакт | Назначение |
|----------|------------|
| Server mod | RPC handlers, выдача |
| Client mod | `UIScriptedMenu`, клавиша, CF RPC |
| Theme PBO | `gui/textures/*.edds` — см. [theme-contract.md](theme-contract.md) |

RPC namespace `"ShopClaim"` не менять между client и server mod.

Сборка theme: [client-mod/scripts/deploy-theme.ps1](../client-mod/scripts/deploy-theme.ps1) `-ThemeName ShopClaimTheme`.
