"""GL-FIX-AUDITORY-ORGANISM-RECONNECT (2026-07-22): the has_sound:false seam.

The 2026-07-15 full-field auditory deploy (5489d74c) retired the 1-D
``_last_sound_signal`` organism cache in process_sound_frame without
rewiring its consumer: ``_enqueue_organism_remember`` still snapshots that
slot within SENSE_BINDING_WINDOW_SEC to bind what she was hearing into each
word's organism experience.  Result: every organism experience bound
has_sound:false -- the organism was deaf while auditory L5 ran fully live.

The fix refills the SAME slot (no new store, no new index) after a frame
successfully settles, with ``_auditory_field_organism_reduction``: each of
the 16 gammatone channels' real pressure-envelope readings resampled onto a
fixed AUDITORY_ORGANISM_ENVELOPE_POINTS-point grid -- bounded,
deterministic, real physics of the actual frame.

These tests verify, against the real engine and the real organism path:
  (a) a word read within the window binds the real reduction (has_sound),
  (b) a word read outside the window binds without sound,
  (c) the reduction is deterministic for identical input,
  (d) the reduction is fixed-size regardless of frame duration,
  plus that embryo.experience_word actually stores the auditory lane
  (the auditory signal reaches the per-neuron observable and the binding
  is recorded).
"""
from __future__ import annotations

import io
import math
import queue as _queue
import struct
import time
import wave

import numpy as np
import pytest

from dsf_ai_service.v4.gualaloom_v5_engine import (
    AUDITORY_ORGANISM_ENVELOPE_POINTS,
    SENSE_BINDING_WINDOW_SEC,
    Guala,
    _auditory_field_organism_reduction,
    _organism_signal_with_senses,
)

EXPECTED_REDUCTION_SIZE = 16 * AUDITORY_ORGANISM_ENVELOPE_POINTS


def _tone_wav(duration_s: float = 1.0, freq_hz: float = 440.0) -> bytes:
    rate = 16_000
    n = int(rate * duration_s)
    values = [
        int(8_000 * math.sin(2.0 * math.pi * freq_hz * index / rate))
        for index in range(n)
    ]
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(struct.pack(f"<{len(values)}h", *values))
    return payload.getvalue()


def _silence_wav(duration_s: float = 0.5) -> bytes:
    rate = 16_000
    n = int(rate * duration_s)
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(struct.pack(f"<{n}h", *([0] * n)))
    return payload.getvalue()


@pytest.fixture
def engine(monkeypatch) -> Guala:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    value = Guala()
    try:
        yield value
    finally:
        value.shutdown()


def _hear(engine: Guala, wav: bytes) -> None:
    receipt = engine.process_sound_frame(
        wav,
        source="browser_microphone",
        source_anchor_ns=1_000_000_000,
        auditory_event_boundary="ambient",
    )
    assert receipt["accepted"] is True


class _CapturedQueue:
    """Context manager: swap in a fresh queue so the enqueued organism item
    can be inspected without racing the background worker, restoring the
    real queue afterward so shutdown() still reaches the real worker."""

    def __init__(self, engine: Guala):
        self._engine = engine

    def __enter__(self) -> _queue.Queue:
        self._old = self._engine._organism_queue
        fresh = _queue.Queue()
        self._engine._organism_queue = fresh
        return fresh

    def __exit__(self, *exc) -> None:
        self._engine._organism_queue = self._old


def test_settled_frame_refills_organism_snapshot(engine: Guala) -> None:
    assert getattr(engine, "_last_sound_signal", None) is None
    _hear(engine, _tone_wav())
    sig = engine._last_sound_signal
    assert sig is not None
    assert sig.shape == (EXPECTED_REDUCTION_SIZE,)
    assert np.any(sig != 0.0), "a real tone must leave real envelope energy"
    assert engine._last_sound_wall_time is not None
    assert time.time() - engine._last_sound_wall_time < SENSE_BINDING_WINDOW_SEC
    # The snapshot IS the reduction of the frame that actually settled.
    expected = _auditory_field_organism_reduction(
        engine._latest_auditory_full_field_capture)
    assert np.array_equal(sig, expected)


def test_word_within_window_binds_real_sound_reduction(engine: Guala) -> None:
    _hear(engine, _tone_wav())
    snapshot = engine._last_sound_signal.copy()
    with _CapturedQueue(engine) as q:
        engine._enqueue_organism_remember("bell")
        word, sight_signal, sound_signal, modal_signal = q.get_nowait()
    assert word == "bell"
    assert sound_signal is not None, "word within window must carry sound"
    assert np.array_equal(sound_signal, snapshot)
    # has_sound in the organism_experience_bound event is literally
    # `sound_signal is not None` on this tuple -- asserted at the source.


def test_word_outside_window_binds_without_sound(engine: Guala) -> None:
    _hear(engine, _tone_wav())
    # Simulate elapsed wall-clock beyond the binding window -- the same
    # honest condition _enqueue_organism_remember checks.
    engine._last_sound_wall_time = time.time() - (SENSE_BINDING_WINDOW_SEC + 0.5)
    with _CapturedQueue(engine) as q:
        engine._enqueue_organism_remember("bell")
        word, _sight, sound_signal, _modal = q.get_nowait()
    assert word == "bell"
    assert sound_signal is None, "expired audio must not bind"


def test_reduction_deterministic_for_identical_input(engine: Guala) -> None:
    wav = _tone_wav()
    _hear(engine, wav)
    first = engine._last_sound_signal.copy()
    capture = engine._latest_auditory_full_field_capture
    # Same capture reduced twice -> identical arrays (no state, no noise).
    assert np.array_equal(
        _auditory_field_organism_reduction(capture),
        _auditory_field_organism_reduction(capture))
    # Same physical bytes transduced again -> identical snapshot.
    _hear(engine, wav)
    second = engine._last_sound_signal
    assert np.array_equal(first, second)


def test_reduction_fixed_size_across_frame_durations(engine: Guala) -> None:
    _hear(engine, _tone_wav(duration_s=0.5))
    short = engine._last_sound_signal
    assert short.shape == (EXPECTED_REDUCTION_SIZE,)
    _hear(engine, _tone_wav(duration_s=2.0))
    long = engine._last_sound_signal
    assert long.shape == (EXPECTED_REDUCTION_SIZE,)
    # Different real frames are allowed to (and here do) differ in content;
    # only the shape is pinned.
    assert not np.array_equal(short, long)


def test_silent_frame_does_not_masquerade_as_heard_audio(engine: Guala) -> None:
    _hear(engine, _tone_wav())
    assert engine._last_sound_signal is not None
    # An all-silent settled frame means she is hearing silence NOW: the
    # previous sound has ended, so the slot clears -- a word read during
    # the silence binds no audio, rather than a zero-energy placeholder
    # or an already-over sound.
    _hear(engine, _silence_wav())
    assert engine._last_sound_signal is None
    assert engine._last_sound_wall_time is None
    with _CapturedQueue(engine) as q:
        engine._enqueue_organism_remember("hush")
        _word, _sight, sound_signal, _modal = q.get_nowait()
    assert sound_signal is None


def test_experience_word_stores_the_auditory_lane(engine: Guala) -> None:
    _hear(engine, _tone_wav())
    sound_signal = engine._last_sound_signal.copy()
    with_sound = _organism_signal_with_senses(
        "bell", engine._organism_transducer, None, sound_signal, None)
    without_sound = _organism_signal_with_senses(
        "bell", engine._organism_transducer, None, None, None)
    assert "auditory" in with_sound
    assert "auditory" not in without_sound

    # The lane reaches the per-neuron observable: the reduction drives the
    # neuron's auditory krimelack to real events (event_count is the live
    # production observable, engine.__init__'s observable="event_count").
    neuron = engine.organism.brain.hemispheres[0].cluster.neurons[0]
    deltas_with = neuron._unwrapped_deltas(with_sound)
    deltas_without = neuron._unwrapped_deltas(without_sound)
    assert deltas_with.get("auditory", 0.0) > 0.0
    assert deltas_without.get("auditory", 0.0) == 0.0

    # And the real experience_word() write path records the binding.
    before = neuron.binding_atlas.bindings
    engine.organism.experience_word("bell", with_sound)
    after = neuron.binding_atlas.bindings
    assert after > before


def test_worker_logs_has_sound_true_end_to_end(engine: Guala) -> None:
    _hear(engine, _tone_wav())
    engine._enqueue_organism_remember("chime")
    engine._organism_queue.join()
    events = [
        ev for ev in list(engine._substrate_events)
        if ev.kind == "organism_experience_bound"
        and ev.detail.get("word") == "chime"
    ]
    assert events, "the organism worker must log the binding"
    assert events[-1].detail["has_sound"] is True
    assert "sound" in events[-1].detail["senses"]
