from __future__ import annotations

import asyncio
import base64
from dataclasses import replace
import hashlib
import json
import math
import struct
from io import BytesIO

import pytest
from PIL import Image
from fastapi.testclient import TestClient

import dsf_ai_service.app as app_module
import dsf_ai_service.substrate_runner as substrate_runner
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_SAMPLE_RATE_HZ,
    pcm_s16le_wav,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    bind_auditory_stream_settlement,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryIncrementalAdvance,
    AuditoryIncrementalStatus,
    _advance_payload,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _pcm(*, offset: int, count: int) -> bytes:
    values = tuple(
        int(8_000 * math.sin(2 * math.pi * 440 * (offset + index) / 16_000))
        for index in range(count)
    )
    return struct.pack(f"<{len(values)}h", *values)


@pytest.fixture
def engine(monkeypatch) -> Guala:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "pcm-http-transport-key")
    value = Guala()
    monkeypatch.setattr(app_module, "_guala", value)
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)
    monkeypatch.setattr(app_module, "_converse_inflight", 0)
    monkeypatch.setattr(app_module, "_converse_window_started_at", 0.0)
    monkeypatch.setattr(
        app_module, "_auditory_pcm_streams", AuditoryPCMStreamRegistry()
    )
    try:
        yield value
    finally:
        value.shutdown()


def _post(
    *,
    stream_id: str,
    sequence: int,
    first_sample_index: int,
    pcm: bytes,
    sight_frames: list[app_module.GLVisualFrameClaim] | None = None,
):
    return asyncio.run(app_module.sound_frame(app_module.GLMessage(
        text=base64.b64encode(pcm).decode("ascii"),
        source="browser_microphone",
        audio_encoding="pcm_s16le",
        audio_stream_id=stream_id,
        audio_sequence=sequence,
        audio_first_sample_index=first_sample_index,
        audio_sample_count=len(pcm) // 2,
        audio_sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        audio_source_epoch_ms=1_000,
        sight_frames=sight_frames,
    )))


def _jpeg_b64() -> str:
    payload = BytesIO()
    Image.new("RGB", (128, 128), color=(30, 90, 170)).save(
        payload, format="JPEG"
    )
    return base64.b64encode(payload.getvalue()).decode("ascii")


def _sight_frames(source_start_ms: int):
    encoded = _jpeg_b64()
    return [
        app_module.GLVisualFrameClaim(
            captured_ms=source_start_ms + offset,
            frame_b64=encoded,
        )
        for offset in (800, 1_600, 2_400, 3_200)
    ]


def test_pcm_chunks_enter_existing_full_field_without_ffmpeg(
    engine: Guala, monkeypatch
) -> None:
    opened = asyncio.run(app_module.auditory_pcm_stream_open())
    stream_id = opened["stream_id"]
    monkeypatch.setattr(
        substrate_runner,
        "_webm_to_wav_bytes",
        lambda _payload: (_ for _ in ()).throw(
            AssertionError("PCM transport invoked ffmpeg")
        ),
    )

    first_pcm = _pcm(offset=0, count=16_000)
    first = _post(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        pcm=first_pcm,
    )
    second_pcm = _pcm(offset=16_000, count=16_000)
    second = _post(
        stream_id=stream_id,
        sequence=1,
        first_sample_index=16_000,
        pcm=second_pcm,
    )

    assert first["ok"] is True
    assert second["ok"] is True
    assert first["pcm_continuity"]["sequence"] == 0
    assert len(first["pcm_continuity"]["causal_settlement_receipt_sha256"]) == 64
    assert second["pcm_continuity"]["sequence"] == 1
    assert second["pcm_continuity"]["first_sample_index"] == 16_000
    assert first["observed_senses"] == ["sound"]
    assert second["observed_senses"] == ["sound"]
    assert engine.auditory_l5_status()["l5_owner"]["settled"] == 2
    assert engine._full_field_prediction.status()["passive_relations"] == 1
    assert engine._latest_full_field_prediction_observation["reason"] == (
        "exact_audiovisual_transition_observed"
    )
    prediction = engine.observation_snapshot()["full_field_prediction"]
    assert prediction["status"] in {"unknown", "predicted", "ambiguous"}
    assert prediction["observer"]["latest_resolution"]["resolution_id"]
    assert prediction["observer"]["latest_resolution"][
        "verification"
    ] == "unknown_observed"


def test_paired_pcm_windows_settle_anonymous_encounter_not_sound_source(
    engine: Guala, monkeypatch,
) -> None:
    stream_id = asyncio.run(app_module.auditory_pcm_stream_open())["stream_id"]
    first = _post(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        pcm=_pcm(offset=0, count=80_000),
        sight_frames=_sight_frames(1_000),
    )
    assert first["ok"] is True
    first_status = engine.auditory_l5_status()["live_anonymous_encounter"]
    assert first_status["state"] == "unknown"
    assert first_status["acoustic_source"] == "unknown"

    second = _post(
        stream_id=stream_id,
        sequence=1,
        first_sample_index=80_000,
        pcm=_pcm(offset=80_000, count=80_000),
        sight_frames=_sight_frames(6_000),
    )
    assert second["ok"] is True
    second_status = engine.auditory_l5_status()[
        "live_anonymous_encounter"
    ]
    assert second_status["state"] == "unknown"
    assert second_status["reason"] == "no_continuing_visual_lineage"
    assert second_status["active"] is True
    assert second_status["acoustic_source"] == "unknown"
    assert second_status["latest"]["assembly_id"] == (
        engine._latest_auditory_stream_settlement_receipt.assembly_id
    )

    discontinuity_payload = _advance_payload(
        status=AuditoryIncrementalStatus.DISCONTINUITY,
        released_terminals=(),
        processed_hops=0,
        active_tracker_count=0,
    )
    discontinuity = AuditoryIncrementalAdvance(
        status=AuditoryIncrementalStatus.DISCONTINUITY,
        released_terminals=(),
        processed_hops=0,
        active_tracker_count=0,
        authority_receipt_sha256=hashlib.sha256(json.dumps(
            discontinuity_payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")).hexdigest(),
    )
    discontinuity.verify()
    monkeypatch.setattr(
        engine._auditory_incremental_terminals,
        "advance",
        lambda **_values: discontinuity,
    )
    third = _post(
        stream_id=stream_id,
        sequence=2,
        first_sample_index=160_000,
        pcm=_pcm(offset=160_000, count=80_000),
        sight_frames=_sight_frames(11_000),
    )
    assert third["ok"] is True
    assert third["pcm_continuity"]["incremental_terminal_status"] == (
        "discontinuity"
    )
    rejected = engine.auditory_l5_status()["live_anonymous_encounter"]
    assert rejected["active"] is False
    assert rejected["state"] == "unknown"

    engine.close_auditory_pcm_stream(stream_id)
    closed = engine.auditory_l5_status()["live_anonymous_encounter"]
    assert closed["active"] is False
    assert closed["state"] == "unknown"


def test_continuity_receipts_are_mounted_into_causal_settlement(
    engine: Guala,
) -> None:
    registry = AuditoryPCMStreamRegistry()
    stream_id = registry.open()["stream_id"]
    pcm = _pcm(offset=0, count=1_600)
    accepted = registry.accept(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=1_000_000_000,
        pcm_s16le=pcm,
    )
    sound = engine.process_sound_frame(
        pcm_s16le_wav(pcm),
        source_anchor_ns=1_000_000_000,
        source_time_end_ns=1_100_000_000,
        auditory_pcm_continuity=accepted.receipt,
        auditory_pcm_s16le=pcm,
    )
    settlement = sound["settlement"]
    l5 = engine._latest_auditory_l5_experience
    cochlear = engine._latest_auditory_continuation_receipt
    mounted = bind_auditory_stream_settlement(
        transport=accepted.receipt,
        cochlear=cochlear,
        auditory_l5=l5,
        causal_settlement=settlement,
    )
    mounted.verify()

    with pytest.raises(ValueError, match="altered"):
        bind_auditory_stream_settlement(
            transport=replace(accepted.receipt, receipt_sha256="0" * 64),
            cochlear=cochlear,
            auditory_l5=l5,
            causal_settlement=settlement,
        )
    with pytest.raises(ValueError, match="altered"):
        bind_auditory_stream_settlement(
            transport=accepted.receipt,
            cochlear=replace(cochlear, receipt_sha256="0" * 64),
            auditory_l5=l5,
            causal_settlement=settlement,
        )


def test_continuous_authorities_survive_an_unrelated_later_sound(
    engine: Guala,
) -> None:
    registry = AuditoryPCMStreamRegistry()
    stream_id = registry.open()["stream_id"]
    pcm = _pcm(offset=0, count=1_600)
    accepted = registry.accept(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=1_000_000_000,
        pcm_s16le=pcm,
    )
    first = engine.process_sound_frame(
        pcm_s16le_wav(pcm),
        source_anchor_ns=1_000_000_000,
        source_time_end_ns=1_100_000_000,
        auditory_pcm_continuity=accepted.receipt,
        auditory_pcm_s16le=pcm,
    )
    engine.process_sound_frame(
        pcm_s16le_wav(_pcm(offset=0, count=1_600)),
        source_anchor_ns=2_000_000_000,
        source_time_end_ns=2_100_000_000,
    )

    joint, terminal = engine.advance_continuous_auditory_terminal(
        pcm_s16le=pcm,
        transport=accepted.receipt,
        settlement=first["settlement"],
    )
    joint.verify()
    terminal.verify()
    assert joint.assembly_id == first["settlement"].assembly_id


def test_duplicate_chunk_fails_closed_and_terminates_stream(engine: Guala) -> None:
    stream_id = asyncio.run(app_module.auditory_pcm_stream_open())["stream_id"]
    pcm = _pcm(offset=0, count=1_600)
    assert _post(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        pcm=pcm,
    )["ok"] is True

    duplicate = _post(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        pcm=pcm,
    )
    assert duplicate["ok"] is False
    assert "discontinuous" in duplicate["error"]
    assert app_module._auditory_pcm_streams.status()["active_streams"] == 0


def test_distinct_stream_epochs_do_not_create_a_prediction_edge(
    engine: Guala,
) -> None:
    first_stream = asyncio.run(
        app_module.auditory_pcm_stream_open()
    )["stream_id"]
    second_stream = asyncio.run(
        app_module.auditory_pcm_stream_open()
    )["stream_id"]
    pcm = _pcm(offset=0, count=16_000)

    assert _post(
        stream_id=first_stream,
        sequence=0,
        first_sample_index=0,
        pcm=pcm,
    )["ok"] is True
    assert _post(
        stream_id=second_stream,
        sequence=0,
        first_sample_index=0,
        pcm=pcm,
    )["ok"] is True

    assert engine._full_field_prediction.status()["passive_relations"] == 0
    assert engine._latest_full_field_prediction_observation["reason"] == (
        "context_rebased_without_relation"
    )


def test_pcm_interval_contains_the_complete_paired_sight_field(
    engine: Guala,
) -> None:
    stream_id = asyncio.run(app_module.auditory_pcm_stream_open())["stream_id"]
    response = _post(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        pcm=_pcm(offset=0, count=80_000),
        sight_frames=_sight_frames(1_000),
    )
    assert response["ok"] is True
    assert response["causal_boundary"] == "audiovisual"
    assert response["observed_senses"] == ["sight", "sound"]
    second = _post(
        stream_id=stream_id,
        sequence=1,
        first_sample_index=80_000,
        pcm=_pcm(offset=80_000, count=80_000),
        sight_frames=_sight_frames(6_000),
    )
    assert second["ok"] is True
    assert second["causal_boundary"] == "audiovisual"
    assert second["observed_senses"] == ["sight", "sound"]
    assert engine._full_field_prediction.status()["passive_relations"] == 1
    relation = engine._full_field_prediction.relation_records()[0]
    context_id = relation["latest_evidence"]["context_episode_id"]
    target_id = relation["latest_evidence"]["target_episode_id"]
    assert context_id != target_id
    assert "sensory_errors" not in response
    assert len(
        response["pcm_continuity"]["causal_settlement_receipt_sha256"]
    ) == 64


def test_rejected_visual_sequence_does_not_close_valid_pcm_continuity(
    engine: Guala,
) -> None:
    stream_id = asyncio.run(app_module.auditory_pcm_stream_open())["stream_id"]
    frames = _sight_frames(1_000)
    frames[2] = app_module.GLVisualFrameClaim(
        captured_ms=frames[1].captured_ms,
        frame_b64=frames[2].frame_b64,
    )
    response = _post(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        pcm=_pcm(offset=0, count=80_000),
        sight_frames=frames,
    )
    assert response["ok"] is True
    assert response["causal_boundary"] == "sound"
    assert response["visual_region"]["status"] == "rejected"
    assert response["pcm_continuity"]["status"] == "contiguous"
    assert asyncio.run(app_module.auditory_pcm_stream_close(
        app_module.AuditoryPCMStreamCloseRequest(stream_id=stream_id)
    ))["ok"] is True


def test_malformed_visual_transport_cannot_preempt_valid_pcm(
    engine: Guala,
) -> None:
    opened = asyncio.run(app_module.auditory_pcm_stream_open())
    stream_id = opened["stream_id"]
    pcm = _pcm(offset=0, count=16_000)
    response = TestClient(app_module.app).post(
        "/sound_frame",
        json={
            "text": base64.b64encode(pcm).decode("ascii"),
            "source": "browser_microphone",
            "audio_encoding": "pcm_s16le",
            "audio_stream_id": stream_id,
            "audio_sequence": 0,
            "audio_first_sample_index": 0,
            "audio_sample_count": 16_000,
            "audio_sample_rate_hz": PCM_SAMPLE_RATE_HZ,
            "audio_source_epoch_ms": 1_000,
            "sight_b64": 7,
            "sight_captured_ms": "not-an-integer",
            "sight_frames": [
                {"captured_ms": "not-an-integer"},
                {},
                3,
                None,
            ],
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["ok"] is True
    assert result["causal_boundary"] == "sound"
    assert result["visual_region"]["status"] == "rejected"
    assert result["pcm_continuity"]["status"] == "contiguous"


def test_continuous_full_field_terminal_opens_one_existing_reply_door(
    engine: Guala, monkeypatch
) -> None:
    learned_pcm = _pcm(offset=0, count=6_400)
    tutor_capture = bytes(3_200 * 2) + learned_pcm + bytes(4_800 * 2)
    engine.teach_isolated_auditory_asset(
        pcm_s16le_wav(tutor_capture), "hello guala"
    )
    replies = []
    monkeypatch.setattr(
        app_module,
        "_maybe_trigger_voice_reply",
        lambda terminal_event, tick: (
            replies.append((terminal_event, tick)) or True
        ),
    )
    stream_id = asyncio.run(app_module.auditory_pcm_stream_open())["stream_id"]
    offset = 21_920
    values = (
        bytes(offset * 2)
        + learned_pcm
        + bytes((80_000 - offset - 6_400) * 2)
    )
    result = _post(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        pcm=values,
    )

    assert result["ok"] is True
    assert result["pcm_continuity"][
        "incremental_terminal_status"
    ] == "released_unique"
    assert result["spoken_word_recognition"]["recognized_form"] == (
        "hello guala"
    )
    assert [value[0].tutor_label for value in replies] == ["hello guala"]
    assert replies[0][0].event_id == result["spoken_word_recognition"][
        "causal_experience_id"
    ]
    assert replies[0][0].as_record()["authority_receipt_sha256"] == (
        replies[0][0].authority_receipt_sha256
    )


def test_pcm_source_interval_is_derived_from_sample_identity() -> None:
    msg = app_module.GLMessage(
        text="AA==",
        audio_encoding="pcm_s16le",
        audio_stream_id="stream",
        audio_sequence=3,
        audio_first_sample_index=48_000,
        audio_sample_count=8_000,
        audio_sample_rate_hz=16_000,
        audio_source_epoch_ms=10_000,
    )
    times = app_module._authoritative_capture_times(msg)
    assert times["source_time_start_ns"] == 13_000_000_000
    assert times["source_time_end_ns"] == 13_500_000_000
