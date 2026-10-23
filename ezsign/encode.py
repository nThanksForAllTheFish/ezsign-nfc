"""Image <-> EZ Sign 2-bit frame buffer.

Pixel format (as implemented for the 2.13" BWRY model in
fossasia/magic-epaper-app, lib/santek/services/santek_image_codec.dart):

  * 2 bits per pixel, palette index 0=black 1=white 2=yellow 3=red
  * column-major, x mirrored:  bit_pos = (x * HEIGHT + y) * 2,
    where the pixel sampled is image[(WIDTH-1-x), y]
  * MSB first within each byte

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
    # name: (width, height)
    "4.2": (400, 300),
    "2.13": (250, 128),
    "2.9": (296, 128),
}


def _nearest(rgb):
    r, g, b = rgb
    best, best_d = WHITE, 1 << 30
    for i, (pr, pg, pb) in enumerate(PALETTE):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best_d:
            best, best_d = i, d
    return best


def encode(img: Image.Image, width: int = 400, height: int = 300,
           strict: bool = True) -> bytes:
    """Return the frame buffer for *img*, which must already be width x height."""
    img = img.convert("RGB")
    if img.size != (width, height):
        raise ValueError(f"image is {img.size}, expected {(width, height)}; "
                         "resize deliberately before encoding")
    px = img.load()
    lut = {c: i for i, c in enumerate(PALETTE)}
    buf = bytearray(width * height * 2 // 8)
    bad = 0
    for x in range(width):
        col = width - 1 - x
        for y in range(height):
            rgb = px[col, y]
            idx = lut.get(rgb)
            if idx is None:
                bad += 1
                if strict:
                    raise ValueError(
                        f"pixel ({col},{y}) = {rgb} is not one of the four panel "
                        "colours; quantize first or pass strict=False")
                idx = _nearest(rgb)
            bit = (x * height + y) * 2
            buf[bit >> 3] |= idx << (6 - (bit & 7))
    return bytes(buf)


def decode(buf: bytes, width: int = 400, height: int = 300) -> Image.Image:
    """Inverse of encode(); useful for round-trip tests and for inspecting dumps."""
    if len(buf) != width * height * 2 // 8:
        raise ValueError(f"buffer is {len(buf)} bytes, expected {width*height*2//8}")
    img = Image.new("RGB", (width, height))
    px = img.load()
    for x in range(width):
        col = width - 1 - x
        for y in range(height):
            bit = (x * height + y) * 2
            idx = (buf[bit >> 3] >> (6 - (bit & 7))) & 3
            px[col, y] = PALETTE[idx]
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
