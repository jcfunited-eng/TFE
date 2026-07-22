from __future__ import annotations

import asyncio
import base64
from dataclasses import replace
import math
import struct
from io import BytesIO

import pytest
from PIL import Image

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
    sight_b64: str | None = None,
    sight_captured_ms: int | None = None,
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
        sight_b64=sight_b64,
        sight_captured_ms=sight_captured_ms,
    )))


def _jpeg_b64() -> str:
    payload = BytesIO()
    Image.new("RGB", (128, 128), color=(30, 90, 170)).save(
        payload, format="JPEG"
    )
    return base64.b64encode(payload.getvalue()).decode("ascii")


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


def test_pcm_interval_contains_the_complete_paired_sight_field(
    engine: Guala,
) -> None:
    stream_id = asyncio.run(app_module.auditory_pcm_stream_open())["stream_id"]
    response = _post(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        pcm=_pcm(offset=0, count=80_000),
        sight_b64=_jpeg_b64(),
        sight_captured_ms=1_000,
    )
    assert response["ok"] is True
    assert response["causal_boundary"] == "audiovisual"
    assert response["observed_senses"] == ["sight", "sound"]
    assert "sensory_errors" not in response
    assert len(
        response["pcm_continuity"]["causal_settlement_receipt_sha256"]
    ) == 64


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
    times = app_module._authoritative_capture_times(msg, paired_sight=False)
    assert times["source_time_start_ns"] == 13_000_000_000
    assert times["source_time_end_ns"] == 13_500_000_000
