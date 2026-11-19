# Author: urumb
"""Generate the app icon (original artwork, drawn in code).

A cream magnifying glass with a green check mark ("audited") on a dark
rounded square, in the UI's colours. Writes:

    desktop/assets/icon.ico   Windows icon (16-256 px) for the exe and installer
    desktop/assets/icon.png   512 px PNG
    frontend/app/icon.png     browser-tab icon for the web UI (Next.js app icon)

    python desktop/make_icon.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
BACKGROUND = (14, 14, 17, 255)     # --card
BORDER = (40, 40, 46, 255)
CREAM = (241, 238, 230, 255)       # --foreground
GREEN = (59, 239, 140, 255)        # --primary

SIZE = 1024  # draw large, then downsample for smooth edges


def draw() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded square tile.
    d.rounded_rectangle([40, 40, SIZE - 40, SIZE - 40], radius=220, fill=BACKGROUND, outline=BORDER, width=12)

    # Magnifying glass: lens ring + handle.
    cx, cy, r = 450, 440, 235
    ring = 58
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=CREAM, width=ring)
    # Handle, from the lens edge toward the bottom-right corner.
    d.line([(cx + 175, cy + 175), (790, 805)], fill=CREAM, width=96)
    d.ellipse([790 - 48, 805 - 48, 790 + 48, 805 + 48], fill=CREAM)  # rounded end

    # Green check mark inside the lens.
    check = [(cx - 108, cy + 12), (cx - 28, cy + 90), (cx + 112, cy - 66)]
    d.line(check, fill=GREEN, width=64, joint="curve")
    for x, y in (check[0], check[-1]):  # rounded line caps
        d.ellipse([x - 32, y - 32, x + 32, y + 32], fill=GREEN)
    return img


def main() -> None:
    big = draw()
    assets = ROOT / "desktop" / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    big.resize((512, 512), Image.LANCZOS).save(assets / "icon.png")
    big.resize((256, 256), Image.LANCZOS).save(
        assets / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    # Next.js serves app/icon.png as the site icon automatically.
    big.resize((256, 256), Image.LANCZOS).save(ROOT / "frontend" / "app" / "icon.png")
    print("wrote", assets / "icon.ico", assets / "icon.png", ROOT / "frontend" / "app" / "icon.png")


if __name__ == "__main__":
    main()
