#!/usr/bin/env python3
"""Build shop_claim_buttons.png (1024x256) for ImageToPAA -> edds atlas."""
from pathlib import Path

from PIL import Image

TEXTURES = Path(__file__).resolve().parents[1] / "ShopClaim_GUI" / "gui" / "textures"
ATLAS_W, ATLAS_H = 1024, 256
SLOT_W = ATLAS_W // 3
BUTTONS = ("claim_button", "refresh_button", "close_button")


def export_via_texview(edds: Path, png: Path, texview: Path) -> bool:
    if png.exists():
        return True
    if not texview.exists():
        return False
    import subprocess

    for args in (
        [str(texview), "-convert", str(edds), str(png)],
        [str(texview), str(edds), str(png)],
    ):
        try:
            subprocess.run(args, check=True, timeout=30)
            if png.exists():
                return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return False


def load_button_image(name: str, texview: Path) -> Image.Image:
    edds = TEXTURES / f"{name}.edds"
    export_png = TEXTURES / f"_{name}.png"
    if export_via_texview(edds, export_png, texview):
        return Image.open(export_png).convert("RGBA")
    return Image.new("RGBA", (200, 200), (0, 0, 0, 0))


def main() -> None:
    texview = Path(r"C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools\Bin\ImageToPAA\TexView.exe")
    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    for i, name in enumerate(BUTTONS):
        im = load_button_image(name, texview)
        x = i * SLOT_W + (SLOT_W - im.width) // 2
        y = (ATLAS_H - im.height) // 2
        atlas.paste(im, (x, y), im)
    out = TEXTURES / "shop_claim_buttons.png"
    atlas.save(out)
    print(f"Wrote {out} ({ATLAS_W}x{ATLAS_H})")


if __name__ == "__main__":
    main()
