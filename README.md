# ezsign-nfc

Pixel-exact writer for the **Santek EZ Sign 4.2" four-colour (black/white/red/yellow) NFC e-paper display**, using a PC/SC reader (ACR1252U or similar) instead of the vendor phone app — plus a set of 400×300 example images built for the panel's four inks.

**Status: untested against real hardware.** The protocol below is taken from the working 2.13" BWRY driver in [fossasia/magic-epaper-app](https://github.com/fossasia/magic-epaper-app) (PR [#688](https://github.com/fossasia/magic-epaper-app/pull/688)). The only change assumed for the 4.2" is the frame-buffer size (30,000 bytes = 120 chunks instead of 8,000 = 32). First run will confirm or correct that; see *Verifying*.

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

Options: `--dry-run out.bin` (encode only), `--quantize` (allow off-palette pixels, nearest-colour mapped — no dithering), `--reader ACR1252` (pick a reader by name substring), `--model 2.13|2.9|4.2`.

## Protocol

ISO 14443-4 (ISO-DEP) APDUs. Any reader or phone that does ISO7816 transceive can drive it.

| Step | APDU | Notes |
|---|---|---|
| SELECT | `00 A4 04 00 07 D2 76 00 00 85 01 01` | NFC Forum Type-4 NDEF application AID |
| VERIFY | `00 20 00 01 04 20 09 12 10` | fixed 4-byte key; retried once after 300 ms |
| SELECT | (again) | |
| INIT | `00 D1 00 00 00` | start image write |
| DATA ×N | `F0 D2 <seq16> FA <250 bytes>` | seq = 0…N−1; N = 120 for 400×300 |
| REFRESH | `F0 D4 85 80 00` | panel starts its waveform |
| POLL | `F0 DE 00 00 01` | repeat ~5 Hz; first data byte `00` = done |

All replies end `90 00` on success.

**Frame buffer**: 2 bits/pixel, palette index `0=black 1=white 2=yellow 3=red`, **column-major with x mirrored**: the pixel at image `(W−1−x, y)` lands at bit position `(x·H + y)·2`, MSB first. `ezsign/encode.py` has `encode()`/`decode()` and the layout is pinned by `tests/test_encode.py`.

## Verifying

Send `examples/ezsign_densetext_400x300.png` first. It's a pixel-font test page: the 100-column ruler along the bottom edge and the 4x6 text block tell you immediately whether the write was 1:1 (a stray-pixel count of zero under a loupe is the goal). If the REFRESH is rejected or the panel stays blank, the 4.2" differs from the 2.13" by more than chunk count — the APK is the next place to look (`jadx`, grep for `F0D2`, `D27600008501`, `20091210`).

## Examples and generators

| Image | What it exercises |
|---|---|
| `ezsign_demo_400x300.png` | ordered-dither gradients (8×8 Bayer), coarse |
| `ezsign_fine_400x300.png` | Floyd–Steinberg per-pixel shading, 1-px detail |
| `ezsign_namecard_400x300.png` | vCard QR (3-px modules, verified decodable), 8–10 px text |
| `ezsign_densetext_400x300.png` | native bitmap fonts 4x6…7x13B, 1 glyph px = 1 panel px, ~1,900 chars |

`tools/gen_*.py` regenerate them into `examples/` (needs Pillow, numpy; the name card also needs `qrcode` and `opencv-python-headless` for its self-check). `fonts/` holds the X11 misc bitmap fonts converted to PIL format by `tools/convert_x11_fonts.py`. Edit `gen_namecard.py` to put your own name and vCard on the card.

**Design rule learned the hard way:** if you must go through the vendor app, give every black pixel at least two black 4-neighbours, or it may come back yellow.

## Credits

Protocol: the Santek driver in [fossasia/magic-epaper-app](https://github.com/fossasia/magic-epaper-app). Related: [kenichi884/ezsign.py](https://github.com/kenichi884/ezsign.py) (USB-serial, older wired model), and [this write-up](https://lilting.ch/en/articles/acr1251u-ntag-ez-sign-windows) on driving an EZ Sign from an ACR1251U with the vendor's Windows software.

## Licence

MIT. The X11 bitmap fonts in `fonts/` are public domain.
