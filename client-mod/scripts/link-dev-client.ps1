param(
    [string]$ServerRoot = "",
    [string]$AddonBuilder = $env:DAYZ_ADDON_BUILDER
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\..\release\scripts\_shop-claim-paths.ps1")

if (-not $ServerRoot) {
    $ServerRoot = Get-ChernoRoot
}

& (Join-Path $PSScriptRoot "deploy-clientmod.ps1") -ServerRoot $ServerRoot -AddonBuilder $AddonBuilder

$ServiceRoot = Get-ShopClaimServiceRoot -FromDir $PSScriptRoot
$modSource = Join-Path $ServiceRoot "client-mod\ShopClaim_GUI"
$linkPath = Join-Path $ServerRoot "ShopClaim_GUI"

if (Test-Path $linkPath) {
    $item = Get-Item $linkPath -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        cmd /c rmdir "$linkPath"
    }
    elseif ($item.PSIsContainer) {
        Remove-Item -Recurse -Force $linkPath
    }
}

Write-Host "Creating junction: $linkPath -> $modSource"
cmd /c mklink /J "$linkPath" "$modSource"
Write-Host "Client file patching prefix ready."
