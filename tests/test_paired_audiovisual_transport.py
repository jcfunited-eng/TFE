from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import dsf_ai_service.app as appmod


def _unknown_auditory_status():
    return {
        "latest_experience_id": "0" * 64,
        "recognitions": [
            {"kind": "spoken_form", "state": "unknown",
             "tutor_label": None, "candidate_labels": []},
            {"kind": "source_continuity", "state": "unknown",
             "tutor_label": None, "candidate_labels": []},
        ],
    }


class _RecordingWindowManager:
    def __init__(self, calls: list[tuple]) -> None:
        self.calls = calls
        self.active = None
        self.owner = None

    def begin_context(self, context_id, trigger_reason, context_detail=None):
        assert self.active is None
        self.active = context_id
        self.calls.append(("begin", context_id, trigger_reason, context_detail))

    def end_context(self, context_id, reason, *, return_settlement=False):
        assert context_id == self.active
        self.calls.append(("end", context_id, reason))
        self.active = None
        observed = []
        if any(call[0] == "sight" for call in self.calls):
            observed.append("sight")
        if any(call[0] == "sound" for call in self.calls):
            observed.append("sound")
        settlement = SimpleNamespace(
            assembly_id=f"causal-{context_id}",
            interpretations=tuple(
                SimpleNamespace(sense=sense, state="observed")
                for sense in observed
            ),
            verify=lambda: None,
        )
        self.owner._latest_causal_settlement = settlement
        if return_settlement:
            return context_id, settlement
        return context_id


def _capture_message(**values):
    return appmod.GLMessage(
        capture_started_ms=1_000,
        capture_ended_ms=6_000,
        sight_captured_ms=1_000,
        **values,
    )


def test_sound_request_binds_paired_camera_frame_in_one_context(
        monkeypatch) -> None:
    import dsf_ai_service.substrate_runner as substrate_runner

    calls = []
    windows = _RecordingWindowManager(calls)
    def process_sight(grid, **_kwargs):
        calls.append(("sight", windows.active, tuple(grid.shape)))
        return {"accepted": True, "entries_bound": 3}

    def process_sound(wav, source=None, **_kwargs):
        calls.append(("sound", windows.active, wav, source))
        return {"accepted": True, "entries_bound": 6}

    fake = SimpleNamespace(
        tick=42,
        window_manager=windows,
        process_sight_frame=process_sight,
        process_sound_frame=process_sound,
        _latest_causal_settlement=None,
        auditory_l5_status=_unknown_auditory_status,
        _log_substrate_event=lambda *_args, **_kwargs: None,
    )
    windows.owner = fake
    monkeypatch.setattr(appmod, "_guala", fake)
    monkeypatch.setattr(appmod, "_converse_inflight", 0)
    monkeypatch.setattr(appmod, "_converse_window_started_at", 0.0)
    monkeypatch.setattr(
        substrate_runner, "_webm_to_wav_bytes", lambda _payload: b"RIFFwav")
    monkeypatch.setattr(
        appmod, "decode_image_bytes",
        lambda _payload: (None, np.zeros((8, 8)), None, None))
    monkeypatch.setenv("VOICE_WHISPER", "0")

    response = asyncio.run(appmod.sound_frame(_capture_message(
        text=base64.b64encode(b"webm").decode("ascii"),
        source="joe_voice",
        sight_b64=base64.b64encode(b"jpeg").decode("ascii"),
    )))

    assert response["ok"] is True
    assert response["causal_boundary"] == "audiovisual"
    assert [call[0] for call in calls] == ["begin", "sight", "sound", "end"]
    context_id = calls[0][1]
    assert calls[1][1] == context_id
    assert calls[2][1] == context_id
    assert calls[3][1] == context_id
    assert windows.active is None


def test_failed_sight_does_not_erase_sound_or_common_settlement(
        monkeypatch) -> None:
    import dsf_ai_service.substrate_runner as substrate_runner

    calls = []
    windows = _RecordingWindowManager(calls)

    def fail_sight(_grid, **_kwargs):
        calls.append(("sight_failed", windows.active))
        raise ValueError("invalid camera frame")

    def process_sound(wav, source=None, **_kwargs):
        calls.append(("sound", windows.active, wav, source))
        return {"accepted": True, "entries_bound": 6}

    fake = SimpleNamespace(
        tick=42,
        window_manager=windows,
        process_sight_frame=fail_sight,
        process_sound_frame=process_sound,
        _latest_causal_settlement=None,
        auditory_l5_status=_unknown_auditory_status,
        _log_substrate_event=lambda *args, **kwargs: calls.append(
            ("event", args, kwargs)),
    )
    windows.owner = fake
    monkeypatch.setattr(appmod, "_guala", fake)
    monkeypatch.setattr(appmod, "_converse_inflight", 0)
    monkeypatch.setattr(appmod, "_converse_window_started_at", 0.0)
    monkeypatch.setattr(
        substrate_runner, "_webm_to_wav_bytes", lambda _payload: b"RIFFwav")
    monkeypatch.setattr(
        appmod, "decode_image_bytes",
        lambda _payload: (None, np.zeros((8, 8)), None, None))
    monkeypatch.setenv("VOICE_WHISPER", "0")

    response = asyncio.run(appmod.sound_frame(_capture_message(
        text=base64.b64encode(b"webm").decode("ascii"),
        source="joe_voice",
        sight_b64=base64.b64encode(b"jpeg").decode("ascii"),
    )))

    assert response["ok"] is True
    assert response["raw_sound"] == "accepted"
    assert response["causal_boundary"] == "sound"
    assert response["observed_senses"] == ["sound"]
    assert "sight" in response["sensory_errors"]
    assert any(call[0] == "sound" for call in calls)
    assert any(call[0] == "end" for call in calls)
    assert windows.active is None


def test_remote_transport_preserves_paired_image_and_reports_queued_state(
        monkeypatch) -> None:
    calls = []

    class _Client:
        async def call(self, operation, **kwargs):
            calls.append((operation, kwargs))
            return {"ok": True, "seq": 7}

    monkeypatch.setattr(appmod, "_is_remote", lambda: True)
    monkeypatch.setattr(appmod, "_get_substrate_client", lambda: _Client())
    sight = base64.b64encode(b"jpeg").decode("ascii")

    response = asyncio.run(appmod.sound_frame(_capture_message(
        text=base64.b64encode(b"webm").decode("ascii"),
        source="joe_voice",
        sight_b64=sight,
    )))

    assert response["ok"] is True
    assert response["causal_boundary"] == "queued_audiovisual"
    assert calls[0][0] == "ring_write"
    assert calls[0][1]["data"]["sight_b64"] == sight
    assert calls[0][1]["data"]["source_time_start_ns"] == 1_000_000_000
    assert calls[0][1]["data"]["source_time_end_ns"] == 6_000_000_000
    assert calls[0][1]["data"]["sight_source_anchor_ns"] == 1_000_000_000


def test_paired_capture_without_authoritative_times_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(appmod, "_is_remote", lambda: True)
    response = asyncio.run(appmod.sound_frame(appmod.GLMessage(
        text=base64.b64encode(b"webm").decode("ascii"),
        source="joe_voice",
        sight_b64=base64.b64encode(b"jpeg").decode("ascii"),
    )))

    assert response["ok"] is False
    assert response["causal_boundary"] == "unsettled"
    assert "timestamps are required" in response["error"]


def test_browser_suppresses_duplicate_camera_stream_during_mic_capture() -> None:
    html = Path("dsf_ai_service/static/gualaloom.html").read_text()
    assert "if(micPCMActive)return;" in html
    assert "utteranceTransitioning" not in html
    assert "utteranceActive" not in html
    assert "const promise=camStream?captureConversationSight()" in html
    assert "JSON.stringify({text,source,sight_b64})" not in html
    assert "JSON.stringify({text,source})" in html
    assert "audio_first_sample_index:firstSampleIndex" in html
    assert "if(epoch.pendingChunks>=PCM_MAX_PENDING_CHUNKS)" in html
