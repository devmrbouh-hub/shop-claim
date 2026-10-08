# WarGM Bridge — сборка exe (Windows)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BridgeRoot = Split-Path -Parent $Root

Push-Location $BridgeRoot
try {
    $env:HTTP_PROXY = $null
    $env:HTTPS_PROXY = $null
    $env:ALL_PROXY = $null
    $env:http_proxy = $null
    $env:https_proxy = $null
    $env:all_proxy = $null

    $pyinstallerCmd = $null
    if (Test-Path (Join-Path $BridgeRoot ".venv\Scripts\pyinstaller.exe")) {
        $pyinstallerCmd = Join-Path $BridgeRoot ".venv\Scripts\pyinstaller.exe"
    } else {
        $globalPi = Get-Command pyinstaller -ErrorAction SilentlyContinue
        if ($globalPi) { $pyinstallerCmd = $globalPi.Source }
    }

    if (-not $pyinstallerCmd) {
        if (-not (Test-Path ".venv")) {
            python -m venv .venv
        }
        $pip = Join-Path $BridgeRoot ".venv\Scripts\pip.exe"
        $ErrorActionPreference = "Continue"
        & $pip install pyinstaller fastapi "uvicorn[standard]" httpx aiosqlite pyyaml pydantic
        $ErrorActionPreference = "Stop"
        $pyinstallerCmd = Join-Path $BridgeRoot ".venv\Scripts\pyinstaller.exe"
    }
    if (-not (Test-Path $pyinstallerCmd)) {
        throw "pyinstaller not found; install globally: pip install pyinstaller"
    }

  $excludes = @(
    "PyQt5", "PySide6", "matplotlib", "IPython", "pytest", "jedi", "zmq",
    "tkinter", "pygments", "nbformat", "jsonschema", "PIL", "numpy", "pygame"
  )
  $excludeArgs = foreach ($m in $excludes) { "--exclude-module=$m" }

  & $pyinstallerCmd --noconfirm --name shop-claim-bridge --onedir `
    --collect-submodules shop_claim_bridge `
    --hidden-import=uvicorn.logging `
    --hidden-import=uvicorn.loops.auto `
    --hidden-import=uvicorn.loops.asyncio `
    --hidden-import=uvicorn.lifespan.on `
    --hidden-import=uvicorn.protocols.http.auto `
    --hidden-import=uvicorn.protocols.http.h11_impl `
    --hidden-import=uvicorn.protocols.websockets.auto `
    --hidden-import=uvicorn.lifespan.on `
    --hidden-import=yaml `
    --hidden-import=aiosqlite `
    @excludeArgs `
    shop_claim_bridge/main.py

  $exe = Join-Path $BridgeRoot "dist\shop-claim-bridge\shop-claim-bridge.exe"
  if (-not (Test-Path $exe)) {
    throw "Build failed: $exe not found"
  }
  Write-Host "Built: $exe ($((Get-Item $exe).Length) bytes)"
  Write-Host "Deploy: exe + _internal + bridge.json + catalog/ + data/"
}
finally {
    Pop-Location
}
