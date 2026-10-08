$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\..\release\scripts\_shop-claim-paths.ps1")

$ServiceRoot = Get-ShopClaimServiceRoot -FromDir $PSScriptRoot
$refDir = Join-Path $ServiceRoot "client-mod\design-reference"
$texDir = Join-Path $ServiceRoot "client-mod\ShopClaim_GUI\gui\textures"
$imageToPaa = "C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe"
$texView = "C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\ImageToPAA\TexView.exe"

if (-not (Test-Path $imageToPaa)) {
    throw "ImageToPAA not found: $imageToPaa"
}

$python = @"
from PIL import Image
from pathlib import Path

ref = Path(r'$refDir')
tex = Path(r'$texDir')

buttons = [
    ('\u041a\u043d\u043e\u043f\u043a\u0430 \u0437\u0430\u0431\u0440\u0430\u0442\u044c.jpg', 'claim_button_256.png'),
    ('\u041a\u043d\u043e\u043f\u043a\u0430 \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c.jpg', 'refresh_button_256.png'),
    ('\u041a\u043d\u043e\u043f\u043a\u0430 \u0437\u0430\u043a\u0440\u044b\u0442\u044c.jpg', 'close_button_256.png'),
]

for src, png_name in buttons:
    im = Image.open(ref / src).convert('RGBA')
    canvas = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    canvas.paste(im, ((256 - im.width) // 2, (256 - im.height) // 2), im)
    canvas.save(tex / png_name)

atlas = Image.new('RGBA', (1024, 256), (0, 0, 0, 0))
xs = [0, 384, 768]
for i, (_, png_name) in enumerate(buttons):
    im = Image.open(tex / png_name)
    atlas.paste(im, (xs[i], 0), im)
atlas.save(tex / 'shop_claim_buttons.png')
print('atlas', atlas.size, 'slots', xs)
"@

python -c $python

$atlasPng = Join-Path $texDir "shop_claim_buttons.png"
$atlasPaa = Join-Path $texDir "shop_claim_buttons.paa"
& $imageToPaa $atlasPng $atlasPaa

Write-Host ""
Write-Host "Atlas PAA ready: $atlasPaa"
Write-Host ""
Write-Host "NEXT in TexView (EDDS cannot be opened, only saved from PAA):"
Write-Host "  1. Open shop_claim_buttons.paa"
Write-Host "  2. File -> Save As -> shop_claim_buttons.edds"
Write-Host "  3. Run deploy-clientmod.ps1"
Write-Host ""
Write-Host "Note: existing .edds (store_menu, etc.) do not open in TexView - ENF format."

if (Test-Path $texView) {
    Write-Host "Opening TexView..."
    Start-Process -FilePath $texView -ArgumentList "`"$atlasPaa`""
}
