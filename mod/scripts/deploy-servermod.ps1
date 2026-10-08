param(
    [string]$ServerRoot = "",
    [string]$AddonBuilder = $env:DAYZ_ADDON_BUILDER
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\..\release\scripts\_shop-claim-paths.ps1")

if (-not $ServerRoot) {
    $ServerRoot = Get-ChernoRoot
}

$ServiceRoot = Get-ShopClaimServiceRoot -FromDir $PSScriptRoot
$modSource = Join-Path $ServiceRoot "mod\ShopClaim"
$modDest = Join-Path $ServerRoot "@ShopClaim"
$addonsDest = Join-Path $modDest "addons"
$pboName = "ShopClaim.pbo"
$pboPath = Join-Path $addonsDest $pboName
$templateModCpp = Join-Path $ServiceRoot "mod\templates\mod.cpp"

$defaultBuilder = "C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe"
if (-not $AddonBuilder -and (Test-Path $defaultBuilder)) {
    $AddonBuilder = $defaultBuilder
}

if (-not (Test-Path $modSource)) {
    throw "Mod sources not found: $modSource"
}

New-Item -ItemType Directory -Force -Path $addonsDest | Out-Null
Copy-Item -Force $templateModCpp (Join-Path $modDest "mod.cpp")

# Remove stale loose / wrong layouts from earlier deploys
$looseDest = Join-Path $addonsDest "ShopClaim"
if (Test-Path $looseDest) {
    Remove-Item -Recurse -Force $looseDest
}
$wrongPboDir = Join-Path $addonsDest "ShopClaim.pbo"
if ((Test-Path $wrongPboDir) -and (Get-Item $wrongPboDir).PSIsContainer) {
    $nestedPbo = Join-Path $wrongPboDir $pboName
    if (Test-Path $nestedPbo) {
        Move-Item -Force $nestedPbo $pboPath
    }
    Remove-Item -Recurse -Force $wrongPboDir
}

$includeFile = Join-Path $PSScriptRoot "addonbuilder-includes.txt"
if (-not (Test-Path $includeFile)) {
    throw "AddonBuilder include list not found: $includeFile"
}

$built = $false
if ($AddonBuilder -and (Test-Path $AddonBuilder)) {
    Write-Host "Building PBO via Addon Builder..."
    Write-Host "  source:  $modSource"
    Write-Host "  dest:    $addonsDest"
    Write-Host "  include: $includeFile"
    & $AddonBuilder $modSource $addonsDest -packonly -clear -prefix=ShopClaim "-include=$includeFile"
    if (Test-Path $pboPath) {
        $built = $true
        $size = (Get-Item $pboPath).Length
        Write-Host "Built $pboPath ($size bytes)"
    }
}

if (-not $built) {
    throw @"
ShopClaim.pbo was not created at: $pboPath
Install DayZ Tools or set DAYZ_ADDON_BUILDER to AddonBuilder.exe.
Loose folders in addons/ are NOT loaded by dedicated server.
"@
}

Write-Host "Deployed server mod folder: $modDest"
