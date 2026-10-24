# ezsign-nfc

Pixel-exact writer for the **Santek EZ Sign 4.2" four-colour (black/white/red/yellow) NFC e-paper display**, using a PC/SC reader (ACR1252U or similar) instead of the vendor phone app — plus a set of 400×300 example images built for the panel's four inks.

Also drives the 2.9" (296×128) and 2.13" (250×128) four-colour models via `--model`.

**Status (2026-10-24): working on the 4.2" and 2.9" via ACR1252U on macOS.** Same command set on both; 4.2" = 120 chunks, layout `row-mirror`, refresh ~24 s; 2.9" = 37 chunks + a short 222-byte chunk (accepted as-is), layout `col`. Text pages come through pixel-exact with no stray colour. The 2.13" entry is from magic-epaper-app and untested here.

 The protocol below is taken from the working 2.13" BWRY driver in [fossasia/magic-epaper-app](https://github.com/fossasia/magic-epaper-app) (PR [#688](https://github.com/fossasia/magic-epaper-app/pull/688)). The only change assumed for the other sizes is the frame-buffer length: 4.2" = 30,000 bytes = 120 chunks; 2.9" = 9,472 bytes = 37 chunks + a 222-byte tail, sent short (confirmed working; `--pad` zero-fills instead if ever needed).

## Why

The official EZ Sign app's "Pure Color" conversion resamples the image before quantizing, and its yellow is `(255,192,0)`, which in RGB distance is the nearest palette entry for mid-grays. The result: isolated black pixels (i-dots, periods, serifs) come out **yellow** about 70% of the time, 2-px stroke ends 8%, thicker strokes never. Measured by diffing the app's saved output against the source: 2,771 stray yellow pixels on a text page.

This tool does nearest-colour against the true palette with **no resampling**, and by default refuses any input pixel that isn't already one of the four colours — so what you draw is what the panel gets.

## Install

```
pip install pyscard pillow
```

macOS has a built-in CCID driver; the ACR1252U is recognised without extra software. On Linux install `pcscd` and `libacsccid1`.

## Use

```
python ezsign_write.py examples/ezsign_densetext_400x300.png -v
```

Lay the panel flat on the reader, centred on its antenna, and keep it there until the script reports the refresh is done (~25–30 s). `-v` logs every APDU and status word.

The panel model is read from the display's INIT reply, and the image must match its resolution or the write is refused. Options: `--model 2.13|2.9|4.2` (override or for `--dry-run`), `--dry-run out.bin` (encode only), `--quantize` (allow off-palette pixels, nearest-colour mapped — no dithering), `--reader PICC` (pick a reader by name substring), `--layout` (override the model's pixel order).

## Protocol

ISO 14443-4 (ISO-DEP) APDUs. Any reader or phone that does ISO7816 transceive can drive it.

| Step | APDU | Notes |
|---|---|---|
| SELECT | `00 A4 04 00 07 D2 76 00 00 85 01 01` | NFC Forum Type-4 NDEF application AID |
| VERIFY | `00 20 00 01 04 20 09 12 10` | fixed 4-byte key; retried once after 300 ms |
| SELECT | (again) | |
| INIT | `00 D1 00 00 00` | start image write |
| DATA ×N | `F0 D2 <seq16> <Lc> <≤250 bytes>` | seq = 0…N−1; N = 120 for 400×300, 38 for 296×128 (last chunk 222 B, or `--pad`) |
| REFRESH | `F0 D4 85 80 00` | panel starts its waveform |
| POLL | `F0 DE 00 00 01` | repeat ~5 Hz; first data byte `00` = done |

All replies end `90 00` on success.

**Frame buffer**: 2 bits/pixel, palette index `0=black 1=white 2=yellow 3=red`, MSB first. Pixel *order* is per model (`--layout`): the 2.13" uses `col-mirror` (pixel `(W−1−x, y)` at bit `(x·H + y)·2`, per magic-epaper-app); the 4.2" uses `row-mirror` (pixel `(W−1−x, y)` at bit `(y·W + x)·2`) and the 2.9" uses `col` (pixel `(x, y)` at bit `(x·H + y)·2`), both verified with the orientation patterns; the wrong mirror gives a mirror image, the wrong major order scrambles. `ezsign/encode.py` has `encode()`/`decode()` for all four layouts, pinned by `tests/test_encode.py`.

**INIT reply** is a TLV block with device info; `-v` prints it. On a 4.2": `A0 = F0 07 20 02 58 01 90` (0x0190 = 400 = panel width), `C0` = ASCII serial, `C1` = 4-byte UID matching the ATR. Model detection looks for a known panel width (then height) as a big-endian 16-bit value inside `A0`.

## Verifying

Send `examples/orientation_400x300.png` first: a big "F", corner labels and a 0/1/2/3 colour strip, so one photo tells you whether the layout, mirror and palette indices are right. Then `examples/ezsign_densetext_400x300.png`. It's a pixel-font test page: the 100-column ruler along the bottom edge and the 4x6 text block tell you immediately whether the write was 1:1 (a stray-pixel count of zero under a loupe is the goal). If the REFRESH is rejected or the panel stays blank, the 4.2" differs from the 2.13" by more than chunk count — the APK is the next place to look (`jadx`, grep for `F0D2`, `D27600008501`, `20091210`).

## Weather screen

```
python tools/fetch_weather.py weather.json --lat 44.85 --lon -93.47 --zip 55344 --place "EDEN PRAIRIE, MN"
python tools/gen_weather.py weather.json
python ezsign_write.py examples/weather_400x300.png --reader PICC
```

The two fall leaves are four-ink sprites in `assets/`, made from a reference illustration with `tools/make_leaf_sprite.py` (isolates a leaf by warm-hue saturation, scales it, Floyd–Steinberg dithers the shading onto red + yellow with black outline/veins); point it at any leaf picture on a plain background to make your own. Set `"leaves": false` in the JSON to drop them.

Open-Meteo needs no key. Pollen comes from the **Google Pollen API** (`--google-key KEY` or `GOOGLE_POLLEN_KEY`): tree, grass and weed on the 0–5 Universal Pollen Index, which maps straight onto the five-segment bars, plus the top plants in season. To get a key: Google Cloud console → APIs & Services → enable "Pollen API" → Credentials → create an API key (restrict it to the Pollen API). Free tier is thousands of lookups a month; this screen uses one per refresh. Without a key the script falls back to Pollen.com's unofficial endpoint, which is frequently blocked, or `--pollen none`. Mold isn't reported by either and shows "no data". Red is reserved for rain chance ≥60%, freezing lows, high pollen and the alert bar (`--alert "text"` or automatic when tonight's low is ≤32 °F).

## Examples and generators

| Image | What it exercises |
|---|---|
| `ezsign_demo_400x300.png` | ordered-dither gradients (8×8 Bayer), coarse |
| `ezsign_fine_400x300.png` | Floyd–Steinberg per-pixel shading, 1-px detail |
| `ezsign_namecard_400x300.png` | vCard QR (3-px modules, verified decodable), 8–10 px text |
| `ezsign_densetext_400x300.png` | native bitmap fonts 4x6…7x13B, 1 glyph px = 1 panel px, ~1,900 chars |
| `weather_400x300.png` | weather dashboard: today, 6 hourly rain-chance bars, pollen, 7-day strip. `tools/fetch_weather.py` fills it with live Open-Meteo + Pollen.com data, `tools/gen_weather.py` renders it |
| `ezsign29_densetext_296x128.png` | the same idea for the 2.9" panel (`--model 2.9`); tests the short last chunk |

`tools/gen_*.py` regenerate them into `examples/` (needs Pillow, numpy; the name card also needs `qrcode` and `opencv-python-headless` for its self-check). `fonts/` holds the X11 misc bitmap fonts converted to PIL format by `tools/convert_x11_fonts.py`, plus DejaVu Sans / Sans Bold (Bitstream Vera licence) for the large type, so the generators run on macOS without system fonts. Edit `gen_namecard.py` to put your own name and vCard on the card.

**Design rule learned the hard way:** if you must go through the vendor app, give every black pixel at least two black 4-neighbours, or it may come back yellow.

## Credits

Protocol: the Santek driver in [fossasia/magic-epaper-app](https://github.com/fossasia/magic-epaper-app). Related: [kenichi884/ezsign.py](https://github.com/kenichi884/ezsign.py) (USB-serial, older wired model), and [this write-up](https://lilting.ch/en/articles/acr1251u-ntag-ez-sign-windows) on driving an EZ Sign from an ACR1251U with the vendor's Windows software.

## Licence

MIT. The X11 bitmap fonts in `fonts/` are public domain; DejaVu Sans is under the Bitstream Vera licence (free to redistribute).
