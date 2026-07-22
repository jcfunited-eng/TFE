from __future__ import annotations

import copy
import io
import math
import struct
import wave

import pytest

from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _tone_wav() -> bytes:
    rate = 16_000
    values = [
        int(8_000 * math.sin(2.0 * math.pi * 440.0 * index / rate))
        for index in range(320)
    ]
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(struct.pack(f"<{len(values)}h", *values))
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


def test_sound_frame_mounts_one_interleaved_32_component_window(
    engine: Guala,
) -> None:
    records = []
    settle = engine.window_manager._settle_window

    def capture(record):
        records.append(copy.deepcopy(record))
        return settle(record)

    engine.window_manager._settle_window = capture
    anchor_ns = 1_000_000_003

    result = engine.process_sound_frame(
        _tone_wav(),
        source="browser_microphone",
        source_anchor_ns=anchor_ns,
        source_time_end_ns=anchor_ns + 20_000_000,
        auditory_event_boundary="ambient",
    )

    assert result["accepted"] is True
    assert result["entries_bound"] == 32
    assert len(records) == 1
    sound_entries = [
        item for item in records[0]["entries"]
        if item["modality"] == "sound"
    ]
    assert len(sound_entries) == 32
    native = [
        item["provenance"]["detail"]["native_full_field_input"]
        for item in sound_entries
    ]
    assert [item["topology_index"] for item in native] == list(range(32))
    assert [item["substream_id"] for item in native[:4]] == [
        "erb_00_pressure",
        "erb_00_phase_advance",
        "erb_01_pressure",
        "erb_01_phase_advance",
    ]
    assert all(item["schema"] == "guala.native_sensory_input.v2"
               for item in native)
    assert all(item["source_anchor_fraction"] == [anchor_ns, 1_000_000_000]
               for item in native)
    assert all("chi" not in item for item in native)
    assert all(value == 0.0 for value in native[0]["phase_turns"])
    assert native[1]["normalized_signal"] == list(
        engine._latest_auditory_full_field_capture.channels[
            0
        ].carrier_phase_advance_nyquist_fraction
    )
    settlement = result["settlement"]
    settlement.verify()
    sound = next(
        item for item in settlement.interpretations if item.sense == "sound"
    )
    assert len(sound.substreams) == 32
    assert tuple(item.substream_id for item in sound.substreams[:4]) == (
        "erb_00_pressure",
        "erb_00_phase_advance",
        "erb_01_pressure",
        "erb_01_phase_advance",
    )
    assert engine.window_manager.open_context_ids() == ()


def test_sound_frame_mount_failure_has_no_legacy_fallback(
    engine: Guala, monkeypatch
) -> None:
    import dsf_ai_service.substrate.auditory_kernel_mount as mount

    def reject(*_args, **_kwargs):
        raise ValueError("injected mount rejection")

    monkeypatch.setattr(mount, "auditory_kernel_component_records", reject)
    before = engine._causal_settlement_accepted

    with pytest.raises(ValueError, match="injected mount rejection"):
        engine.process_sound_frame(
            _tone_wav(),
            source="browser_microphone",
            source_anchor_ns=1_000_000_003,
            source_time_end_ns=1_020_000_003,
            auditory_event_boundary="ambient",
        )

    assert engine._causal_settlement_accepted == before
    assert engine._latest_auditory_full_field_capture is None
    assert engine.window_manager.open_context_ids() == ()
