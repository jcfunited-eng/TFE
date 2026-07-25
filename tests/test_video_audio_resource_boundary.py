from __future__ import annotations

import asyncio
import base64
import io
import os
import shutil
import subprocess
import threading
import time
import wave
from fractions import Fraction
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import HTTPException
from PIL import Image

import dsf_ai_service.app as appmod
import dsf_ai_service.substrate_runner as substrate_runner
import dsf_ai_service.v4.gualaloom_v5_engine as engine_module
from dsf_ai_service.v4.gualaloom_v5_engine import Guala, VideoItem


def _pcm_wav(*, frame_count: int = 320, sample: int = 700) -> bytes:
    raw = int(sample).to_bytes(2, "little", signed=True) * frame_count
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16_000)
        target.writeframes(raw)
    return output.getvalue()


def _retained_frames(tmp_path, *, frame_count: int = 120):
    frame_dir = tmp_path / "frames"
    frame_dir.mkdir()
    frames = []
    rows, columns = np.indices((120, 160))
    for frame_index in range(frame_count):
        frame = ((
            rows * 17 + columns * 31 + frame_index * 13
        ) % 256).astype(np.uint8)
        frames.append(frame)
        np.save(frame_dir / f"frame_{frame_index + 1:05d}.npy", frame)
    return frame_dir, frames


def _configure_embedded_engine(monkeypatch) -> Guala:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    return Guala()


class _Upload:
    def __init__(self, payload: bytes, filename: str = "lesson.mp4") -> None:
        self.payload = payload
        self.filename = filename
        self.read_sizes = []

    async def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        return self.payload[:size]


def test_video_upload_rejects_before_an_unbounded_request_read() -> None:
    upload = _Upload(b"x" * (appmod._VIDEO_UPLOAD_MAX_BYTES + 1))

    with pytest.raises(HTTPException) as raised:
        asyncio.run(appmod.gualaloom_upload_video(upload))

    assert raised.value.status_code == 413
    assert upload.read_sizes == [appmod._VIDEO_UPLOAD_MAX_BYTES + 1]


def test_video_decode_has_duration_frame_and_retention_boundaries(
        monkeypatch) -> None:
    commands = []
    events = []
    fake_engine = SimpleNamespace(
        lock=threading.RLock(),
        _videos={},
        tick=7,
        _log_substrate_event=lambda kind, **detail: events.append(
            (kind, detail)),
    )

    async def run_inline(function, *args):
        return function(*args)

    def bounded_ffmpeg(command, **kwargs):
        commands.append((command, kwargs))
        output_template = command[command.index("-frames:v") + 2]
        output_path = output_template.replace("%05d", "00001")
        Image.new("L", (160, 120), color=127).save(output_path)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(appmod, "_is_remote", lambda: False)
    monkeypatch.setattr(appmod, "_gl_init", lambda: None)
    monkeypatch.setattr(appmod, "_guala", fake_engine)
    monkeypatch.setattr(appmod, "_run_lifecycle_executor", run_inline)
    monkeypatch.setattr(subprocess, "run", bounded_ffmpeg)
    decode_calls = []
    monkeypatch.setattr(
        substrate_runner,
        "_webm_to_wav_bytes",
        lambda payload, **kwargs: (
            decode_calls.append((payload, kwargs)), _pcm_wav()
        )[1],
    )

    result = asyncio.run(appmod.gualaloom_upload_video(_Upload(b"video")))
    video = fake_engine._videos[result["item_id"]]
    retained_root = os.path.dirname(video.frame_dir)
    try:
        assert len(commands) == 1
        assert decode_calls == [(
            b"video",
            {"encoded_max_bytes": appmod._VIDEO_UPLOAD_MAX_BYTES},
        )]
        command, kwargs = commands[0]
        assert command[command.index("-t") + 1] == str(
            appmod._VIDEO_CAPTURE_MAX_SECONDS)
        assert command[command.index("-r") + 1] == str(
            appmod._VIDEO_FRAME_RATE)
        assert command[command.index("-frames:v") + 1] == str(
            appmod._VIDEO_MAX_RETAINED_FRAMES)
        assert kwargs["timeout"] == 60
        assert video.n_frames == 1
        assert os.listdir(video.frame_dir) == ["frame_00001.npy"]
        retained_frame = np.load(
            os.path.join(video.frame_dir, "frame_00001.npy"),
            allow_pickle=False)
        assert retained_frame.dtype == np.uint8
        assert retained_frame.shape == (120, 160)
        assert np.all(retained_frame == 127)
        assert not os.path.exists(os.path.join(retained_root, "input.mp4"))
        assert os.path.getsize(video.audio_path) <= (
            engine_module.REPLAY_SOUND_MAX_WAV_BYTES)
        assert events[0][0] == "video_uploaded"
    finally:
        shutil.rmtree(retained_root, ignore_errors=True)


def test_real_upload_frame_representation_enters_video_causal_attention(
        monkeypatch) -> None:
    engine = _configure_embedded_engine(monkeypatch)
    retained_root = None

    async def run_inline(function, *args):
        return function(*args)

    def bounded_ffmpeg(command, **kwargs):
        output_template = command[command.index("-frames:v") + 2]
        Image.new("L", (160, 120), color=127).save(
            output_template.replace("%05d", "00001"))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(appmod, "_is_remote", lambda: False)
    monkeypatch.setattr(appmod, "_gl_init", lambda: None)
    monkeypatch.setattr(appmod, "_guala", engine)
    monkeypatch.setattr(appmod, "_run_lifecycle_executor", run_inline)
    monkeypatch.setattr(subprocess, "run", bounded_ffmpeg)
    monkeypatch.setattr(
        substrate_runner, "_webm_to_wav_bytes",
        lambda _payload, **_kwargs: _pcm_wav())
    try:
        result = asyncio.run(appmod.gualaloom_upload_video(_Upload(b"video")))
        video = engine._videos[result["item_id"]]
        retained_root = os.path.dirname(video.frame_dir)
        activity = SimpleNamespace(
            target=video.item_id, started_tick=engine.tick,
            expected_end_tick=engine.tick + 20, metadata={})

        Guala._atick_attending_video(engine, activity)

        assert activity.metadata["_video_causal_settled"] is True
        assert activity.metadata["_audiovisual_settled"] is True
        assert activity.metadata["sight_causal_entries"] == 16
        assert activity.metadata["audio_causal_entries"] == 16
        assert engine.window_manager.open_context_ids() == ()
        observed = {
            item.sense for item in engine._latest_causal_settlement.interpretations
            if item.state == "observed"
        }
        assert observed == {"sight", "sound"}
    finally:
        engine.shutdown()
        if retained_root:
            shutil.rmtree(retained_root, ignore_errors=True)


def test_retained_video_retina_uses_every_pixel_frame_and_exact_cadence(
        tmp_path) -> None:
    frame_dir, frames = _retained_frames(tmp_path)

    started = time.perf_counter()
    signals, phases, offsets_ns = Guala._retained_video_retinal_field(
        str(frame_dir))
    elapsed = time.perf_counter() - started

    assert len(signals) == 16
    assert all(len(signal) == 120 for signal in signals)
    assert len(phases) == 16
    assert all(len(phase) == 120 for phase in phases)
    assert offsets_ns == tuple(
        (Fraction(index, 15).numerator, Fraction(index, 15).denominator)
        for index in range(120))
    for frame_index, frame in enumerate(frames):
        for topology_index in range(16):
            row, column = divmod(topology_index, 4)
            region = frame[
                row * 30:(row + 1) * 30,
                column * 40:(column + 1) * 40,
            ]
            expected = 2.0 * (
                int(region.sum(dtype=np.uint64)) / (255.0 * region.size)
            ) - 1.0
            assert signals[topology_index][frame_index] == pytest.approx(
                expected, abs=1e-15)
    first_intensity = (signals[0][0] + 1.0) / 2.0
    expected_first_phase_turns = (
        (5.0 + 50.0 * first_intensity) / 15.0 / (2.0 * np.pi))
    assert phases[0][0] == pytest.approx(expected_first_phase_turns, abs=1e-15)
    assert any(value != 0.0 for value in phases[0])
    # A generous production regression wall: the bounded retinal integration
    # itself must remain seconds, not minutes, on the test runner.
    assert elapsed < 5.0


def test_exact_legacy_video_frame_is_read_without_mutating_sealed_source(
        tmp_path) -> None:
    original = (
        np.arange(120 * 160, dtype=np.uint32).reshape(120, 160) % 256
    ).astype(np.uint8)
    legacy = original.astype(np.float64) / 255.0
    frame_path = tmp_path / "frame_00001.npy"
    np.save(frame_path, legacy)

    loaded, was_legacy = Guala._load_retained_video_frame(str(frame_path))

    assert was_legacy is True
    assert np.array_equal(loaded, original)
    assert np.load(frame_path, allow_pickle=False).dtype == np.float64


def test_non_reversible_legacy_video_frame_fails_closed(tmp_path) -> None:
    legacy = np.zeros((120, 160), dtype=np.float64)
    legacy[0, 0] = 0.1
    frame_path = tmp_path / "frame_00001.npy"
    np.save(frame_path, legacy)

    with pytest.raises(ValueError, match="not exactly reversible"):
        Guala._load_retained_video_frame(str(frame_path))


def test_next_staged_generation_preserves_exact_legacy_video_frame_bytes(
        tmp_path) -> None:
    source_dir = tmp_path / "sealed-source"
    source_dir.mkdir()
    original = (
        np.arange(120 * 160, dtype=np.uint32).reshape(120, 160) % 256
    ).astype(np.uint8)
    source_path = source_dir / "frame_00001.npy"
    np.save(source_path, original.astype(np.float64) / 255.0)
    source_bytes = source_path.read_bytes()
    metadata_path = source_dir / "decoder-metadata.txt"
    metadata_path.write_bytes(b"15fps-gray")
    video = VideoItem(
        item_id="legacy", title="legacy", frame_dir=str(source_dir),
        n_frames=1)
    engine = object.__new__(Guala)
    engine.lock = threading.RLock()
    engine._pictures = {}
    engine._videos = {"legacy": video}
    _records, assets = Guala._video_persistence_snapshot(engine)
    state_dir = tmp_path / "state"

    Guala._materialize_media_assets(engine, str(state_dir), {}, assets)

    assert np.load(source_path, allow_pickle=False).dtype == np.float64
    installed_path = os.path.join(video.frame_dir, "frame_00001.npy")
    assert open(installed_path, "rb").read() == source_bytes
    assert open(
        os.path.join(video.frame_dir, "decoder-metadata.txt"), "rb"
    ).read() == b"15fps-gray"


def test_video_attention_routes_one_full_audiovisual_settlement_once(
        tmp_path, monkeypatch) -> None:
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(_pcm_wav(frame_count=128_000))
    frame_dir, _frames = _retained_frames(tmp_path)
    video = VideoItem(
        item_id="lesson", title="lesson", frame_dir=str(frame_dir),
        audio_path=str(audio_path), n_frames=120)
    engine = _configure_embedded_engine(monkeypatch)
    engine._videos = {"lesson": video}
    settled_records = []
    settle_window = engine.window_manager._settle_window
    engine.window_manager._settle_window = lambda record: (
        settled_records.append(record), settle_window(record))[1]
    activity = SimpleNamespace(
        target="lesson", started_tick=engine.tick,
        expected_end_tick=engine.tick + 20, metadata={})
    try:
        accepted_before = engine._causal_settlement_accepted
        Guala._atick_attending_video(engine, activity)
        Guala._atick_attending_video(engine, activity)

        assert engine._causal_settlement_accepted == accepted_before + 1
        assert engine._causal_settlement_failed == 0
        assert activity.metadata["_video_causal_settled"] is True
        assert activity.metadata["_audiovisual_settled"] is True
        assert activity.metadata["sight_causal_entries"] == 16
        assert activity.metadata["audio_causal_entries"] == 16
        assert engine.window_manager.open_context_ids() == ()
        settlement = engine._latest_causal_settlement
        settlement.verify()
        observed = {
            item.sense: item for item in settlement.interpretations
            if item.state == "observed"
        }
        assert set(observed) == {"sight", "sound"}
        assert len(observed["sight"].substreams) == 16
        assert len(observed["sound"].substreams) == 16
        assert tuple(
            item.substream_id for item in observed["sight"].substreams
        ) == tuple(
            f"retinal-field-{row}-{column}"
            for row in range(4) for column in range(4)
        )
        assert len(settled_records) == 1
        native_inputs = [
            entry["provenance"]["detail"]["native_full_field_input"]
            for entry in settled_records[0]["entries"]
            if "native_full_field_input"
            in entry["provenance"]["detail"]
        ]
        assert len(native_inputs) == 32
        assert sum(
            len(value["normalized_signal"]) for value in native_inputs
        ) == 14_720
        assert engine._causal_experience_owner.status()[
            "transition_relations"] <= 1_024
        assert engine._auditory_l5_owner.status()[
            "transition_relations"] <= 1_024
        assert engine._organism_sensory_queue.qsize() == 0
    finally:
        engine.shutdown()


def test_video_without_audio_settles_sight_and_marks_sound_unavailable(
        tmp_path, monkeypatch) -> None:
    import dsf_ai_service.glew_runtime.native_sensory_full_field as native_boundary
    from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
        PhysicalSense)

    frame_dir = tmp_path / "frames"
    frame_dir.mkdir()
    rows, columns = np.indices((120, 160))
    for frame_index in range(2):
        frame = ((rows * 7 + columns * 19 + frame_index) % 256).astype(
            np.uint8)
        np.save(
            frame_dir / f"frame_{frame_index:05d}.npy",
            frame.astype(np.float64) / 255.0)
    sealed_bytes = {
        path.name: path.read_bytes() for path in frame_dir.iterdir()
    }
    video = VideoItem(
        item_id="silent", title="silent", frame_dir=str(frame_dir),
        audio_path="", n_frames=2)
    engine = _configure_embedded_engine(monkeypatch)
    engine._videos = {"silent": video}
    settled_records = []
    admitted_fields = []
    settle_window = engine.window_manager._settle_window
    engine.window_manager._settle_window = lambda record: (
        settled_records.append(record), settle_window(record))[1]
    build_field = native_boundary.build_six_sense_full_field

    def capture_admitted_field(**kwargs):
        admitted_fields.append(kwargs)
        return build_field(**kwargs)

    monkeypatch.setattr(
        native_boundary, "build_six_sense_full_field", capture_admitted_field)
    activity = SimpleNamespace(
        target="silent", started_tick=engine.tick,
        expected_end_tick=engine.tick + 20, metadata={})
    try:
        accepted_before = engine._causal_settlement_accepted
        Guala._atick_attending_video(engine, activity)

        assert engine._causal_settlement_accepted == accepted_before + 1
        assert engine.window_manager.open_context_ids() == ()
        assert activity.metadata["_video_causal_settled"] is True
        assert "_audiovisual_settled" not in activity.metadata
        assert activity.metadata["_audio_unavailable"] == (
            "video_has_no_retained_audio")
        by_sense = {
            item.sense: item
            for item in engine._latest_causal_settlement.interpretations
        }
        settlement = engine._latest_causal_settlement
        assert settlement.source_time_end - settlement.source_time_start == (
            Fraction(2, 15))
        assert by_sense["sight"].state == "observed"
        assert len(by_sense["sight"].substreams) == 16
        assert by_sense["sound"].state == "sensor_unavailable"
        assert by_sense["sound"].substreams == ()
        assert len(settled_records) == 1
        native_sight = [
            entry["provenance"]["detail"]["native_full_field_input"]
            for entry in settled_records[0]["entries"]
            if entry["modality"] == "sight"
        ]
        assert len(native_sight) == 16
        assert all(value["schema"] == "guala.native_sensory_input.v2"
                   for value in native_sight)
        assert all(value["causal_offsets_fraction"] == [[0, 1], [1, 15]]
                   for value in native_sight)
        assert len(admitted_fields) == 1
        admitted_sight = admitted_fields[0]["observed_substreams"][
            PhysicalSense.SIGHT]
        assert all(
            port.source_times[1] - port.source_times[0] == Fraction(1, 15)
            for port in admitted_sight)
        assert {
            path.name: path.read_bytes() for path in frame_dir.iterdir()
        } == sealed_bytes
    finally:
        engine.shutdown()


def test_video_attention_failure_discards_context_without_partial_settlement(
        tmp_path, monkeypatch) -> None:
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(_pcm_wav(frame_count=320))
    frame_dir, _frames = _retained_frames(tmp_path, frame_count=2)
    video = VideoItem(
        item_id="lesson", title="lesson", frame_dir=str(frame_dir),
        audio_path=str(audio_path), n_frames=2)
    engine = _configure_embedded_engine(monkeypatch)
    engine._videos = {"lesson": video}
    engine.process_sound_frame = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        RuntimeError("injected auditory failure"))
    activity = SimpleNamespace(
        target="lesson", started_tick=engine.tick,
        expected_end_tick=engine.tick + 20, metadata={})
    try:
        accepted_before = engine._causal_settlement_accepted
        Guala._atick_attending_video(engine, activity)

        assert engine._causal_settlement_accepted == accepted_before
        assert engine.window_manager.open_context_ids() == ()
        assert "injected auditory failure" in activity.metadata[
            "_video_causal_unavailable"]
        assert "_audiovisual_settled" not in activity.metadata
        assert "_video_causal_settled" not in activity.metadata
        assert video.times_attended == 0
    finally:
        engine.shutdown()


def _native_timing_record(*, context_detail, native_input):
    return {
        "window_id": "window-test",
        "context_detail": context_detail,
        "entries": [{
            "chi": 0,
            "source_tag": "test",
            "provenance": {"detail": {
                "native_full_field_input": native_input,
            }},
        }],
    }


def _rational_sight_input():
    return {
        "schema": "guala.native_sensory_input.v2",
        "sense": "sight",
        "sensor_id": "test-retina",
        "substream_id": "retinal-field-0-0",
        "topology_index": 0,
        "coordinates": [["retinal-row", "0"]],
        "physical_quantity": "regional-mean-light-intensity",
        "physical_unit": "normalized-full-scale-intensity",
        "source_anchor_fraction": [1, 1],
        "causal_offsets_fraction": [[0, 1]],
        "normalized_signal": [0.0],
        "phase_turns": [0.0],
    }


def test_causal_adapter_rejects_mixed_rational_and_ns_context_interval() -> None:
    engine = object.__new__(Guala)
    engine._causal_experience_owner = object()
    record = _native_timing_record(
        context_detail={
            "source_time_start_fraction": [1, 1],
            "source_time_end_fraction": [2, 1],
            "source_time_start_ns": 1_000_000_000,
            "source_time_end_ns": 2_000_000_000,
        },
        native_input=_rational_sight_input(),
    )

    with pytest.raises(RuntimeError, match="mixes ns and rational"):
        Guala._build_causal_window_settlement(engine, record)


def test_causal_adapter_rejects_mixed_native_timing_transport() -> None:
    engine = object.__new__(Guala)
    engine._causal_experience_owner = object()
    native = _rational_sight_input()
    native["source_anchor_ns"] = 1_000_000_000
    native["causal_offsets_ns"] = [0]
    record = _native_timing_record(
        context_detail={
            "source_time_start_fraction": [1, 1],
            "source_time_end_fraction": [2, 1],
        },
        native_input=native,
    )

    with pytest.raises(RuntimeError, match="mixes ns and rational"):
        Guala._build_causal_window_settlement(engine, record)


def test_causal_adapter_rejects_boolean_legacy_ns_offset() -> None:
    engine = object.__new__(Guala)
    engine._causal_experience_owner = object()
    native = _rational_sight_input()
    native.update({
        "schema": "guala.native_sensory_input.v1",
        "source_anchor_ns": 1_000_000_000,
        "causal_offsets_ns": [False],
    })
    native.pop("source_anchor_fraction")
    native.pop("causal_offsets_fraction")
    record = _native_timing_record(
        context_detail={
            "source_time_start_ns": 1_000_000_000,
            "source_time_end_ns": 2_000_000_000,
        },
        native_input=native,
    )

    with pytest.raises(RuntimeError, match="ns causal offsets are invalid"):
        Guala._build_causal_window_settlement(engine, record)


def test_causal_adapter_rejects_noncanonical_rational_offset() -> None:
    engine = object.__new__(Guala)
    engine._causal_experience_owner = object()
    native = _rational_sight_input()
    native["causal_offsets_fraction"] = [[0, 2]]
    record = _native_timing_record(
        context_detail={
            "source_time_start_fraction": [1, 1],
            "source_time_end_fraction": [2, 1],
        },
        native_input=native,
    )

    with pytest.raises(RuntimeError, match="not canonical"):
        Guala._build_causal_window_settlement(engine, record)


def test_sounds_state_rejects_bytes_before_parse_and_caps_legacy_raw_signal(
        tmp_path, monkeypatch) -> None:
    oversized = tmp_path / "guala_sounds.json"
    with oversized.open("wb") as output:
        output.truncate(engine_module.SOUNDS_STATE_MAX_BYTES + 1)

    with pytest.raises(ValueError, match="pre-parse byte boundary"):
        Guala._load_sounds_state_file(str(oversized))

    monkeypatch.setattr(engine_module, "LEGACY_SOUND_MAX_RAW_SAMPLES", 2)
    legacy = {
        "legacy": {
            "item_id": "legacy",
            "title": "legacy",
            "times_attended": 0,
            "last_attended_tick": 0,
            "cochlear": {},
            "raw_signal": [0.0, 0.1, 0.2],
        },
    }
    with pytest.raises(ValueError, match="legacy sample boundary"):
        Guala._validate_sounds_payload(legacy, engine_tick=1)


def test_remote_ring_capacity_refusal_is_not_labeled_queued(
        monkeypatch) -> None:
    class _RefusingClient:
        async def call(self, *_args, **_kwargs):
            return {"ok": False, "error": "input ring capacity reached"}

    monkeypatch.setattr(appmod, "_is_remote", lambda: True)
    monkeypatch.setattr(appmod, "_get_substrate_client", _RefusingClient)
    monkeypatch.setattr(
        appmod, "_spoken_word_recognition_report", lambda _source: {})
    message = appmod.GLMessage(
        text=base64.b64encode(b"audio").decode("ascii"),
        source="joe_voice",
        capture_started_ms=1_000,
        capture_ended_ms=2_000,
        capture_purpose="utterance",
    )

    result = asyncio.run(appmod.sound_frame(message))

    assert result["ok"] is False
    assert result["causal_boundary"] == "unsettled"
    assert "capacity" in result["error"]
