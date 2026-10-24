#!/usr/bin/env python3
"""Weather screen for the 4.2" EZ Sign (400x300, black/white/red/yellow).

    python tools/gen_weather.py                 # renders the built-in sample
    python tools/gen_weather.py weather.json    # renders fetched data (see fetch_weather.py)

Output: examples/weather_400x300.png (pixel-exact, four colours).

Design rules for this panel: text in black on white; yellow for sun and
fill bars; red only for things that want attention (high rain chance, high
pollen, freeze). Small text is X11 bitmap fonts at native size so every
stroke is whole pixels; large numbers are DejaVu Bold rendered without
anti-aliasing.
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "examples", "weather_400x300.png")
W, H = 400, 300
K, Wt, Rd, Yl = (0, 0, 0), (255, 255, 255), (255, 0, 0), (255, 255, 0)
P = lambda n: ImageFont.load(os.path.join(HERE, "..", "fonts", f"{n}.pil"))
F4, F5, F6, F6B, F7B = P("4x6"), P("5x7"), P("6x10"), P("6x13B"), P("7x13B")
BIG = os.environ.get("EZSIGN_FONT_BOLD", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

SAMPLE = {
    "place": "EDEN PRAIRIE, MN", "date": "SAT OCT 24", "updated": "11:10",
    "today": {"temp": 47, "feels": 42, "hi": 52, "lo": 36, "cond": "Partly cloudy",
              "icon": "partly", "wind": "NW 12 mph", "hum": 58, "sunrise": "7:38", "sunset": "6:11",
              "rain": 20},
    "alert": "Frost advisory 2-8 AM",
    "tonight": "Clearing, low 36°",
    "rain_hours": [("12p", 10), ("3p", 20), ("6p", 35), ("9p", 45), ("12a", 30), ("3a", 10)],
    "pollen": {"index": 3.4, "level": "LOW-MED", "tree": 1, "grass": 0, "weed": 3, "mold": 4,
               "top": "Ragweed, Mold"},
    "week": [
        {"day": "SUN", "icon": "rain",   "cond": "Showers",  "hi": 49, "lo": 38, "rain": 70},
        {"day": "MON", "icon": "cloud",  "cond": "Cloudy",   "hi": 45, "lo": 33, "rain": 30},
        {"day": "TUE", "icon": "sun",    "cond": "Sunny",    "hi": 50, "lo": 31, "rain": 5},
        {"day": "WED", "icon": "partly", "cond": "Pt cloudy","hi": 54, "lo": 37, "rain": 10},
        {"day": "THU", "icon": "rain",   "cond": "Rain",     "hi": 48, "lo": 40, "rain": 60},
        {"day": "FRI", "icon": "snow",   "cond": "Snow shwr","hi": 37, "lo": 27, "rain": 55},
        {"day": "SAT", "icon": "sun",    "cond": "Clear",    "hi": 41, "lo": 26, "rain": 0},
    ],
}


def icon(d, x, y, kind, s=1):
    """Pixel weather icons in a 24x24 box (s=1) or 48x48 (s=2)."""
    def R(x0, y0, x1, y1, c, o=None): d.rectangle([x + x0 * s, y + y0 * s, x + (x1 + 1) * s - 1, y + (y1 + 1) * s - 1], fill=c, outline=o)
    def E(x0, y0, x1, y1, c, o=None): d.ellipse([x + x0 * s, y + y0 * s, x + (x1 + 1) * s - 1, y + (y1 + 1) * s - 1], fill=c, outline=o)
    def L(x0, y0, x1, y1, c): d.line([(x + x0 * s, y + y0 * s), (x + x1 * s, y + y1 * s)], fill=c, width=s)
    def sun(cx, cy, r):
        E(cx - r, cy - r, cx + r, cy + r, Yl, K)
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            L(cx + dx * (r + 2), cy + dy * (r + 2), cx + dx * (r + 4), cy + dy * (r + 4), K)
    def cloud(x0, y0, w, fill=Wt):
        shapes = [("e", x0, y0 + 3, x0 + 9, y0 + 11), ("e", x0 + 5, y0, x0 + 15, y0 + 10),
                  ("e", x0 + w - 10, y0 + 3, x0 + w - 1, y0 + 11), ("r", x0 + 4, y0 + 5, x0 + w - 5, y0 + 11)]
        for kind_, a, b, c, e in shapes:           # pass 1: outlined
            (E if kind_ == "e" else R)(a, b, c, e, fill, K)
        for kind_, a, b, c, e in shapes:           # pass 2: interiors, erases shared edges
            (E if kind_ == "e" else R)(a + 1, b + 1, c - 1, e - 1, fill)
    def drops(x0, y0, n, c=K):
        for i in range(n):
            L(x0 + i * 5, y0, x0 + i * 5 - 2, y0 + 4, c)
    def flakes(x0, y0, n):
        for i in range(n):
            cx, cy = x0 + i * 6, y0 + 2
            L(cx - 2, cy, cx + 2, cy, K); L(cx, cy - 2, cx, cy + 2, K)
    if kind == "sun":
        sun(12, 12, 6)
    elif kind == "partly":
        sun(8, 8, 5); cloud(5, 10, 18)
    elif kind == "cloud":
        cloud(2, 6, 20)
    elif kind == "rain":
        cloud(2, 3, 20); drops(6, 17, 3)
    elif kind == "storm":
        cloud(2, 2, 20); L(13, 14, 9, 20, Yl); L(9, 20, 13, 19, Yl); L(13, 19, 10, 24, Yl)
    elif kind == "snow":
        cloud(2, 3, 20); flakes(6, 17, 3)
    elif kind == "fog":
        for i in range(4): L(3, 7 + i * 4, 21, 7 + i * 4, K)


def T(d, x, y, s, f, c=K):
    d.text((x, y), s, font=f, fill=c); return d.textlength(s, font=f)


def TR(d, xr, y, s, f, c=K):
    w = d.textlength(s, font=f); d.text((xr - w, y), s, font=f, fill=c); return w


def bar(d, x, y, w, h, frac, col, warn=None):
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=K, fill=Wt)
    fw = int(round((w - 2) * max(0, min(1, frac))))
    if fw:
        d.rectangle([x + 1, y + 1, x + fw, y + h - 2], fill=(warn or col) if (warn and frac >= 0.6) else col)


def render(data):
    im = Image.new("RGB", (W, H), Wt); d = ImageDraw.Draw(im); d.fontmode = "1"
    t = data["today"]
    # ---- header
    d.rectangle([0, 0, W, 17], fill=K)
    T(d, 5, 2, data["place"], F7B, Wt)
    TR(d, W - 5, 2, data["date"], F7B, Yl)
    # ---- today (left column, x 0..175)
    big = ImageFont.truetype(BIG, 58)
    temp = f"{t['temp']}"
    d.text((6, 20), temp, font=big, fill=K)
    tw = d.textlength(temp, font=big)
    d.text((6 + tw + 1, 26), "°", font=ImageFont.truetype(BIG, 24), fill=K)
    icon(d, 112, 26, t["icon"], s=2)
    T(d, 6, 88, t["cond"], F6B)
    y = 102
    T(d, 6, y, f"Feels {t['feels']}°", F6); TR(d, 172, y, f"H {t['hi']}°  L {t['lo']}°", F6, Rd if t["lo"] <= 32 else K); y += 11
    T(d, 6, y, f"Wind {t['wind']}", F6); TR(d, 172, y, f"Hum {t['hum']}%", F6); y += 11
    T(d, 6, y, f"Sunrise {t['sunrise']}   Sunset {t['sunset']}", F5); y += 11
    alert = data.get("alert")
    if alert:
        d.rectangle([6, y, 172, y + 10], fill=Rd); T(d, 9, y + 2, alert[:32].upper(), F5, Wt); y += 12
    tonight = data.get("tonight")
    if tonight:
        T(d, 6, y, "Tonight", F6B); T(d, 6 + d.textlength("Tonight ", font=F6B), y + 2, tonight[:30], F5); y += 12
    # ---- right column: rain (x 186..394)
    X0 = 186; d.line([(180, 20), (180, 158)], fill=K)
    d.rectangle([X0, 20, X0 + 5 * 14 + 4, 29], fill=K); T(d, X0 + 2, 21, "RAIN CHANCE", F5, Wt)
    rc = t["rain"]
    TR(d, W - 6, 19, f"{rc}%", F7B, Rd if rc >= 60 else K)
    T(d, W - 6 - d.textlength(f"{rc}%", font=F7B) - 4 - d.textlength("today", font=F4), 25, "today", F4)
    # hourly bars
    hx, hy, bw, bh = X0, 36, 30, 28
    for i, (lab, p) in enumerate(data["rain_hours"][:6]):
        x = hx + i * 35
        fh = int(round(bh * p / 100))
        d.rectangle([x, hy, x + bw - 1, hy + bh - 1], outline=K)
        if fh:
            d.rectangle([x + 1, hy + bh - 1 - fh, x + bw - 2, hy + bh - 2], fill=Rd if p >= 60 else Yl)
        T(d, x + (bw - d.textlength(f"{p}", font=F4)) // 2, hy + 2 if fh > 10 else hy + bh - 8, f"{p}", F4)
        T(d, x + (bw - d.textlength(lab, font=F4)) // 2, hy + bh + 2, lab, F4)
    # ---- pollen
    py = 78
    d.rectangle([X0, py, X0 + 5 * 7 + 4, py + 9], fill=K); T(d, X0 + 2, py + 1, "POLLEN", F5, Wt)
    pol = data["pollen"]
    lvl = pol["level"]; TR(d, W - 6, py - 2, f"{pol['index']:.1f}  {lvl}", F6B, Rd if pol["index"] >= 7.3 else K)
    rows = [("Tree", pol["tree"]), ("Grass", pol["grass"]), ("Weed", pol["weed"]), ("Mold", pol["mold"])]
    ry = py + 13
    for name, v in rows:
        T(d, X0, ry, name, F5)
        if v is None:
            T(d, X0 + 36, ry, "no data", F4); ry += 10; continue
        for seg in range(5):
            x = X0 + 36 + seg * 13
            on = seg < v
            d.rectangle([x, ry, x + 10, ry + 6], fill=(Rd if v >= 4 else Yl) if on else Wt, outline=K)
        TR(d, W - 6, ry, ["None", "Low", "Low", "Med", "High", "V.High"][min(v, 5)], F5, Rd if v >= 4 else K)
        ry += 10
    T(d, X0, ry + 1, "Top: " + pol["top"], F4)
    # ---- 7-day strip
    sy = 166
    d.line([(0, sy - 2), (W, sy - 2)], fill=K)
    cw = W // 7
    for i, day in enumerate(data["week"][:7]):
        x = i * cw
        if i:
            d.line([(x, sy), (x, H - 11)], fill=K)
        cx = x + cw // 2
        d.rectangle([x + 1, sy, x + cw - 1, sy + 11], fill=K if i else Rd)
        T(d, cx - d.textlength(day["day"], font=F6B) // 2, sy, day["day"], F6B, Wt)
        icon(d, cx - 12, sy + 17, day["icon"])
        T(d, cx - d.textlength(day.get("cond", ""), font=F4) // 2, sy + 44, day.get("cond", ""), F4)
        T(d, cx - d.textlength(f"{day['hi']}°", font=F7B) // 2, sy + 54, f"{day['hi']}°", F7B)
        T(d, cx - d.textlength(f"{day['lo']}°", font=F6) // 2, sy + 69, f"{day['lo']}°", F6, Rd if day["lo"] <= 32 else K)
        p = day["rain"]
        bar(d, x + 5, sy + 84, cw - 10, 8, p / 100, Yl, warn=Rd)
        T(d, cx - d.textlength(f"{p}%", font=F5) // 2, sy + 95, f"{p}%", F5, Rd if p >= 60 else K)
        T(d, cx - d.textlength("rain", font=F4) // 2, sy + 104, "rain" if day["icon"] != "snow" else "snow", F4)
    # footer
    d.rectangle([0, H - 10, W, H], fill=K)
    T(d, 3, H - 8, f"Updated {data['updated']}  ·  Open-Meteo / Pollen.com", F4, Wt)
    TR(d, W - 3, H - 8, "EZ Sign 4.2\" · 400x300 · 4-color", F4, Wt)
    assert set(c for _, c in im.getcolors()) <= {K, Wt, Rd, Yl}, "off-palette pixel"
    return im


if __name__ == "__main__":
    data = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else SAMPLE
    im = render(data)
    pal = Image.new("P", (1, 1)); pal.putpalette([0, 0, 0, 255, 255, 255, 255, 0, 0, 255, 255, 0] + [0] * (252 * 3))
    out = OUT if len(sys.argv) < 3 else sys.argv[2]
    im.quantize(palette=pal, dither=Image.Dither.NONE).save(out, optimize=True)
    print("wrote", out)
