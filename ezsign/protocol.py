"""Santek EZ Sign NFC write protocol, transport-agnostic.

The display is an ISO 14443-4 (ISO-DEP) tag. Everything below is plain
APDUs, so it can run over any PC/SC reader (pyscard) or a phone's IsoDep /
Core NFC ISO7816 session.

Sequence, as reverse-engineered for the 2.13" BWRY model in
fossasia/magic-epaper-app (lib/santek/services/santek_nfc_protocol.dart):

    00 A4 04 00 07 D2 76 00 00 85 01 01      SELECT  (NFC Forum T4T NDEF AID)
    00 20 00 01 04 20 09 12 10               VERIFY  (fixed 4-byte key)
    00 A4 04 00 07 D2 76 00 00 85 01 01      SELECT again
    00 D1 00 00 00                           INIT write
    F0 D2 <seq hi> <seq lo> FA <250 bytes>   DATA chunk, seq = 0..N-1
    F0 D4 85 80 00                           REFRESH (panel starts its waveform)
    F0 DE 00 00 01                           POLL; first data byte 0x00 = done

Frame sizes: 2.13" 250x128 = 8,000 B = 32 chunks; 4.2" 400x300 = 30,000 B =
120 chunks; 2.9" 296x128 = 9,472 B = 37 chunks + a short 222-byte chunk.
Verified on hardware 2026-10-24 for the 4.2" and 2.9" (ACR1252U, macOS):
same command set for both, the 2.9" accepts the short final chunk as-is.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

log = logging.getLogger("ezsign")

Transceive = Callable[[bytes], bytes]   # send APDU, return response incl. SW1 SW2

CHUNK = 250

APDU_SELECT = bytes.fromhex("00A4040007D2760000850101")
APDU_VERIFY = bytes.fromhex("002000010420091210")
APDU_INIT = bytes.fromhex("00D1000000")
APDU_REFRESH = bytes.fromhex("F0D4858000")
APDU_POLL = bytes.fromhex("F0DE000001")


class EZSignError(RuntimeError):
    pass


def parse_tlv(data: bytes) -> dict:
    """INIT replies with simple tag/len/value records. Observed on a 4.2":
    A0: F0 07 20 02 58 01 90   (01 90 = 400; geometry/model block?)
    A1: 01 12 00 30 FF FF FF   (firmware?)   B1: 08   B2: 14   B3: 00
    C0: ASCII serial number    C1: 4-byte UID (matches the ATR)   D1: 01 20 00 ..
    """
    out, i = {}, 0
    while i + 2 <= len(data):
        tag, ln = data[i], data[i + 1]
        out[tag] = data[i + 2:i + 2 + ln]
        i += 2 + ln
    return out


def identify(info: dict, models: dict) -> Optional[str]:
    """Guess the panel model from the INIT reply.

    Tag A0 holds the geometry: on a 4.2" it is F0 07 20 02 58 01 90, where
    01 90 = 400 is the panel width. We look for any model's width (or height)
    as a big-endian 16-bit value inside A0 and return the model if exactly one
    matches. *models* is {name: (width, height, layout)}.
    """
    a0 = info.get(0xA0, b"")
    words = {(a0[i] << 8) | a0[i + 1] for i in range(len(a0) - 1)}
    for pick in (lambda w, h: w, lambda w, h: h):     # width first: 2.9" and 2.13" share h=128
        hits = [m for m, (w, h, _) in models.items() if pick(w, h) in words]
        if len(hits) == 1:
            return hits[0]
    return None


def _hex(b: bytes) -> str:
    return b.hex(" ").upper()


def sw_ok(resp: bytes) -> bool:
    return len(resp) >= 2 and resp[-2:] == b"\x90\x00"


class EZSign:
    def __init__(self, transceive: Transceive, *, chunk: int = CHUNK):
        self._tx = transceive
        self.chunk = chunk

    def _send(self, apdu: bytes, what: str, expect_ok: bool = True) -> bytes:
        t0 = time.monotonic()
        resp = self._tx(apdu)
        dt = (time.monotonic() - t0) * 1000
        shown = _hex(apdu) if len(apdu) <= 16 else _hex(apdu[:8]) + f" .. ({len(apdu)} B)"
        log.debug("%-8s > %s", what, shown)
        log.debug("%-8s < %s  (%.0f ms)", what, _hex(resp), dt)
        if expect_ok and not sw_ok(resp):
            raise EZSignError(f"{what}: unexpected response {_hex(resp)}")
        return resp

    def begin(self) -> dict:
        """SELECT / VERIFY / INIT. Returns the parsed INIT device-info TLVs."""
        self._send(APDU_SELECT, "SELECT")
        resp = self._send(APDU_VERIFY, "VERIFY", expect_ok=False)
        if not sw_ok(resp):
            time.sleep(0.3)
            self._send(APDU_VERIFY, "VERIFY")
        self._send(APDU_SELECT, "SELECT")
        info = parse_tlv(self._send(APDU_INIT, "INIT")[:-2])
        for k, v in info.items():
            log.info("device info tag %02X: %s", k,
                     v.decode("ascii", "replace") if k == 0xC0 else v.hex(" ").upper())
        return info

    def send_frame(self, frame: bytes,
                   progress: Optional[Callable[[int, int], None]] = None,
                   refresh_timeout_s: float = 60.0, pad: bool = False) -> float:
        """DATA chunks + REFRESH + POLL, after begin(). Returns refresh seconds."""
        if pad and len(frame) % self.chunk:
            frame = frame + bytes(self.chunk - len(frame) % self.chunk)
        n = (len(frame) + self.chunk - 1) // self.chunk
        for seq in range(n):
            part = frame[seq * self.chunk:(seq + 1) * self.chunk]
            apdu = bytes([0xF0, 0xD2, seq >> 8, seq & 0xFF, len(part)]) + part
            self._send(apdu, f"DATA{seq:03d}")
            if progress:
                progress(seq + 1, n)

        self._send(APDU_REFRESH, "REFRESH")
        t0 = time.monotonic()
        time.sleep(1.5)
        saw_any = False
        while time.monotonic() - t0 < refresh_timeout_s:
            resp = self._send(APDU_POLL, "POLL", expect_ok=False)
            if resp:
                saw_any = True
            if resp and resp[0] == 0x00:
                dt = time.monotonic() - t0
                log.info("refresh complete after %.1f s", dt)
                return dt
            time.sleep(0.2)
        if not saw_any:
            raise EZSignError("lost contact with the display during refresh")
        raise EZSignError(f"refresh did not report completion within {refresh_timeout_s:.0f} s")

    def write(self, frame: bytes,
              progress: Optional[Callable[[int, int], None]] = None,
              refresh_timeout_s: float = 60.0, pad: bool = False) -> float:
        """begin() + send_frame(): the whole write in one call."""
        self.begin()
        return self.send_frame(frame, progress, refresh_timeout_s, pad)
