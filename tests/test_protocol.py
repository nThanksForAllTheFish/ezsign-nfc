from ezsign.protocol import (APDU_INIT, APDU_POLL, APDU_REFRESH, APDU_SELECT,
                             APDU_VERIFY, EZSign)


class FakeTag:
    """Replays the command sequence magic-epaper-app sends to a 2.13" EZ Sign."""

    def __init__(self, polls_until_ready=3):
        self.log = []
        self.data = bytearray()
        self.polls = polls_until_ready

    def __call__(self, apdu: bytes) -> bytes:
        self.log.append(apdu)
        if apdu in (APDU_SELECT, APDU_VERIFY, APDU_INIT, APDU_REFRESH):
            return b"\x90\x00"
        if apdu[:2] == b"\xF0\xD2":
            seq = (apdu[2] << 8) | apdu[3]
            assert seq == len(self.data) // 250, "chunks out of order"
            assert apdu[4] == len(apdu) - 5 <= 250
            self.data += apdu[5:]
            return b"\x90\x00"
        if apdu == APDU_POLL:
            self.polls -= 1
            return (b"\x00" if self.polls <= 0 else b"\x01") + b"\x90\x00"
        raise AssertionError(f"unexpected APDU {apdu.hex()}")


def test_sequence_and_payload(monkeypatch):
    import ezsign.protocol as p
    monkeypatch.setattr(p.time, "sleep", lambda s: None)
    frame = bytes(range(256)) * 117 + bytes(48)   # 30,000 bytes
    tag = FakeTag()
    EZSign(tag).write(frame)
    assert bytes(tag.data) == frame
    assert tag.log[:4] == [APDU_SELECT, APDU_VERIFY, APDU_SELECT, APDU_INIT]
    data_apdus = [a for a in tag.log if a[:2] == b"\xF0\xD2"]
    assert len(data_apdus) == 120
    assert tag.log[4 + 120] == APDU_REFRESH
    assert tag.log[-1] == APDU_POLL


def test_short_last_chunk_2in9(monkeypatch):
    import ezsign.protocol as p
    monkeypatch.setattr(p.time, "sleep", lambda s: None)
    frame = bytes(9472)                      # 296x128x2/8
    tag = FakeTag()
    EZSign(tag).write(frame)
    data_apdus = [a for a in tag.log if a[:2] == b"\xF0\xD2"]
    assert len(data_apdus) == 38
    assert data_apdus[-1][4] == 222 and len(data_apdus[-1]) == 227
    assert bytes(tag.data) == frame


def test_padded_last_chunk_2in9(monkeypatch):
    import ezsign.protocol as p
    monkeypatch.setattr(p.time, "sleep", lambda s: None)
    frame = bytes(9472)
    tag = FakeTag()
    EZSign(tag).write(frame, pad=True)
    data_apdus = [a for a in tag.log if a[:2] == b"\xF0\xD2"]
    assert len(data_apdus) == 38 and all(a[4] == 250 for a in data_apdus)
    assert bytes(tag.data) == frame + bytes(28)
