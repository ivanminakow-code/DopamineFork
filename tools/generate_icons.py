#!/usr/bin/env python3
"""Generate Synapse JB artwork from master images.

Reads opaque 1024x1024 square masters from branding/icons/ and writes every
appiconset slot. Also regenerates the in-app logo assets.

Layout expected on disk:

    branding/icons/icon.png              -> used for every theme that has no
                                            dedicated master
    branding/icons/icon-<theme>.png      -> per-theme override
                                            (default, blue, red, purple, ellekit)
    branding/logo/logo.png               -> in-app wordmark, transparent
    branding/logo/logo-square.png        -> 350x350pt overlay, transparent

Anything missing is skipped with a warning, so this script is safe to run in CI
before the artwork exists.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  python -m pip install Pillow")

REPO = Path(__file__).resolve().parent.parent
BRANDING = REPO / "branding"
ASSETS = REPO / "Application" / "Dopamine" / "Assets.xcassets"

APPICONSETS = ("AppIcon", "AppIcon_Blue", "AppIcon_Red", "AppIcon_Purple", "AppIcon_ElleKit")

MASTER_SIZE = 1024

# (size, scale, filename) -- pixel dimensions are derived as int(size * scale).
ICON_SLOTS = [
    ("20x20", "2x", "Icon-Notification@2x.png"),
    ("20x20", "3x", "Icon-Notification@3x.png"),
    ("29x29", "2x", "Icon-Small@2x.png"),
    ("29x29", "3x", "Icon-Small@3x.png"),
    ("38x38", "2x", "Icon-38@2x.png"),
    ("38x38", "3x", "Icon-38@3x.png"),
    ("40x40", "2x", "Icon-Small-40@2x.png"),
    ("40x40", "3x", "Icon-Small-40@3x.png"),
    ("60x60", "2x", "Icon-60@2x.png"),
    ("60x60", "3x", "Icon-60@3x.png"),
    ("64x64", "2x", "Icon-64@2x.png"),
    ("64x64", "3x", "Icon-64@3x.png"),
    ("68x68", "2x", "Icon-68@2x.png"),
    ("76x76", "2x", "Icon-76@2x.png"),
    ("83.5x83.5", "2x", "Icon-83.5@2x.png"),
]

MARKETING_SLOT = ("1024x1024", "Icon-1024.png")

# Stale file left over from a Finder duplicate in the upstream repo.
STALE_ICON_FILES = ("Icon-Small-40@3x 1.png",)

# Dopamine.imageset renders the wordmark at 203pt wide.
LOGO_WIDTHS = (("Dopamine.png", 1), ("Dopamine@2x.png", 2), ("Dopamine@3x.png", 3))
LOGO_BASE_WIDTH = 203

# DOTheme.m draws DopamineLogo at 350x350pt.
LOGO_SQUARE_PT = 350
LOGO_SQUARE_PX = 1050
PDF_RESOLUTION = LOGO_SQUARE_PX / LOGO_SQUARE_PT * 72


def pixel_size(size, scale):
    return round(float(size.split("x")[0]) * int(scale.rstrip("x")))


def setname_to_theme(setname):
    """AppIcon -> default, AppIcon_Blue -> blue. Matches branding/README.md."""
    suffix = setname[len("AppIcon_"):] if setname.startswith("AppIcon_") else ""
    return suffix.lower() or "default"


def theme_master(theme):
    """Per-theme master if present, else the shared one."""
    dedicated = BRANDING / "icons" / f"icon-{theme}.png"
    if dedicated.is_file():
        return dedicated
    return BRANDING / "icons" / "icon.png"


def load_master(path):
    """Open a master, rejecting anything too small to downscale from."""
    img = Image.open(path)
    img.load()
    shortest = min(img.size)
    if shortest < MASTER_SIZE:
        raise SystemExit(f"{path}: master must be at least {MASTER_SIZE}x{MASTER_SIZE}, got {img.size}")
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    return img


def write_png(img, path, flatten_to=None):
    """Write a PNG, optionally compositing onto a solid colour.

    App icons ship fully opaque: iOS applies the squircle mask itself, so a
    transparent master would otherwise show as dark corners.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    out = img
    if flatten_to is not None:
        out = Image.new("RGB", img.size, flatten_to)
        out.paste(img, mask=img.getchannel("A") if img.mode == "RGBA" else None)
    elif img.mode == "RGBA":
        out = Image.new("RGB", img.size, (255, 255, 255))
        out.paste(img, mask=img.getchannel("A"))
    else:
        out = img.convert("RGB")
    out.save(path, "PNG", optimize=True)


def resize_to_width(img, width):
    if img.width == width:
        return img
    height = round(img.height * width / img.width)
    return img.resize((width, height), Image.LANCZOS)


def appicon_contents(with_1024):
    images = []
    for size, scale, filename in ICON_SLOTS:
        images.append(
            {
                "filename": filename,
                "idiom": "universal",
                "platform": "ios",
                "scale": scale,
                "size": size,
            }
        )
    size, filename = MARKETING_SLOT
    marketing = {"idiom": "universal", "platform": "ios", "size": size}
    if with_1024:
        marketing["filename"] = filename
    images.append(marketing)
    return {"images": images, "info": {"author": "xcode", "version": 1}}


def generate_appicons(with_1024, only=None):
    shared = BRANDING / "icons" / "icon.png"
    themes = [setname_to_theme(s) for s in APPICONSETS]
    if not shared.is_file() and not any(
        (BRANDING / "icons" / f"icon-{t}.png").is_file() for t in themes
    ):
        print("warning: no icon masters in branding/icons, skipping app icons")
        return

    for setname in APPICONSETS:
        if only and setname not in only:
            continue
        outdir = ASSETS / f"{setname}.appiconset"
        master = theme_master(setname_to_theme(setname))
        if not master.is_file():
            print(f"warning: no master for {setname}, skipping")
            continue

        base = load_master(master).convert("RGB")
        corner = base.getpixel((0, 0))
        for size, scale, filename in ICON_SLOTS:
            px = pixel_size(size, scale)
            slot = base.resize((px, px), Image.LANCZOS)
            write_png(slot, outdir / filename, flatten_to=corner)

        if with_1024:
            write_png(base, outdir / MARKETING_SLOT[1], flatten_to=corner)

        for stale in STALE_ICON_FILES:
            p = outdir / stale
            if p.is_file():
                p.unlink()

        (outdir / "Contents.json").write_text(
            json.dumps(appicon_contents(with_1024), indent=2) + "\n", encoding="utf-8"
        )
        print(f"{setname}: {len(ICON_SLOTS)} slots from {master.name}")


def generate_wordmark():
    master = BRANDING / "logo" / "logo.png"
    if not master.is_file():
        print("warning: branding/logo/logo.png missing, keeping upstream wordmark")
        return
    img = Image.open(master)
    img.load()
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    outdir = ASSETS / "Dopamine.imageset"
    for filename, scale in LOGO_WIDTHS:
        resized = resize_to_width(img, LOGO_BASE_WIDTH * scale)
        outdir.mkdir(parents=True, exist_ok=True)
        resized.save(outdir / filename, "PNG", optimize=True)
    print(f"wordmark: {LOGO_BASE_WIDTH}pt wide ({img.size} -> {LOGO_BASE_WIDTH * 3}px @3x)")


def generate_square_logo():
    master = BRANDING / "logo" / "logo-square.png"
    if not master.is_file():
        print("warning: branding/logo/logo-square.png missing, keeping upstream overlay")
        return
    img = Image.open(master)
    img.load()
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    resized = img.resize((LOGO_SQUARE_PX, LOGO_SQUARE_PX), Image.LANCZOS)
    out = ASSETS / "DopamineLogo.imageset" / "DopamineLogo.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    # Raster wrapped in a PDF sized so iOS lays it out at exactly 350x350pt.
    out.unlink(missing_ok=True)
    flat = Image.new("RGB", resized.size, (255, 255, 255))
    flat.paste(resized, mask=resized.getchannel("A"))
    flat.save(out, "PDF", resolution=PDF_RESOLUTION)
    print(f"overlay: {LOGO_SQUARE_PX}px raster -> {LOGO_SQUARE_PT}x{LOGO_SQUARE_PT}pt PDF")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-1024",
        action="store_true",
        help="leave the 1024x1024 marketing slot empty",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="SET",
        help="limit to one appiconset, repeatable (AppIcon, AppIcon_Blue, ...)",
    )
    args = parser.parse_args()

    if not BRANDING.is_dir():
        print(f"warning: {BRANDING} does not exist, nothing to do")
        return

    generate_appicons(not args.no_1024, only=args.only)
    generate_wordmark()
    generate_square_logo()


if __name__ == "__main__":
    main()
