#!/usr/bin/env python3
"""Write a 400x300 four-colour PNG to a Santek EZ Sign over a PC/SC NFC reader.

    pip install pyscard pillow
    python ezsign_write.py examples/ezsign_densetext_400x300.png

Lay the panel flat on the reader, centred on its antenna, and keep it there
until the script reports the refresh is complete (~25-30 s for 4-colour).
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from PIL import Image

from ezsign import LAYOUTS, MODELS, EZSign, EZSignError, decode, encode, identify, quantize

log = logging.getLogger("ezsign")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="PNG/BMP, exactly the panel resolution, four exact colours")
    ap.add_argument("--model", default="auto", choices=["auto", *sorted(MODELS)],
                    help="panel size; 'auto' (default) reads it from the display, "
                         "and is required for --dry-run only if the image size is ambiguous")
    ap.add_argument("--quantize", action="store_true",
                    help="nearest-colour map off-palette pixels instead of refusing them")
    ap.add_argument("--dry-run", metavar="OUT.bin",
                    help="encode only; write the frame buffer to OUT.bin and exit")
    ap.add_argument("--reader", help="substring of the PC/SC reader name to use")
    ap.add_argument("--wait", type=float, default=60, help="seconds to wait for the tag (default 60)")
    ap.add_argument("--layout", choices=LAYOUTS,
                    help="pixel order in the frame buffer (default: the model's)")
    ap.add_argument("--pad", action="store_true",
                    help="zero-pad the frame to a multiple of 250 bytes instead of sending a short last chunk (2.9\" only)")
    ap.add_argument("-v", "--verbose", action="store_true", help="log every APDU")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-5s %(message)s", datefmt="%H:%M:%S")

    img = Image.open(args.image)

    def build_frame(model: str) -> bytes:
        w, h, default_layout = MODELS[model]
        layout = args.layout or default_layout
        src = quantize(img, w, h) if args.quantize else img
        frame = encode(src, w, h, strict=not args.quantize, layout=layout)
        assert decode(frame, w, h, layout).tobytes() == src.convert("RGB").tobytes(), "encoder round-trip failed"
        log.info("encoded %s for %s\" -> %d bytes (%d chunks), layout=%s",
                 args.image, model, len(frame), -(-len(frame) // 250), layout)
        return frame

    def model_for_image_size() -> str | None:
        hits = [m for m, (w, h, _) in MODELS.items() if (w, h) == img.size]
        return hits[0] if len(hits) == 1 else None

    if args.dry_run:
        model = args.model if args.model != "auto" else model_for_image_size()
        if model is None:
            print(f"image is {img.size}; pass --model to say which panel it is for", file=sys.stderr)
            return 2
        frame = build_frame(model)
        with open(args.dry_run, "wb") as f:
            f.write(frame)
        log.info("wrote %s", args.dry_run)
        return 0

    try:
        from smartcard.System import readers
        from smartcard.Exceptions import CardConnectionException, NoCardException
    except ImportError:
        print("pyscard is not installed: pip install pyscard", file=sys.stderr)
        return 2

    rl = readers()
    if args.reader:
        rl = [r for r in rl if args.reader.lower() in str(r).lower()]
    if not rl:
        print("no PC/SC reader found" + (f" matching {args.reader!r}" if args.reader else ""), file=sys.stderr)
        return 2
    reader = rl[0]
    log.info("reader: %s", reader)

    conn = reader.createConnection()
    log.info("waiting for the display (place it on the reader) ...")
    t0 = time.monotonic()
    while True:
        try:
            conn.connect()
            break
        except (NoCardException, CardConnectionException):
            if time.monotonic() - t0 > args.wait:
                print("no tag detected", file=sys.stderr)
                return 3
            time.sleep(0.25)
    log.info("tag ATR: %s", bytes(conn.getATR()).hex(" ").upper())

    def transceive(apdu: bytes) -> bytes:
        data, sw1, sw2 = conn.transmit(list(apdu))
        return bytes(data) + bytes([sw1, sw2])

    def progress(i: int, n: int) -> None:
        if i % 10 == 0 or i == n:
            log.info("  sent %3d / %d chunks", i, n)

    try:
        dev = EZSign(transceive)
        info = dev.begin()
        detected = identify(info, MODELS)
        if args.model == "auto":
            model = detected
            if model is None:
                log.error("could not identify the panel from its INIT reply (A0 = %s); rerun with --model",
                          info.get(0xA0, b"").hex(" ").upper())
                return 1
            log.info("detected panel: %s\" (%dx%d)", model, *MODELS[model][:2])
        else:
            model = args.model
            if detected and detected != model:
                log.error("display identifies as %s\" but --model %s was given; refusing to write", detected, model)
                return 1
        w, h = MODELS[model][:2]
        if img.size != (w, h):
            log.error("image is %dx%d but the %s\" panel is %dx%d; refusing to write", *img.size, model, w, h)
            return 1
        frame = build_frame(model)
        dt = dev.send_frame(frame, progress=progress, pad=args.pad)
    except EZSignError as e:
        log.error("%s", e)
        return 1
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass
    log.info("done; panel refreshed in %.1f s", dt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
