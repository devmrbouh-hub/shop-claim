param(
    [string]$ServerRoot = "",
    [string]$AddonBuilder = $env:DAYZ_ADDON_BUILDER
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\..\release\scripts\_shop-claim-paths.ps1")

if (-not $ServerRoot) {
    $ServerRoot = Get-ChernoRoot
}

& (Join-Path $PSScriptRoot "..\..\mod\scripts\build-pbo.ps1") -ServerRoot $ServerRoot -AddonBuilder $AddonBuilder
