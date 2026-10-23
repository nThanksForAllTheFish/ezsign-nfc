"""296x128 pixel-font test page for the EZ Sign 2.9" four-colour panel."""
import os, textwrap
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "examples")
W, H = 296, 128
K, Wt, Rd, Yl = (0, 0, 0), (255, 255, 255), (255, 0, 0), (255, 255, 0)
P = lambda n: ImageFont.load(os.path.join(HERE, "..", "fonts", f"{n}.pil"))
f4, f5, f6b, f7b = P("4x6"), P("5x7"), P("6x13B"), P("7x13B")
im = Image.new("RGB", (W, H), Wt); d = ImageDraw.Draw(im); d.fontmode = "1"
d.rectangle([0, 0, W, 15], fill=K); d.text((3, 1), "EZ SIGN 2.9\" 296x128 4-COLOR", font=f7b, fill=Wt)
d.text((3, 18), "FONT LADDER  1 glyph px = 1 panel px", font=f4, fill=K)
y = 26
for name, f, h, s in [("4x6", f4, 6, "The quick brown fox jumps over the lazy dog 0123456789"),
                      ("5x7", f5, 7, "The quick brown fox jumps over the lazy 012345"),
                      ("6x13B", f6b, 13, "The quick brown fox jumps 01234")]:
    d.rectangle([3, y, 30, y + h - 1], fill=Rd); d.text((4, y + (h - 6) // 2), name, font=f4, fill=Wt)
    d.text((34, y), s, font=f, fill=K); y += h + 1
d.line([(0, y + 1), (W, y + 1)], fill=K); y += 4
body = ("Frame buffer 296x128x2 bits = 9472 bytes = 37 full chunks of 250 plus a 222-byte tail. "
        "If this page arrives intact the short final DATA APDU is accepted; if the bottom rows "
        "are missing or wrong, retry with --pad.")
for ln in textwrap.wrap(body, 72)[:6]:
    d.text((3, y), ln, font=f4, fill=K); y += 6
d.rectangle([3, y + 2, 3 + 5 * 12, y + 10], fill=Yl); d.text((4, y + 3), "COLOR CHECK", font=f5, fill=K)
for i, c in enumerate([K, Rd, Yl, Wt]):
    d.rectangle([70 + i * 12, y + 2, 70 + i * 12 + 9, y + 10], fill=c, outline=K)
ry = H - 13; d.rectangle([0, ry, W, H], fill=K)
d.text((0, ry + 1), "".join(str(i % 10) for i in range(74)), font=f4, fill=Yl)
d.text((0, ry + 7), "".join(f"{i*10:<10d}" for i in range(8))[:74], font=f4, fill=Wt)
assert set(c for _, c in im.getcolors()) <= {K, Wt, Rd, Yl}
pal = Image.new("P", (1, 1)); pal.putpalette([0, 0, 0, 255, 255, 255, 255, 0, 0, 255, 255, 0] + [0] * (252 * 3))
im.quantize(palette=pal, dither=Image.Dither.NONE).save(os.path.join(OUT, "ezsign29_densetext_296x128.png"), optimize=True)
