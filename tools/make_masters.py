#!/usr/bin/env python3
"""Turn a single logo into the five themed icon masters.

Reads one square logo and writes branding/icons/icon-<theme>.png for every
Dopamine theme, with the logo sitting on that theme's background gradient.

Only the *outer* white is removed. The white enclosed by the logo's own
strokes is left alone, which is what keeps a gradient-stroked mark readable
against a coloured background -- recolouring the interior would dissolve the
mark into the theme.

The background gradients are sampled from the upstream icon set so the new
icons sit in the same palette as the in-app themes.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent
BRANDING = REPO / "branding"

CANVAS = 1024
CONTENT_FRACTION = 0.86
NEAR_WHITE = 232

# DopamineLogo is drawn at 350x350pt, so the cutout needs ~1050px.
OVERLAY_PX = 1050

# (from, to) sampled from the upstream appiconsets: darker top-left,
# lighter bottom-right.
THEME_GRADIENTS = {
    "default": ((0x01, 0x56, 0x72), (0x13, 0xBF, 0x94)),
    "blue": ((0x00, 0x63, 0xE7), (0x17, 0xBB, 0xF1)),
    "red": ((0xD3, 0x1B, 0x1E), (0xFF, 0x69, 0x39)),
    "purple": ((0x6E, 0x2A, 0xDE), (0x7F, 0x89, 0xFF)),
    "ellekit": ((0xF4, 0x70, 0xF9), (0xEE, 0xB3, 0xFF)),
}


def outer_white_alpha(img, flat=False):
    """Alpha mask for the logo.

    Default floods in from the border only, so white enclosed by the logo's
    own strokes survives. flat=True drops every near-white pixel instead.
    """
    rgb = img.convert("RGB")
    w, h = rgb.size

    near = Image.new("L", (w, h), 0)
    near.putdata([255 if min(p) >= NEAR_WHITE else 0 for p in rgb.getdata()])
    if flat:
        alpha = near.point(lambda v: 0 if v == 255 else 255)
        return rgb, alpha

    filled = near.copy()
    border = ([(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
              + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)])
    for pt in border:
        if filled.getpixel(pt) == 255:
            ImageDraw.floodfill(filled, pt, 128, thresh=0)

    # 128 == reached from outside; everything else stays opaque.
    alpha = filled.point(lambda v: 0 if v == 128 else 255)
    return rgb, alpha


def diagonal_gradient(size, start, end):
    """Linear gradient along the top-left to bottom-right diagonal."""
    w, h = size
    img = Image.new("RGB", (w, h))
    data = []
    denom = float((w - 1) + (h - 1)) or 1.0
    for y in range(h):
        for x in range(w):
            t = (x + y) / denom
            data.append(tuple(round(start[c] + (end[c] - start[c]) * t) for c in range(3)))
    img.putdata(data)
    return img


def fit_on_canvas(logo, fraction=CONTENT_FRACTION):
    """Crop to content, scale it, centre it on an empty canvas."""
    bbox = logo.getbbox()
    if not bbox:
        raise SystemExit("logo is entirely transparent")
    logo = logo.crop(bbox)

    target = round(CANVAS * fraction)
    scale = target / max(logo.size)
    resized = logo.resize((max(1, round(logo.width * scale)),
                           max(1, round(logo.height * scale))), Image.LANCZOS)

    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.paste(resized, ((CANVAS - resized.width) // 2,
                           (CANVAS - resized.height) // 2), resized)
    return canvas


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flat = "--flat" in sys.argv
    if not args:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} <logo.png> [--flat]")
    src = Path(args[0])
    if not src.is_file():
        raise SystemExit(f"{src}: not found")

    rgb, alpha = outer_white_alpha(Image.open(src), flat=flat)
    logo = fit_on_canvas(rgb.convert("RGBA"))
    hard = alpha.resize(logo.size, Image.LANCZOS).point(lambda v: 255 if v > 127 else v)
    logo.putalpha(hard)

    outdir = BRANDING / "icons"
    outdir.mkdir(parents=True, exist_ok=True)

    for theme, (start, end) in THEME_GRADIENTS.items():
        bg = diagonal_gradient((CANVAS, CANVAS), start, end)
        out = bg.convert("RGBA")
        out.alpha_composite(logo)
        out = out.convert("RGB")  # iOS app icons must be opaque
        path = outdir / f"icon-{theme}.png"
        out.save(path, "PNG", optimize=True)
        print(f"{theme:8} #{start[0]:02X}{start[1]:02X}{start[2]:02X}"
              f"->#{end[0]:02X}{end[1]:02X}{end[2]:02X}  ->  {path.name}")

    # The same cutout also drives the 350x350pt overlay drawn over the theme
    # background inside the app, so keep it transparent and generously sized.
    overlay = BRANDING / "logo" / "logo-square.png"
    overlay.parent.mkdir(parents=True, exist_ok=True)
    cutout = logo.crop(logo.getbbox()) if logo.getbbox() else logo
    scale = OVERLAY_PX / max(cutout.size)
    cutout = cutout.resize((max(1, round(cutout.width * scale)),
                            max(1, round(cutout.height * scale))), Image.LANCZOS)
    # Square transparent canvas: DopamineLogo is drawn at 350x350pt, so the
    # raster must be square too or the letter gets squashed.
    square = Image.new("RGBA", (OVERLAY_PX, OVERLAY_PX), (0, 0, 0, 0))
    square.paste(cutout, ((OVERLAY_PX - cutout.width) // 2,
                          (OVERLAY_PX - cutout.height) // 2), cutout)
    square.save(overlay, "PNG", optimize=True)
    print(f"{'overlay':8} {cutout.width}x{cutout.height} on square {OVERLAY_PX} -> {overlay.name}")

    preview = Path(args[0]).parent / ("synapse-preview-flat.png" if flat else "synapse-preview.png")
    tile = CANVAS // 4
    strip = Image.new("RGB", (tile * len(THEME_GRADIENTS), tile))
    for i, theme in enumerate(THEME_GRADIENTS):
        with Image.open(outdir / f"icon-{theme}.png") as im:
            strip.paste(im.resize((tile, tile), Image.LANCZOS), (i * tile, 0))
    strip.save(preview)
    print(f"\nmode   : {'flat (all white removed)' if flat else 'outer flood (inner white kept)'}")
    print(f"preview: {preview}")


if __name__ == "__main__":
    main()
