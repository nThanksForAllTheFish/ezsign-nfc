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
120 chunks; 2.9" 296x128 = 9,472 B = 37 chunks + 222 B. Only the 2.13" is
verified on hardware. Whether the others need anything beyond the chunk count
changing (and how the 2.9" wants its short last chunk) is UNVERIFIED; see README.
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

    def write(self, frame: bytes,
              progress: Optional[Callable[[int, int], None]] = None,
              refresh_timeout_s: float = 60.0, pad: bool = False) -> float:
        """Send *frame* and refresh. Returns refresh time in seconds.

        The frame is sent in self.chunk-byte DATA APDUs. If its length is not
        a multiple of the chunk size (the 2.9" 296x128 panel: 9,472 bytes =
        37 x 250 + 222), the final APDU is short by default, with Lc equal to
        the remaining byte count. pad=True instead zero-fills the last chunk
        to the full size. Which one the 2.9" firmware wants is unverified.
        """
        if pad and len(frame) % self.chunk:
            frame = frame + bytes(self.chunk - len(frame) % self.chunk)
        n = (len(frame) + self.chunk - 1) // self.chunk

        self._send(APDU_SELECT, "SELECT")
        resp = self._send(APDU_VERIFY, "VERIFY", expect_ok=False)
        if not sw_ok(resp):
            time.sleep(0.3)
            self._send(APDU_VERIFY, "VERIFY")
        self._send(APDU_SELECT, "SELECT")
        info = self._send(APDU_INIT, "INIT")
        for k, v in parse_tlv(info[:-2]).items():
            log.info("device info tag %02X: %s", k, v.hex(" ").upper() if k != 0xC0 else v.decode("ascii", "replace"))

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
