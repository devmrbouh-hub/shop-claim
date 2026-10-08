param(
    [string]$ProfilesDir = "",
    [string]$ApiToken = "test-token-1"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\..\release\scripts\_shop-claim-paths.ps1")

$ServiceRoot = Get-ShopClaimServiceRoot -FromDir $PSScriptRoot
if (-not $ProfilesDir) {
    $ProfilesDir = Join-Path (Get-ChernoRoot) "Instance_1"
}

$example = Join-Path $ServiceRoot "config\mod.example.json"
$destDir = Join-Path $ProfilesDir "ShopClaim"
$destFile = Join-Path $destDir "config.json"

if (-not (Test-Path $example)) {
    throw "Missing mod.example.json"
}

New-Item -ItemType Directory -Force -Path $destDir | Out-Null

$content = Get-Content -LiteralPath $example -Raw -Encoding UTF8
$content = $content -replace '"api_token"\s*:\s*"[^"]*"', "`"api_token`": `"$ApiToken`""

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($destFile, $content, $utf8NoBom)

Write-Host "Wrote $destFile"
