"""Generate PWA icons for Promptly."""
from PIL import Image, ImageDraw


def make_icon(size: int, path: str, maskable: bool = False) -> None:
    img = Image.new("RGB", (size, size), (10, 10, 15))
    draw = ImageDraw.Draw(img)

    if maskable:
        # Safe zone: content must fit within inner 80%
        pad = int(size * 0.10)
        box = (pad, pad, size - pad, size - pad)
    else:
        box = (0, 0, size, size)

    # Rounded-square accent tile
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tile_draw = ImageDraw.Draw(tile)
    radius = int(size * 0.24)
    tile_draw.rounded_rectangle(box, radius=radius, fill=(139, 124, 246, 255))
    img = Image.alpha_composite(img.convert("RGBA"), tile).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Diamond mark (matches the ◆ logo)
    cx, cy = size / 2, size / 2
    r = size * (0.16 if maskable else 0.22)
    diamond = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    draw.polygon(diamond, fill=(255, 255, 255, 255))

    img.save(path, "PNG")
    print(f"Wrote {path} ({size}x{size}, maskable={maskable})")


if __name__ == "__main__":
    from pathlib import Path

    out = Path(__file__).resolve().parent.parent / "static" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    for s in (192, 512):
        make_icon(s, str(out / f"icon-{s}.png"))
        make_icon(s, str(out / f"icon-maskable-{s}.png"), maskable=True)
