$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\..\release\scripts\_shop-claim-paths.ps1")

$ServiceRoot = Get-ShopClaimServiceRoot -FromDir $PSScriptRoot
$ChernoRoot = Get-ChernoRoot

$srcPng = Join-Path $ChernoRoot "services\STORE_MENU\imagesets\store_menu.png"
$outDir = Join-Path $ServiceRoot "client-mod\ShopClaimTheme\gui\textures"
$paddedPng = Join-Path $outDir "store_menu_padded.png"
$edds = Join-Path $outDir "store_menu.edds"
$packer = Join-Path $PSScriptRoot "tools\imageset-packer.exe"

if (-not (Test-Path $srcPng)) {
    throw "Source not found: $srcPng (set CHERNO_ROOT if Cherno is not at D:\Cherno)"
}
if (-not (Test-Path $packer)) {
    throw "imageset-packer not found: $packer (download v0.1.3 windows-amd64.exe)"
}

$python = @"
from PIL import Image
from pathlib import Path
src = Path(r'$srcPng')
out = Path(r'$paddedPng')
im = Image.open(src).convert('RGBA')
canvas = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
canvas.paste(im, ((1024 - im.width) // 2, (1024 - im.height) // 2), im)
canvas.save(out)
print('Wrote', out)
"@

python -c $python
& $packer convert $paddedPng $edds -F dxt5 -q 8 -x 1
Remove-Item -Force $paddedPng -ErrorAction SilentlyContinue

Write-Host "Built $edds"
