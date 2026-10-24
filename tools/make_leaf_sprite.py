#!/usr/bin/env python3
"""Turn a photo/illustration of a leaf into a four-ink sprite for the panel.

    python tools/make_leaf_sprite.py leaf.jpg assets/leaf_52.png 52
    python tools/make_leaf_sprite.py leaf.jpg assets/leaf_28.png 28 --flip

Isolates the leaf by colour saturation (background must be grey/white/blue),
scales it so its longer side is `size` px, and Floyd-Steinberg dithers the
shading onto red + yellow with black for the dark outline and veins. Output is
RGBA with only black/red/yellow pixels, transparent elsewhere.
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

K, R, Y = (0, 0, 0), (255, 0, 0), (255, 255, 0)
BLACK_PENALTY = 0.6     # error-diffusion bias against black inside the leaf
DARK_V = 45             # only source pixels darker than this (0-255 V) may become black
OUTLINE = True          # 1-px black ring around the silhouette


def main(src, out, size, flip=False):
    im = Image.open(src).convert("RGB")
    hsv = np.array(im.convert("HSV")).astype(int)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    warm = (hue < 50) | (hue > 235)                        # reds through yellows (PIL hue 0-255)
    coarse = warm & (sat > 90) & (val > 40)                # saturated leaf colours only
    ys, xs = np.nonzero(coarse)
    pad = 6
    box = (max(0, xs.min() - pad), max(0, ys.min() - pad), min(im.width, xs.max() + pad), min(im.height, ys.max() + pad))
    crop = im.crop(box)
    scale = size / max(crop.size)
    small = crop.resize((max(1, round(crop.width * scale)), max(1, round(crop.height * scale))), Image.LANCZOS)
    if flip:
        small = small.transpose(Image.FLIP_LEFT_RIGHT)
    h = np.array(small.convert("HSV")).astype(int); rgb = np.array(small).astype(float) / 255
    hh, s, v = h[..., 0], h[..., 1], h[..., 2]
    mask = (((hh < 50) | (hh > 235)) & (s > 70)) | (v < 70)   # warm leaf body or dark outline
    # keep only the component containing the centre; fill holes
    m = Image.fromarray((mask * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    mask = np.array(m) > 0
    from collections import deque
    Hh, Ww = mask.shape; seen = np.zeros_like(mask); q = deque()
    cy, cx = Hh // 2, Ww // 2
    if not mask[cy, cx]:
        yy, xx = np.nonzero(mask); i = np.argmin((yy - cy) ** 2 + (xx - cx) ** 2); cy, cx = yy[i], xx[i]
    seen[cy, cx] = True; q.append((cy, cx))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < Hh and 0 <= nx < Ww and mask[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True; q.append((ny, nx))
    # fill enclosed holes (white highlights inside the leaf): anything not reachable from the border
    outside = np.zeros_like(seen); q = deque()
    for y in range(Hh):
        for x in (0, Ww - 1):
            if not seen[y, x] and not outside[y, x]: outside[y, x] = True; q.append((y, x))
    for x in range(Ww):
        for y in (0, Hh - 1):
            if not seen[y, x] and not outside[y, x]: outside[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < Hh and 0 <= nx < Ww and not seen[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True; q.append((ny, nx))
    mask = seen | ~outside
    # pad 1 px so the outline ring has room
    mask = np.pad(mask, 1); rgb = np.pad(rgb, ((1, 1), (1, 1), (0, 0)), constant_values=1.0)
    v = np.pad(v, 1, constant_values=255); Hh, Ww = mask.shape
    # error diffusion onto {K, R, Y} inside the mask; "redness" from hue/value
    pal = np.array([K, R, Y], float) / 255
    buf = rgb.copy(); outp = np.zeros((Hh, Ww), int) - 1
    for y in range(Hh):
        rng = range(Ww) if y % 2 == 0 else range(Ww - 1, -1, -1); sd = 1 if y % 2 == 0 else -1
        for x in rng:
            if not mask[y, x]:
                continue
            p = np.clip(buf[y, x], -0.3, 1.3)
            # interior is red/yellow only; black is reserved for the darkest vein
            # pixels (and the outline ring added below), so the leaf reads warm
            d = ((pal - p) ** 2).sum(1)
            d[0] += BLACK_PENALTY
            if v[y, x] > DARK_V:
                d[0] = 9.0
            i = int(np.argmin(d)); outp[y, x] = i
            err = p - pal[i]
            for ddy, ddx, w in ((0, sd, 7 / 16), (1, -sd, 3 / 16), (1, 0, 5 / 16), (1, sd, 1 / 16)):
                yy, xx = y + ddy, x + ddx
                if 0 <= yy < Hh and 0 <= xx < Ww and mask[yy, xx]:
                    buf[yy, xx] += err * w
    spr = Image.new("RGBA", (Ww, Hh), (0, 0, 0, 0)); px = spr.load()
    for y in range(Hh):
        for x in range(Ww):
            if outp[y, x] >= 0:
                px[x, y] = (K, R, Y)[outp[y, x]] + (255,)
    if OUTLINE:
        m = Image.fromarray((mask * 255).astype(np.uint8))
        ring = np.array(m.filter(ImageFilter.MaxFilter(3))) > 0
        ring &= ~mask
        for y in range(Hh):
            for x in range(Ww):
                if ring[y, x]:
                    px[x, y] = K + (255,)
    spr.save(out); print("wrote", out, spr.size, "leaf px:", int(mask.sum()))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), "--flip" in sys.argv)
