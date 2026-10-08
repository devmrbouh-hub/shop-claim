param(
    [string]$ThemeName = "ShopClaimTheme",
    [string]$ServerRoot = "",
    [string]$AddonBuilder = $env:DAYZ_ADDON_BUILDER
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\..\release\scripts\_shop-claim-paths.ps1")

if (-not $ServerRoot) {
    $ServerRoot = Get-ChernoRoot
}

$ServiceRoot = Get-ShopClaimServiceRoot -FromDir $PSScriptRoot
$themeRoots = @{
    "ShopClaimTheme" = Join-Path $ServiceRoot "client-mod\ShopClaimTheme"
}

if (-not $themeRoots.ContainsKey($ThemeName)) {
    throw "Unknown theme: $ThemeName. Valid: $($themeRoots.Keys -join ', ')"
}

$modSource = $themeRoots[$ThemeName]
$modDest = Join-Path $ServerRoot "@$ThemeName"
$addonsDest = Join-Path $modDest "addons"
$pboName = "$ThemeName.pbo"
$pboPath = Join-Path $addonsDest $pboName
$templateModCpp = Join-Path $ServiceRoot "client-mod\theme-template\templates\mod.cpp"

$defaultBuilder = "C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe"
if (-not $AddonBuilder -and (Test-Path $defaultBuilder)) {
    $AddonBuilder = $defaultBuilder
}

if (-not (Test-Path $modSource)) {
    throw "Theme sources not found: $modSource"
}

New-Item -ItemType Directory -Force -Path $addonsDest | Out-Null
Copy-Item -Force $templateModCpp (Join-Path $modDest "mod.cpp")

$includeFile = Join-Path $PSScriptRoot "addonbuilder-includes.txt"
if (-not (Test-Path $includeFile)) {
    throw "AddonBuilder include list not found: $includeFile"
}

$built = $false
if ($AddonBuilder -and (Test-Path $AddonBuilder)) {
    Write-Host "Building theme PBO via Addon Builder..."
    Write-Host "  source:  $modSource"
    Write-Host "  dest:    $addonsDest"
    & $AddonBuilder $modSource $addonsDest -packonly -clear "-include=$includeFile"
    if (Test-Path $pboPath) {
        $built = $true
        Write-Host "Built $pboPath"
    }
}

if (-not $built) {
    throw "Theme PBO was not created at: $pboPath"
}

Write-Host "Deployed theme mod folder: $modDest"
