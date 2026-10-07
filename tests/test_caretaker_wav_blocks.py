"""Finite WAV transport only; no organism, native trajectory or live calls."""
from __future__ import annotations

import struct
import wave

import pytest

from guala_caretaker.caretaker import wav_blocks


@pytest.mark.parametrize("samples", [4000 + 137, 8000, 137])
def test_final_wav_interval_preserves_every_recorded_sample(tmp_path, samples):
    raw = struct.pack(f"<{samples}h", *((i % 60001) - 30000 for i in range(samples)))
    path = tmp_path / "recording.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(raw)
    before = path.read_bytes()
    blocks = wav_blocks(str(path))
    assert len(blocks) == (samples + 3999) // 4000
    assert all(type(block) is bytes and len(block) == 8000 for block in blocks)
    delivered = b"".join(blocks)
    assert delivered[:len(raw)] == raw
    silence_bytes = (-len(raw)) % 8000
    assert delivered[len(raw):] == b"\0" * silence_bytes
    assert len(delivered) == len(raw) + silence_bytes
    assert path.read_bytes() == before


def test_wav_odd_pcm_tail_refuses_instead_of_dropping_half_sample(tmp_path):
    raw = b"\x12\x34\x56"
    # RIFF padding is outside the odd-length data chunk; it is not PCM.
    header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(raw) + 1,
                         b"WAVE", b"fmt ", 16, 1, 1, 16000, 32000, 2, 16,
                         b"data", len(raw))
    path = tmp_path / "odd.wav"
    path.write_bytes(header + raw + b"\0")
    before = path.read_bytes()
    with pytest.raises(ValueError, match="inside a signed16 sample"):
        wav_blocks(str(path))
    assert path.read_bytes() == before
