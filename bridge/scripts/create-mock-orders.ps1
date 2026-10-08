param(
    [string]$SteamId = "76561198000000001",
    [string]$ServerId = "demo_server_alpha",
    [int]$ShopClaimServerId = 10001,
    [int[]]$OfferIds = @(5001, 5010)
)

$ErrorActionPreference = "Stop"
$uri = "http://127.0.0.1:8787/dev/mock-operation"

foreach ($offerId in $OfferIds) {
    $body = @{
        steam_id        = $SteamId
        offer_id        = $offerId
        shop_server_id = $ShopClaimServerId
        server_id       = $ServerId
    } | ConvertTo-Json
    Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType "application/json"
    Write-Host "Mock operation offer_id=$offerId"
}
