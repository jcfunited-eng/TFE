from __future__ import annotations

import asyncio
import base64
import json
import math
import struct
import subprocess
from pathlib import Path

import pytest
from fastapi.responses import JSONResponse

import dsf_ai_service.app as app_module
from dsf_ai_service.substrate.browser_binaural_pcm_stream import (
    BrowserBinauralPCMStreamRegistry,
)
from dsf_ai_service.substrate.browser_discrete_channel_projection import (
    BrowserDiscreteChannelProjectionOwner,
)
from dsf_ai_service.substrate.live_hearing_authority_integration import (
    LiveHearingAuthorityIntegrator,
)


SAMPLE_RATE = 16_000
SAMPLES = 320


def _pcm(frequency: int) -> bytes:
    values = tuple(
        round(
            4_000
            * math.sin(2 * math.pi * frequency * index / SAMPLE_RATE)
        )
        for index in range(SAMPLES)
    )
    return struct.pack(f"<{SAMPLES}h", *values)


def _response(value):
    if isinstance(value, JSONResponse):
        return value.status_code, json.loads(value.body)
    return 200, value


@pytest.fixture(autouse=True)
def isolated_browser_binaural_runtime(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "_browser_binaural_pcm_streams",
        BrowserBinauralPCMStreamRegistry(),
    )
    monkeypatch.setattr(
        app_module,
        "_live_hearing_browser_integrator",
        LiveHearingAuthorityIntegrator(
            authority_key=b"http-binaural-integration-authority",
            room_authority_key=b"http-binaural-room-authority-v11",
            w1_capture_authority_key=(
                b"http-binaural-w1-capture-authority"
            ),
            loom_authority_key=b"http-binaural-loom-authority-v11",
        ),
    )
    monkeypatch.setattr(
        app_module,
        "_browser_discrete_channel_projection_owner",
        BrowserDiscreteChannelProjectionOwner(
            b"http-discrete-channel-projection-authority"
        ),
    )


def _open_and_register(
    *,
    media_track_channels: int = 2,
    worklet_input_channels: int = 2,
):
    opened = asyncio.run(
        app_module.browser_binaural_pcm_stream_open()
    )
    request = app_module.BrowserBinauralLineageRequest(
        stream_id=opened["stream_id"],
        capture_session_sha256="1" * 64,
        worklet_source_sha256="2" * 64,
        media_track_settings_sha256="3" * 64,
        mode="discrete_source_channels",
        media_track_channel_count=media_track_channels,
        worklet_input_channel_count=worklet_input_channels,
        channel_order=["left", "right"],
    )
    lineage = asyncio.run(
        app_module.browser_binaural_pcm_stream_lineage(request)
    )
    return opened, lineage


def _chunk(
    *,
    stream_id: str,
    lineage_receipt_sha256: str,
    sequence: int = 0,
    first_sample_index: int = 0,
    render_frame_start: int = 48_000,
):
    request = app_module.BrowserBinauralChunkRequest(
        stream_id=stream_id,
        target_mono_stream_id="mono-stream",
        lineage_receipt_sha256=lineage_receipt_sha256,
        sequence=sequence,
        first_sample_index=first_sample_index,
        render_frame_start=render_frame_start,
        sample_rate_hz=SAMPLE_RATE,
        source_epoch_start_ns=8_000_000_000,
        left_pcm_b64=base64.b64encode(_pcm(440)).decode("ascii"),
        right_pcm_b64=base64.b64encode(_pcm(730)).decode("ascii"),
    )
    return asyncio.run(
        app_module.browser_binaural_pcm_stream_chunk(request)
    )


def test_http_transport_preserves_two_channels_but_refuses_ear_authority():
    opened, lineage = _open_and_register()
    status, lineage_value = _response(lineage)

    assert status == 200
    assert opened["channel_order"] == ["left", "right"]
    assert opened["binaural_hardware_authority_proven"] is False
    assert lineage_value["binaural_hardware_authority_proven"] is False
    result = _chunk(
        stream_id=opened["stream_id"],
        lineage_receipt_sha256=(
            lineage_value["lineage_receipt_sha256"]
        ),
    )
    status, value = _response(result)

    assert status == 200
    assert value["continuity"]["status"] == "contiguous"
    assert value["continuity"]["sample_count"] == SAMPLES
    assert value["binaural_hardware_authority_proven"] is False
    assert value["room_hearing"]["state"] == (
        "refused_unproven_browser_hardware"
    )
    assert value["room_hearing"]["authority"] is False
    assert value["room_hearing"][
        "full_field_occurrence_receipt_sha256s"
    ] == []
    assert value["production_exact_room_hearing_wired"] is False
    assert value["cognition_authority"] is False
    assert value["meaning_authority"] is False
    assert len(value["integration_receipt_sha256"]) == 64
    projection = value["left_channel_projection"]
    assert projection["channel"] == "left"
    assert projection["binaural_hardware_authority_proven"] is False
    assert projection["room_hearing_authority"] is False

    mono_message = app_module.GLMessage(
        text=base64.b64encode(_pcm(440)).decode("ascii"),
        source="browser_microphone",
        audio_encoding="pcm_s16le",
        audio_stream_id="mono-stream",
        audio_sequence=0,
        audio_first_sample_index=0,
        audio_sample_count=SAMPLES,
        audio_sample_rate_hz=SAMPLE_RATE,
        audio_source_epoch_ms=1_000,
        audio_channel_mode="discrete_left_projection",
        audio_channel_projection=projection,
    )
    verified = app_module._verify_browser_channel_projection(
        mono_message,
        _pcm(440),
    )
    assert verified is not None
    assert verified.authority_receipt_sha256 == (
        projection["authority_receipt_sha256"]
    )
    with pytest.raises(
        ValueError,
        match="mono hearing bytes left their discrete channel",
    ):
        app_module._verify_browser_channel_projection(
            mono_message,
            _pcm(730),
        )
    replay_target = mono_message.model_copy(
        update={"audio_stream_id": "different-mono-stream"}
    )
    with pytest.raises(
        ValueError,
        match="mono hearing left its parent channel interval",
    ):
        app_module._verify_browser_channel_projection(
            replay_target,
            _pcm(440),
        )


def test_requested_two_channels_cannot_replace_runtime_channel_evidence():
    opened, lineage = _open_and_register(worklet_input_channels=1)
    status, value = _response(lineage)

    assert status == 400
    assert value["ok"] is False
    assert "cannot become binaural authority" in value["error"]
    assert (
        app_module._browser_binaural_pcm_streams.status()[
            "active_streams"
        ]
        == 0
    )


def test_shared_render_clock_discontinuity_closes_the_epoch():
    opened, lineage = _open_and_register()
    _, lineage_value = _response(lineage)
    first = _chunk(
        stream_id=opened["stream_id"],
        lineage_receipt_sha256=(
            lineage_value["lineage_receipt_sha256"]
        ),
    )
    assert _response(first)[0] == 200

    changed = _chunk(
        stream_id=opened["stream_id"],
        lineage_receipt_sha256=(
            lineage_value["lineage_receipt_sha256"]
        ),
        sequence=1,
        first_sample_index=SAMPLES,
        render_frame_start=48_000 + SAMPLES + 1,
    )
    status, value = _response(changed)

    assert status == 400
    assert "render clock is discontinuous" in value["error"]
    assert (
        app_module._browser_binaural_pcm_streams.status()[
            "active_streams"
        ]
        == 0
    )


