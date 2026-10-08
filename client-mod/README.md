# Client mod (GUI + theme)

| PBO | Назначение |
|-----|------------|
| `@ShopClaim_GUI` | Меню магазина (dev) |
| `@ShopClaimTheme` | Текстуры `.edds` — [docs/theme-contract.md](../docs/theme-contract.md) |

```powershell
.\client-mod\scripts\deploy-theme.ps1 -ThemeName ShopClaimTheme
```

Демо offer id в каталоге: `5001` (container), `5010` (vehicle). Mock: [bridge/scripts/create-mock-orders.ps1](../bridge/scripts/create-mock-orders.ps1).
