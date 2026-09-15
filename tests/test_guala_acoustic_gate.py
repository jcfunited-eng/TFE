"""Level 1: the acoustic gate (docs/GL-SPC-ACOUSTIC-GATE-C1-20260915-v1.md).

The bars, measured on real recordings from her library when they are present
(spoken words from Wikimedia Commons, a piece from the Internet Archive), and on
synthesized tones always."""
from __future__ import annotations

import math
import os
import struct

import pytest

from dsf_ai_service.guala_acoustic_gate import (
    EAR_BANDS, FRAMES_PER_HOP, MAX_EVENT_FRAMES, PAUSE_FRAMES, AcousticGate, events_of, hop_frames,
)

LIBRARY = "/workspaces/Tao_Financial_Engine/guala_caretaker/media"
SILENCE = b"\0" * 8000


def _tone(hz: float, beats: int = 2, amplitude: int = 9000) -> list[bytes]:
    return [struct.pack("<4000h", *(int(amplitude * math.sin(2 * math.pi * hz * (b * 4000 + i) / 16000)) for i in range(4000))) for b in range(beats)]


def _hops(path: str, start: int = 0, count: int | None = None) -> list[bytes]:
    raw = open(path, "rb").read()
    hops = [raw[i:i + 8000] for i in range(0, len(raw) - 7999, 8000)]
    return hops[start:start + count] if count else hops


def test_silence_has_no_event_and_a_tone_is_one_event_with_its_own_structure() -> None:
    assert events_of([SILENCE] * 6) == []
    frames, heard = hop_frames(SILENCE)
    assert len(frames) == FRAMES_PER_HOP and heard is False and all(f.energy == 0.0 for f in frames)
    low = events_of([SILENCE] * 2 + _tone(200) + [SILENCE] * 2)
    high = events_of([SILENCE] * 2 + _tone(3000) + [SILENCE] * 2)
    assert len(low) == 1 and len(high) == 1
    assert low[0].frames >= 24 and any(low[0].gates_per_band) and low[0].key != high[0].key
    # The same tone after another sound, with a pause between, is the same event.
    again = events_of([SILENCE] * 2 + _tone(3000) + [SILENCE] * 2 + _tone(200) + [SILENCE] * 2)
    assert [e.key for e in again] == [high[0].key, low[0].key]


def test_a_long_sound_becomes_a_sequence_of_bounded_events() -> None:
    long = events_of([SILENCE] + _tone(440, beats=30) + [SILENCE] * 2)
    assert all(e.frames <= MAX_EVENT_FRAMES for e in long) and len(long) >= 2
    assert sum(e.frames for e in long) >= 30 * FRAMES_PER_HOP - PAUSE_FRAMES * len(long) - FRAMES_PER_HOP


@pytest.mark.skipif(not os.path.exists(f"{LIBRARY}/words/en-us-apple.pcm"), reason="her library's spoken words are not on this machine")
def test_a_spoken_word_is_the_same_event_after_silence_and_after_music_and_words_differ() -> None:
    words = {w: _hops(f"{LIBRARY}/words/en-us-{w}.pcm") for w in ("apple", "water", "book", "hello", "bear", "star")}
    keys = {w: [e.key for e in events_of([SILENCE] * 4 + hops + [SILENCE] * 2)] for w, hops in words.items()}
    assert all(len(k) >= 1 for k in keys.values())
    flat = [k for ks in keys.values() for k in ks]
    assert len(set(flat)) == len(flat), "two different words gave the same event"
    music_path = f"{LIBRARY}/musopen-chopin/Allegro de Concert Op. 46 in A Major.pcm"
    if os.path.exists(music_path):
        music = _hops(music_path, 200, 30)
        after = events_of([SILENCE] * 4 + music + [SILENCE] * 2 + words["apple"] + [SILENCE] * 2)
        assert [e.key for e in after[-len(keys["apple"]):]] == keys["apple"], "the same recording after music was not the same event"
        music_events = events_of([SILENCE] * 4 + music + [SILENCE] * 2)
        assert len(music_events) >= 3 and all(e.frames <= MAX_EVENT_FRAMES for e in music_events)


def test_the_gate_is_deterministic_and_bounded_frame_by_frame() -> None:
    gate = AcousticGate()
    out = []
    for hop in [SILENCE] + _tone(500, beats=14) + [SILENCE] * 2:
        out.extend(gate.feed(hop))
    out.extend(gate.flush())
    once = [e.key for e in out]
    gate2 = AcousticGate()
    again = []
    for hop in [SILENCE] + _tone(500, beats=14) + [SILENCE] * 2:
        again.extend(gate2.feed(hop))
    again.extend(gate2.flush())
    assert once == [e.key for e in again] and all(e.frames <= MAX_EVENT_FRAMES for e in out)
