# ezsign-nfc — project notes for Claude Code

Pixel-exact writer and screen generators for Santek **EZ Sign** 4-colour NFC e-paper
panels (black / white / red / yellow), driven from macOS through an **ACS ACR1252U**
PC/SC reader. Built 23–24 Oct 2026 with Kevin Gomez; everything below was verified
on his hardware unless marked otherwise.

## Hardware on hand

| Panel | Resolution | Frame buffer | Chunks | Pixel layout (`--layout`) | Refresh |
|---|---|---|---|---|---|
| EZ Sign 4.2" | 400×300 | 30,000 B | 120 | `row-mirror` | ~24 s |
| EZ Sign 2.9" | 296×128 | 9,472 B | 37 + short 222 B | `col` | ~20 s |
| (2.13", not owned) | 250×128 | 8,000 B | 32 | `col-mirror` (from magic-epaper-app) | — |

Reader shows up as `ACS ACR1252 Dual Reader PICC` (use `--reader PICC`); the SAM slot is
irrelevant. Panel goes flat on the reader, centred, for the whole write.

## Protocol (ISO-DEP APDUs, `ezsign/protocol.py`)

SELECT AID `D2760000850101` → VERIFY key `20091210` → SELECT → INIT `00D1000000` →
DATA `F0 D2 <seq16> <Lc> <≤250 B>` → REFRESH `F0D4858000` → POLL `F0DE000001` until first
byte is `00`. All replies end `90 00`. INIT returns a TLV block: `A0` holds the panel
width as big-endian 16-bit (`01 90` = 400) — used for model auto-detection; `C0` = ASCII
serial; `C1` = UID. Credit: fossasia/magic-epaper-app PR #688 for the 2.13" driver.

Frame buffer is 2 bpp, MSB first, palette index `0=K 1=W 2=Y 3=R`. Pixel *order* differs
per panel (table above); `ezsign/encode.py` has all four orders, pinned by tests.

## Why this exists

The vendor app's "Pure Color" path resamples before quantizing, and its yellow is
`(255,192,0)` — nearest palette entry for mid-greys — so isolated black pixels come out
yellow ~70% of the time. This tool never resamples and refuses off-palette input by
default. Don't add dithering/anti-aliasing to text: the panel can't show grey, so edge
pixels become random black/white and strokes jitter.

## Workflow (on Kevin's Mac, `~/ezsign-nfc`, venv in `.venv`)

```
source .venv/bin/activate
python3 tools/fetch_weather.py weather.json      # Open-Meteo + Google Pollen (GOOGLE_POLLEN_KEY in ~/.zshrc)
python3 tools/gen_weather.py weather.json        # -> weather_live.png (git-ignored)
python3 ezsign_write.py weather_live.png --reader PICC
```

`gen_weather.py` with no args renders the built-in SAMPLE to `examples/weather_400x300.png`
(tracked). Never let a live render overwrite the tracked example — it blocks `git pull`.
Pollen.com's endpoint is blocked by bot protection from his network; Google Pollen is the
working source. Kevin's API key covers Pollen + Air Quality APIs.

## Design rules learned on the panel

- Panel red is a deep brick red, yellow a mustard; yellow-on-white has little contrast.
  Rain bars therefore carry a dotted black line at the fill level.
- Red is rationed: ≥60% rain, freezing lows, high pollen, the alert bar.
- Small text is X11 bitmap fonts at native size (`fonts/*.pil`: 4x6, 5x7, 6x10, 6x12,
  6x13B, 7x13, 7x13B). Bold faces get +1 px tracking; the 6x12 detail lines and 4x6 do not.
  Section labels are bold, centred in a 13-px black box (`label()`).
- Orange is a 2×2 ordered dither of red+yellow; reads as russet on the real panel.
- Leaf sprites (`assets/leaf_52.png`, `leaf_38.png`) are made by `tools/make_leaf_sprite.py`
  from a reference illustration (not in repo): warm-hue saturation mask, Floyd–Steinberg
  onto red/yellow, black only for darkest veins, no outline, stem kept via 8-connectivity.
  Knobs at the top of that file. Kevin reviews leaves closely; show a zoomed preview first.
- Kevin's preference: discuss/preview first, build when he says go; concise replies;
  surgical edits over rewrites.

## Commit conventions

Author `Kevin Gomez <nThanksForAllTheFish@users.noreply.github.com>` (email-privacy
protection rejects other addresses). Run `python3 -m pytest -q tests` before pushing.

## Open items / ideas

- launchd job for a scheduled morning refresh (panel left on the reader).
- Air Quality block (OWM or Google AQ) for months when pollen is "none in season".
- 2.9" weather layout (currently only a text test page for that panel).
- Photo mode: arbitrary image → four-ink dither for the 4.2".
