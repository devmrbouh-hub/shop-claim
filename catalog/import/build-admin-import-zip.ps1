# Assemble admin catalog import zip into catalog/import/
param(
    [string]$OffersYaml = "",
    [string]$ProfilesYaml = "",
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$ImportDir = $PSScriptRoot
if (-not $Version) {
    $Version = Get-Date -Format "yyyy.MM.dd"
}

$chernoRoot = $env:CHERNO_ROOT
if (-not $chernoRoot) { $chernoRoot = "D:\Cherno" }
$chernoStaging = Join-Path $chernoRoot "_bridge_vps_staging"
if (-not $OffersYaml) {
    $OffersYaml = Join-Path $chernoStaging "tenants\demo\offers.yaml"
}
if (-not $ProfilesYaml) {
    $ProfilesYaml = Join-Path $chernoStaging "tenants\demo\vehicle_profiles.yaml"
}
if (-not (Test-Path $OffersYaml)) {
    $OffersYaml = Join-Path $ImportDir "..\offers.yaml"
    $ProfilesYaml = Join-Path $ImportDir "..\vehicle_profiles.yaml"
}

$packName = "ShopClaim-catalog-import-$Version"
$staging = Join-Path $ImportDir "_pack_staging\$packName"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Force -Path $staging, (Join-Path $staging "current-yaml"), (Join-Path $staging "output") | Out-Null

Write-Host "==> export Excel from $OffersYaml"
& python (Join-Path $ImportDir "export-offers-to-xlsx.py") `
    --offers $OffersYaml `
    --profiles $ProfilesYaml `
    -o (Join-Path $staging "offers-demo.xlsx")

Copy-Item $OffersYaml (Join-Path $staging "current-yaml\offers.yaml") -Force
Copy-Item $ProfilesYaml (Join-Path $staging "current-yaml\vehicle_profiles.yaml") -Force

foreach ($name in @(
        "import-offers-from-xlsx.py",
        "export-offers-to-xlsx.py",
        "build-offers-template.py",
        "publish-catalog-to-bridge.ps1",
        "requirements.txt",
        "ADMIN-README.txt",
        "README.md"
    )) {
    Copy-Item (Join-Path $ImportDir $name) $staging -Force
}

New-Item -ItemType File -Path (Join-Path $staging "output\.gitkeep") -Force | Out-Null

$zipPath = Join-Path $ImportDir "$packName.zip"
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path $staging -DestinationPath $zipPath -Force
Remove-Item -Recurse -Force (Split-Path $staging -Parent)

Write-Host "Zip: $zipPath"
