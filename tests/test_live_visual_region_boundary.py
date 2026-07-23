import time
import asyncio

import numpy as np
import pytest

from dsf_ai_service.substrate.visual_region_continuity import (
    CanonicalVisualFrame,
)
from dsf_ai_service.substrate.ring_buffer import InputRing
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_SAMPLE_RATE_HZ,
)
import dsf_ai_service.app as app_module
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _engine(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "visual-live-boundary-key")
    return Guala()


def _frames(offset=0, origin=None):
    if origin is None:
        origin = time.time_ns()
    values = []
    for index in range(4):
        rows, columns = np.indices((64, 64))
        pixels = ((rows * 7 + columns * 11 + index * 13 + offset) % 256).astype(
            np.uint8
        )
        values.append(
            CanonicalVisualFrame.from_uint8(
                origin + index * 1_000_000_000, pixels
            )
        )
    return tuple(values)


def test_live_visual_sequence_uses_complete_retina_and_not_random_fovea(
    monkeypatch,
):
    engine = _engine(monkeypatch)
    monkeypatch.setattr(
        engine.sight,
        "process_viewing",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("live sight invoked the legacy foveal path")
        ),
    )
    try:
        receipt = engine.process_live_visual_region_sequence(_frames())
        assert receipt["accepted"] is True
        settlement = receipt["settlement"]
        settlement.verify()
        sight = next(
            value for value in settlement.interpretations if value.sense == "sight"
        )
        assert len(sight.substreams) == 64
        assert engine._latest_visual_region_observation["regions"]
        assert engine.window_manager.open_context_ids("sense:sight:") == ()
    finally:
        engine.shutdown()


def test_visual_l5_rolls_back_if_causal_owner_rejects(monkeypatch):
    engine = _engine(monkeypatch)
    try:
        first_frames = _frames()
        engine.process_live_visual_region_sequence(first_frames)
        before = engine._visual_region_continuity.snapshot_encoded()
        prior = engine._latest_visual_region_observation
        prior_rejection = engine.record_live_visual_rejection(
            error_type="PriorVisualRejection",
            reason="prior visual rejection must survive rollback",
        )
        monkeypatch.setattr(
            engine._causal_experience_owner,
            "settle",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("injected causal owner rejection")
            ),
        )
        second_origin = (
            first_frames[-1].source_time_ns + 1_000_000
        )
        with pytest.raises(RuntimeError, match="injected causal owner"):
            engine.process_live_visual_region_sequence(
                _frames(offset=1, origin=second_origin)
            )
        assert engine._visual_region_continuity.snapshot_encoded() == before
        assert engine._latest_visual_region_observation == prior
        assert engine._latest_visual_region_rejection == prior_rejection
        assert engine.window_manager.open_context_ids("sense:sight:") == ()
    finally:
        engine.shutdown()


def test_visual_exposure_epoch_rolls_back_with_causal_owner(monkeypatch):
    engine = _engine(monkeypatch)
    auditory = AuditoryPCMStreamRegistry()
    stream_id = auditory.open()["stream_id"]
    try:
        first_frames = _frames()
        first_audio = auditory.accept(
            stream_id=stream_id,
            sequence=0,
            first_sample_index=0,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=b"\0\0" * 8,
        ).receipt
        engine.process_live_visual_region_sequence(
            first_frames,
            auditory_pcm_continuity=first_audio,
        )
        before = engine._visual_exposure_epoch.snapshot_encoded()
        monkeypatch.setattr(
            engine._causal_experience_owner,
            "settle",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("injected causal owner rejection")
            ),
        )
        second_audio = auditory.accept(
            stream_id=stream_id,
            sequence=1,
            first_sample_index=8,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=b"\0\0" * 8,
        ).receipt
        second_origin = first_frames[-1].source_time_ns + 1_000_000
        with pytest.raises(RuntimeError, match="injected causal owner"):
            engine.process_live_visual_region_sequence(
                _frames(offset=1, origin=second_origin),
                auditory_pcm_continuity=second_audio,
            )
        assert engine._visual_exposure_epoch.snapshot_encoded() == before
    finally:
        engine.shutdown()


def test_invalid_visual_sequence_creates_no_partial_window(monkeypatch):
    engine = _engine(monkeypatch)
    try:
        with pytest.raises(ValueError, match="four through eight"):
            engine.process_live_visual_region_sequence(_frames()[:3])
        assert engine.window_manager.open_context_ids("sense:sight:") == ()
        assert engine._visual_region_continuity.status()["history_count"] == 0
        assert engine._latest_visual_region_rejection["reason"]
    finally:
        engine.shutdown()


def test_remote_ring_admits_temporal_sight_and_live_paths_never_call_legacy():
    ring = InputRing(size=8)
    sequence = ring.publish("sight_sequence", "camera", frames=[])
    assert sequence == 0
    assert ring.drain()[0]["kind"] == "sight_sequence"
    for path in (
        "dsf_ai_service/app.py",
        "dsf_ai_service/substrate_runner.py",
    ):
        assert "process_sight_frame(" not in open(path, encoding="utf-8").read()


def test_live_sensory_request_is_bounded_before_json_allocation():
    calls = []
    chunks = [
        b"x" * app_module._LIVE_CAPTURE_REQUEST_MAX_BYTES,
        b"x",
    ]

    async def receive():
        value = chunks.pop(0)
        return {
            "type": "http.request",
            "body": value,
            "more_body": bool(chunks),
        }

    async def call_next(_request):
        calls.append("called")

    from starlette.requests import Request
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/sound_frame",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 1),
            "scheme": "http",
        },
        receive,
    )
    response = asyncio.run(
        app_module.bounded_live_sensory_ingress(request, call_next)
    )
    assert response.status_code == 413
    assert calls == []
