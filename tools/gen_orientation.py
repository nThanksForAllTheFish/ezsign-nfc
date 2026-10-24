"""Orientation test pattern: a big asymmetric 'F', labelled corners, and a
colour strip, so one photo tells you the buffer layout (row/column, mirror,
flip) and the palette-index mapping."""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "examples")
K, Wt, Rd, Yl = (0, 0, 0), (255, 255, 255), (255, 0, 0), (255, 255, 0)
P = lambda n: ImageFont.load(os.path.join(HERE, "..", "fonts", f"{n}.pil"))

def make(W, H, name):
    im = Image.new("RGB", (W, H), Wt); d = ImageDraw.Draw(im); d.fontmode = "1"
    f = P("7x13B") if H >= 200 else P("6x13B")
    s = H // 300 if H >= 300 else 1
    # big F, top-left heavy
    fx, fy, fh = int(W * 0.08), int(H * 0.15), int(H * 0.6)
    t = max(6, fh // 7)
    d.rectangle([fx, fy, fx + t, fy + fh], fill=K)
    d.rectangle([fx, fy, fx + int(fh * 0.7), fy + t], fill=K)
    d.rectangle([fx, fy + fh // 2 - t // 2, fx + int(fh * 0.5), fy + fh // 2 + t // 2], fill=K)
    # corner labels
    d.text((3, 2), "TL", font=f, fill=K)
    tw = d.textlength("TR", font=f); d.text((W - 3 - tw, 2), "TR", font=f, fill=Rd)
    d.text((3, H - 15), "BL", font=f, fill=K)
    tw = d.textlength("BR", font=f); d.text((W - 3 - tw, H - 15), "BR", font=f, fill=Rd)
    # colour strip with index labels, right side
    cx = int(W * 0.55); cw = (W - cx - 6) // 4
    for i, (c, lab) in enumerate([(K, "0 K"), (Wt, "1 W"), (Yl, "2 Y"), (Rd, "3 R")]):
        x0 = cx + i * cw
        d.rectangle([x0, int(H * 0.25), x0 + cw - 3, int(H * 0.55)], fill=c, outline=K)
        d.text((x0 + 2, int(H * 0.57)), lab, font=f, fill=K)
    # 1-px checker and single-pixel lines to show bit order / stride
    for x in range(cx, W - 6, 2):
        d.point((x, int(H * 0.7)), fill=K)
    d.line([(cx, int(H * 0.72)), (W - 6, int(H * 0.72))], fill=K)
    d.line([(cx, int(H * 0.74)), (W - 6, int(H * 0.74))], fill=Rd)
    d.line([(cx, int(H * 0.76)), (W - 6, int(H * 0.76))], fill=Yl)
    d.text((cx, int(H * 0.79)), f"{W}x{H}  TOP LEFT IS 'TL'", font=P("5x7"), fill=K)
    assert set(c for _, c in im.getcolors()) <= {K, Wt, Rd, Yl}
    pal = Image.new("P", (1, 1)); pal.putpalette([0, 0, 0, 255, 255, 255, 255, 0, 0, 255, 255, 0] + [0] * (252 * 3))
    im.quantize(palette=pal, dither=Image.Dither.NONE).save(os.path.join(OUT, name), optimize=True)

make(400, 300, "orientation_400x300.png")
make(296, 128, "orientation_296x128.png")
