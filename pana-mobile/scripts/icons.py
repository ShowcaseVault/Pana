"""Generate the Android launcher icons from the app logo.

Android's adaptive icon is two layers -- a background and a foreground -- which
the launcher masks to whatever shape it prefers: a circle, a squircle, a
rounded square.

The source logo is a rounded teal square, artwork on a gradient, with a soft
drop shadow around it. Three things follow:

  * the shadow means the image's bounding box is the whole canvas, so the plate
    is found by opacity instead;
  * the plate's own rounded-square edge must not reach the background layer, or
    the launcher masks a second shape out of the first -- a square visible
    inside a circle -- so the gradient is sampled and repainted edge to edge;
  * the artwork is placed within the safe zone, the inner region no launcher
    mask can crop.

Usage: python3 scripts/icons.py  (or: npm run icons)
"""

import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "public" / "logo-app.png"
RES = ROOT / "android" / "app" / "src" / "main" / "res"

# Launcher icon sizes per density bucket, with the adaptive layer size that
# goes with each: a 108dp layer against a 48dp icon.
DENSITIES = {
    "mdpi": (48, 108),
    "hdpi": (72, 162),
    "xhdpi": (96, 216),
    "xxhdpi": (144, 324),
    "xxxhdpi": (192, 432),
}

# The fraction of an adaptive layer guaranteed to survive any launcher mask.
# The artwork is scaled to sit inside it.
SAFE_ZONE = 0.58

# Alpha at or above this counts as the plate; below it is the drop shadow.
OPAQUE = 250


def plate_box(logo: Image.Image) -> tuple[int, int, int, int]:
    """Return the box of the logo's plate, excluding its drop shadow."""
    width, height = logo.size
    alpha = logo.split()[3]

    columns = [x for x in range(width) if alpha.getpixel((x, height // 2)) >= OPAQUE]
    rows = [y for y in range(height) if alpha.getpixel((width // 2, y)) >= OPAQUE]

    return columns[0], rows[0], columns[-1] + 1, rows[-1] + 1


def gradient_stops(plate: Image.Image) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Return the plate's top and bottom colours.

    Read from a column near the left edge: the artwork occupies the centre, so
    a middle column would sample the book rather than the plate behind it. The
    rounded corners are skipped by starting a tenth of the way down.
    """
    column = int(plate.width * 0.06)
    top = plate.getpixel((column, int(plate.height * 0.10)))[:3]
    bottom = plate.getpixel((column, int(plate.height * 0.90)))[:3]
    return top, bottom


def paint_gradient(
    top: tuple[int, int, int], bottom: tuple[int, int, int], size: int
) -> Image.Image:
    """Paint a vertical gradient between two colours, edge to edge."""
    layer = Image.new("RGB", (size, size))
    pixels = layer.load()
    for y in range(size):
        ratio = y / max(size - 1, 1)
        colour = tuple(round(a + (b - a) * ratio) for a, b in zip(top, bottom, strict=True))
        for x in range(size):
            pixels[x, y] = colour
    return layer.convert("RGBA")


def main() -> None:
    logo = Image.open(SOURCE).convert("RGBA")
    plate = logo.crop(plate_box(logo))
    top, bottom = gradient_stops(plate)

    print(f"plate {plate.width}x{plate.height}")
    print(
        f"gradient #{top[0]:02x}{top[1]:02x}{top[2]:02x} -> #{bottom[0]:02x}{bottom[1]:02x}{bottom[2]:02x}"
    )

    # The artwork sits inside the plate with a margin of its own. Cropping that
    # margin away lets the artwork fill the safe zone rather than floating
    # small inside it.
    inset = int(plate.width * 0.05)
    artwork = plate.crop((inset, inset, plate.width - inset, plate.height - inset))

    for density, (legacy_size, layer_size) in DENSITIES.items():
        folder = RES / f"mipmap-{density}"
        folder.mkdir(parents=True, exist_ok=True)

        # --- Legacy icon, for Android 7 and older: the logo's plate as it is,
        # since those launchers apply no mask and expect a finished shape.
        square = plate.resize((legacy_size, legacy_size), Image.LANCZOS)
        square.save(folder / "ic_launcher.png")
        square.save(folder / "ic_launcher_round.png")

        # --- Adaptive background: the gradient with no shape of its own, so
        # whatever the launcher masks lands on colour.
        paint_gradient(top, bottom, layer_size).save(folder / "ic_launcher_background.png")

        # --- Adaptive foreground: the artwork, centred in the safe zone.
        layer = Image.new("RGBA", (layer_size, layer_size), (0, 0, 0, 0))
        target = int(layer_size * SAFE_ZONE)
        scaled = artwork.resize((target, target), Image.LANCZOS)
        offset = (layer_size - target) // 2
        layer.paste(scaled, (offset, offset), scaled)
        layer.save(folder / "ic_launcher_foreground.png")

        print(f"  {density}: {legacy_size}px legacy, {layer_size}px adaptive")

    # Point the adaptive icon at the image background rather than the flat
    # colour Capacitor generated, so the gradient survives.
    for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
        icon_file = RES / "mipmap-anydpi-v26" / name
        if not icon_file.exists():
            continue
        icon_file.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@mipmap/ic_launcher_background"/>\n'
            '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
            "</adaptive-icon>\n"
        )

    print("adaptive icons point at the image background")


if __name__ == "__main__":
    main()
