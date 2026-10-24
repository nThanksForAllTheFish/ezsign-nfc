import os
import random

from PIL import Image

from ezsign import LAYOUTS, PALETTE, decode, encode

HERE = os.path.dirname(__file__)
EXAMPLES = os.path.join(HERE, "..", "examples")


def test_frame_size():
    img = Image.new("RGB", (400, 300), PALETTE[1])
    assert len(encode(img)) == 30000


def test_col_mirror_matches_magic_epaper_reference():
    # Reference formula from magic-epaper-app's SantekImageCodec (2.13"): the
    # pixel at image x = W-1-x, y lands at bit (x*H + y)*2, MSB first.
    W, H = 8, 4
    img = Image.new("RGB", (W, H), PALETTE[1])
    img.putpixel((W - 1, 0), PALETTE[3])  # -> first two bits = 3 (red)
    img.putpixel((W - 1, 1), PALETTE[0])  # -> next two bits = 0 (black)
    buf = encode(img, W, H, layout="col-mirror")
    assert buf[0] >> 6 == 3
    assert (buf[0] >> 4) & 3 == 0
    assert (buf[0] >> 2) & 3 == 1


def test_row_layout():
    W, H = 8, 4
    img = Image.new("RGB", (W, H), PALETTE[1])
    img.putpixel((0, 0), PALETTE[3]); img.putpixel((1, 0), PALETTE[0]); img.putpixel((0, 1), PALETTE[2])
    buf = encode(img, W, H, layout="row")
    assert buf[0] == 0b11_00_01_01          # x=0..3 of row 0
    assert buf[2] == 0b10_01_01_01          # x=0..3 of row 1


def test_all_layouts_roundtrip():
    rnd = random.Random(2)
    img = Image.new("RGB", (40, 30))
    img.putdata([PALETTE[rnd.randrange(4)] for _ in range(40 * 30)])
    for lay in LAYOUTS:
        assert decode(encode(img, 40, 30, layout=lay), 40, 30, lay).tobytes() == img.tobytes(), lay


def test_roundtrip_random():
    rnd = random.Random(1)
    img = Image.new("RGB", (400, 300))
    img.putdata([PALETTE[rnd.randrange(4)] for _ in range(400 * 300)])
    assert decode(encode(img)).tobytes() == img.tobytes()


def test_examples_are_pure_palette_and_roundtrip():
    for name in os.listdir(EXAMPLES):
        if not name.endswith(".png"):
            continue
        img = Image.open(os.path.join(EXAMPLES, name)).convert("RGB")
        w, h = img.size
        assert (w, h) in ((400, 300), (296, 128), (250, 128)), name
        assert set(c for _, c in img.getcolors()) <= set(PALETTE), name
        assert decode(encode(img, w, h), w, h).tobytes() == img.tobytes(), name


def test_strict_rejects_offpalette():
    img = Image.new("RGB", (400, 300), (255, 192, 0))
    try:
        encode(img)
    except ValueError:
        return
    raise AssertionError("off-palette pixel accepted in strict mode")
