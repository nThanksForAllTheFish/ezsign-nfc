"""Image <-> EZ Sign 2-bit frame buffer.

Pixel format (as implemented for the 2.13" BWRY model in
fossasia/magic-epaper-app, lib/santek/services/santek_image_codec.dart):

  * 2 bits per pixel, palette index 0=black 1=white 2=yellow 3=red
  * MSB first within each byte
  * pixel ORDER differs by panel. The 2.13" (natively 128 wide, portrait)
    uses column-major with x mirrored: bit_pos = ((W-1-x) * H + y) * 2.
    The 4.2" (natively 400 wide) uses row-major with x mirrored:
    bit_pos = (y * W + (W-1-x)) * 2  -- verified on hardware 2026-10-24
    (plain row-major displays a mirror image; column-major is scrambled).
    encode() takes a layout argument; see LAYOUTS.

For 400x300 that is 400*300*2/8 = 30,000 bytes.

Quantization is a plain nearest-RGB match against the four exact palette
colours. By default any pixel that is not already one of those four colours
is an error, so nothing is silently dithered or resampled on the way to the
panel; pass strict=False to allow nearest-colour mapping.
"""
from __future__ import annotations

from PIL import Image

PALETTE = [
    (0, 0, 0),        # 0 black
    (255, 255, 255),  # 1 white
    (255, 255, 0),    # 2 yellow
    (255, 0, 0),      # 3 red
]
BLACK, WHITE, YELLOW, RED = range(4)

MODELS = {
    # name: (width, height, default layout)
    "4.2": (400, 300, "row-mirror"),  # VERIFIED on hardware 2026-10-24
    "2.13": (250, 128, "col-mirror"), # verified by magic-epaper-app
    "2.9": (296, 128, "col-mirror"),  # guess: same native-portrait family as 2.13
}


def _nearest(rgb):
    r, g, b = rgb
    best, best_d = WHITE, 1 << 30
    for i, (pr, pg, pb) in enumerate(PALETTE):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best_d:
            best, best_d = i, d
    return best


LAYOUTS = ("row", "row-mirror", "col", "col-mirror")


def _bitpos(x, y, width, height, layout):
    """Bit position of the pixel at image (x, y) for the given layout."""
    if layout == "row":            # natural raster: y*W + x
        return (y * width + x) * 2
    if layout == "row-mirror":     # raster, x mirrored
        return (y * width + (width - 1 - x)) * 2
    if layout == "col":            # column-major, column x then row y
        return (x * height + y) * 2
    if layout == "col-mirror":     # column-major, x mirrored (2.13" per magic-epaper)
        return ((width - 1 - x) * height + y) * 2
    raise ValueError(f"unknown layout {layout!r}; choose from {LAYOUTS}")


def encode(img: Image.Image, width: int = 400, height: int = 300,
           strict: bool = True, layout: str = "row") -> bytes:
    """Return the 2-bit frame buffer for *img*, which must be width x height.

    layout: how pixels are ordered in the buffer (see LAYOUTS). "col-mirror" is
    what the 2.13" uses; the 4.2" uses "row-mirror" (verified).
    """
    img = img.convert("RGB")
    if img.size != (width, height):
        raise ValueError(f"image is {img.size}, expected {(width, height)}; "
                         "resize deliberately before encoding")
    px = img.load()
    lut = {c: i for i, c in enumerate(PALETTE)}
    buf = bytearray(width * height * 2 // 8)
    for y in range(height):
        for x in range(width):
            rgb = px[x, y]
            idx = lut.get(rgb)
            if idx is None:
                if strict:
                    raise ValueError(
                        f"pixel ({x},{y}) = {rgb} is not one of the four panel "
                        "colours; quantize first or pass strict=False")
                idx = _nearest(rgb)
            bit = _bitpos(x, y, width, height, layout)
            buf[bit >> 3] |= idx << (6 - (bit & 7))
    return bytes(buf)


def decode(buf: bytes, width: int = 400, height: int = 300,
           layout: str = "row") -> Image.Image:
    """Inverse of encode(); useful for round-trip tests and for inspecting dumps."""
    if len(buf) != width * height * 2 // 8:
        raise ValueError(f"buffer is {len(buf)} bytes, expected {width*height*2//8}")
    img = Image.new("RGB", (width, height))
    px = img.load()
    for y in range(height):
        for x in range(width):
            bit = _bitpos(x, y, width, height, layout)
            px[x, y] = PALETTE[(buf[bit >> 3] >> (6 - (bit & 7))) & 3]
    return img


def quantize(img: Image.Image, width: int = 400, height: int = 300) -> Image.Image:
    """Nearest-colour map to the four panel colours, no resampling, no dithering.

    Use this only on images that are already the right size; it exists so the
    CLI can accept an arbitrary-colour PNG with --quantize. Dithering is left
    to the image generator, where it can be checked before it reaches the panel.
    """
    img = img.convert("RGB")
    if img.size != (width, height):
        raise ValueError(f"image is {img.size}, expected {(width, height)}")
    out = Image.new("RGB", img.size)
    src, dst = img.load(), out.load()
    for y in range(height):
        for x in range(width):
            dst[x, y] = PALETTE[_nearest(src[x, y])]
    return out
