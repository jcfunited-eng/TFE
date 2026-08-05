from __future__ import annotations

import asyncio
import base64
import math
import struct

import dsf_ai_service.app as app_module
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala


def _pcm(sample_count: int = 1_600) -> bytes:
    values = tuple(
        int(8_000 * math.sin(2 * math.pi * 440 * index / 16_000))
        for index in range(sample_count)
    )
    return struct.pack(f"<{len(values)}h", *values)


def test_unified_runtime_mounts_complete_pcm_transaction(monkeypatch) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "unified-auditory-transaction-mount-test-key-v1",
    )
    engine = Guala()
    registry = AuditoryPCMStreamRegistry()
    monkeypatch.setattr(app_module, "_guala", engine)
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)
    monkeypatch.setattr(app_module, "_auditory_pcm_streams", registry)
    try:
        stream_id = registry.open()["stream_id"]
        pcm = _pcm()
        response = asyncio.run(app_module.sound_frame(app_module.GLMessage(
            text=base64.b64encode(pcm).decode("ascii"),
            source="browser_microphone",
            audio_encoding="pcm_s16le",
            audio_stream_id=stream_id,
            audio_sequence=0,
            audio_first_sample_index=0,
            audio_sample_count=len(pcm) // 2,
            audio_sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            audio_source_epoch_ms=1_000,
        )))

        assert response["ok"] is True
        assert response["observed_senses"] == ["sound"]
        assert response["pcm_continuity"]["status"] == "contiguous"
        assert engine.auditory_l5_status()["l5_owner"]["settled"] == 1
        assert not engine._auditory_capture_authorities
        assert not engine._auditory_l5_by_assembly
        assert not engine._auditory_prediction_joint_by_transport
        assert not engine._auditory_verified_capability_by_transport
    finally:
        engine.shutdown()
