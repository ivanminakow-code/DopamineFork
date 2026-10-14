# Synapse JB branding

Artwork for the fork lives here. Drop masters in, run the generator, commit the
resulting asset changes.

```
branding/icons/icon.png            1024x1024  opaque square
branding/icons/icon-default.png    1024x1024  optional per-theme override
branding/icons/icon-blue.png       1024x1024  optional
branding/icons/icon-red.png        1024x1024  optional
branding/icons/icon-purple.png     1024x1024  optional
branding/icons/icon-ellekit.png    1024x1024  optional
branding/logo/logo.png             transparent wordmark, ~5:1, any width >= 609
branding/logo/logo-square.png      transparent square overlay, >= 1050x1050
```

## Regenerate

```sh
python -m pip install Pillow
python tools/generate_icons.py
```

Flags:

- `--no-1024` leaves the 1024x1024 marketing slot empty (upstream ships it empty)
- `--only AppIcon_Blue` limits the run to one `appiconset`, repeatable

Missing masters are skipped with a warning, so the script is safe to run in CI
before the artwork exists.

## Rules that matter

App icons are flattened to opaque RGB on purpose. iOS applies the squircle mask
itself, so a transparent master produces dark corners on the home screen.

Do not bake rounded corners or a drop shadow into the 1024 master -- iOS adds
both. Keep the glyph inside the centre ~80% so it survives the mask.

The wordmark and the square overlay must keep their alpha channel; they are
composited over the theme background at runtime.

## What the generator touches

| Path | What |
|---|---|
| `Assets.xcassets/AppIcon.appiconset` | default icon |
| `Assets.xcassets/AppIcon_{Blue,Red,Purple,ElleKit}.appiconset` | the four theme icons |
| `Assets.xcassets/Dopamine.imageset` | wordmark in the main view header |
| `Assets.xcassets/DopamineLogo.imageset` | 350x350pt PDF overlay drawn on the theme background |

Each `appiconset` gets the full 15-slot grid plus an optional 1024 marketing
icon. The generator also drops `Icon-Small-40@3x 1.png`, a leftover Finder
duplicate from upstream that had been standing in for the missing
`Icon-60@2x.png` slot.
