# Copy YAML to Bridge (catalog + tenants/demo) and reload catalog.
param(
    [Parameter(Mandatory = $true)]
    [string]$BridgeRoot,
    [Parameter(Mandatory = $true)]
    [string]$OffersYaml,
    [Parameter(Mandatory = $true)]
    [string]$ProfilesYaml,
    [string]$TenantId = "demo",
    [string]$BridgeUrl = "http://127.0.0.1:8787",
    [string]$AdminSecret = $env:BRIDGE_ADMIN_SECRET
)

$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

$targets = @(
    @{
        Offers   = Join-Path $BridgeRoot "catalog\offers.yaml"
        Profiles = Join-Path $BridgeRoot "catalog\vehicle_profiles.yaml"
    },
    @{
        Offers   = Join-Path $BridgeRoot "tenants\$TenantId\offers.yaml"
        Profiles = Join-Path $BridgeRoot "tenants\$TenantId\vehicle_profiles.yaml"
    }
)

foreach ($pair in @(
        @{ Src = $OffersYaml; Key = "Offers" },
        @{ Src = $ProfilesYaml; Key = "Profiles" }
    )) {
    if (-not (Test-Path $pair.Src)) {
        throw "File not found: $($pair.Src)"
    }
}

foreach ($destSet in $targets) {
    foreach ($key in @("Offers", "Profiles")) {
        $src = if ($key -eq "Offers") { $OffersYaml } else { $ProfilesYaml }
        $dest = $destSet[$key]
        $dir = Split-Path -Parent $dest
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        if (Test-Path $dest) {
            Copy-Item $dest "$dest.bak-$stamp"
        }
        Copy-Item $src $dest -Force
        Write-Host "Copied $src -> $dest"
    }
}

if (-not $AdminSecret) {
    Write-Warning "BRIDGE_ADMIN_SECRET not set — YAML on disk; restart ShopClaimBridge or set secret for reload."
    exit 0
}

$uri = "$($BridgeUrl.TrimEnd('/'))/admin/catalog/reload"
try {
    $resp = Invoke-RestMethod -Method Post -Uri $uri -Headers @{
        "X-Bridge-Admin-Secret" = $AdminSecret
    } -TimeoutSec 30
    Write-Host "Reload OK: $($resp | ConvertTo-Json -Compress)"
} catch {
    Write-Error "Catalog reload failed (YAML already copied): $($_.Exception.Message)"
    exit 1
}
