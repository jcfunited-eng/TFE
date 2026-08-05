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


def test_browser_worklet_has_no_average_duplication_or_mono_fallback():
    page = Path(
        "dsf_ai_service/static/gualaloom.html"
    ).read_text(encoding="utf-8")

    assert "sample/=channels.length;" not in page
    assert "(channels.length!==1&&channels.length!==2)" in page
    assert "settings.channelCount!==2||inputChannelCount!==2" in page
    assert "leftBuffer:new" not in page
    assert "this.leftBuffer=new ArrayBuffer" in page
    assert "this.rightBuffer=new ArrayBuffer" in page
    assert "left_pcm_b64:_pcmBase64(leftBuffer)" in page
    assert "right_pcm_b64:_pcmBase64(rightBuffer)" in page
    assert "channelCount:{ideal:2}" in page
    assert "audio_channel_mode:channelProjection?" in page
    assert "'discrete_left_projection':'single_runtime_channel'" in page
    assert "fetchT(`${API}/sound_frame`" in page
    assert "audio_stream_id:epoch.monoStreamId" in page
    assert "binaural_hardware_authority_proven!==false" in page
    assert "physical ear authority unproven" in page
    assert "single captured channel hearing active" in page


def test_worklet_preserves_stereo_and_keeps_single_channel_hearing():
    page = Path(
        "dsf_ai_service/static/gualaloom.html"
    ).read_text(encoding="utf-8")
    start = page.index("  const workletSource=`") + len(
        "  const workletSource=`"
    )
    end = page.index("\n  `;", start)
    worklet = page[start:end]
    program = f"""
      let Registered=null,currentFrame=0;
      class AudioWorkletProcessor {{
        constructor() {{
          this.port={{
            messages:[],
            postMessage:(value)=>this.port.messages.push(value),
            onmessage:null
          }};
        }}
      }}
      function registerProcessor(_name,value){{Registered=value}}
      {worklet}
      function run(channelCount){{
        currentFrame=0;
        const value=new Registered({{processorOptions:{{chunkSamples:32000}}}});
        const blockLength=128;
        const channels=[];
        for(let channel=0;channel<channelCount;channel++){{
          const samples=new Float32Array(blockLength);
          samples.fill(channel===0?0.25:-0.5);
          channels.push(samples);
        }}
        value.process([channels]);currentFrame+=blockLength;
        for(let block=0;block<250;block++){{
          value.process([channels]);currentFrame+=blockLength;
        }}
        const chunk=value.port.messages.find(item=>item.type==='chunk');
        if(!chunk)throw new Error('worklet emitted no bounded chunk');
        return {{
          inputChannelCount:value.inputChannelCount,
          rightIsNull:chunk.rightBuffer===null,
          leftFirst:new DataView(chunk.leftBuffer).getInt16(0,true),
          rightFirst:chunk.rightBuffer===null?null:
            new DataView(chunk.rightBuffer).getInt16(0,true)
        }};
      }}
      process.stdout.write(JSON.stringify({{mono:run(1),stereo:run(2)}}));
    """
    completed = subprocess.run(
        ["node", "-e", program],
        check=True,
        capture_output=True,
        text=True,
    )
    value = json.loads(completed.stdout)

    assert value["mono"] == {
        "inputChannelCount": 1,
        "rightIsNull": True,
        "leftFirst": 8192,
        "rightFirst": None,
    }
    assert value["stereo"] == {
        "inputChannelCount": 2,
        "rightIsNull": False,
        "leftFirst": 8192,
        "rightFirst": -16384,
    }
