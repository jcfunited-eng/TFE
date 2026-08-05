from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import replace
from pathlib import Path

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.browser_binaural_pcm_stream import (
    BINAURAL_CHANNEL_ORDER,
    BrowserBinauralLineageMode,
    BrowserBinauralPCMStreamRegistry,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodiedBody,
    EmbodimentPort,
    EmbodimentWorldAuthority,
    PoseMM,
    PositionMM,
    VocalizeCommand,
    encode_command,
)
from dsf_ai_service.substrate.live_hearing_authority_integration import (
    LiveHearingAuthorityIntegrator,
    LiveHearingEvidenceRoute,
    audit_live_hearing_sources,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_authenticated_multi_emitter_capture import (
    W1AuthenticatedMultiEmitterCaptureOwner,
)


WORLD_KEY = b"live-integration-world-authority"
EMITTER_KEY = b"live-integration-emitter-authority"
CAPTURE_KEY = b"live-integration-capture-authority"
ROOM_KEY = b"live-integration-room-authority-v1"
LOOM_KEY = b"live-integration-loom-authority-v1"
INTEGRATION_KEY = b"live-integration-view-authority-v1"
EPOCH = "live-integration-room-interval"
SAMPLES = 960
LEFT_PORT = "integration.external.left"
RIGHT_PORT = "integration.external.right"


def _pcm(frequency: int, amplitude: int = 4_000) -> bytes:
    values = tuple(
        int(
            amplitude
            * math.sin(2 * math.pi * frequency * index / 16_000)
        )
        for index in range(SAMPLES)
    )
    return struct.pack(f"<{SAMPLES}h", *values)


def _integrator() -> LiveHearingAuthorityIntegrator:
    return LiveHearingAuthorityIntegrator(
        authority_key=INTEGRATION_KEY,
        room_authority_key=ROOM_KEY,
        w1_capture_authority_key=CAPTURE_KEY,
        loom_authority_key=LOOM_KEY,
    )


def _capture():
    world = EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        bodies=(
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                250,
                800,
            ),
            EmbodiedBody(
                "left-source",
                PoseMM(PositionMM(1_000, 1_500, 0), 180_000),
                100,
                300,
            ),
            EmbodiedBody(
                "right-source",
                PoseMM(PositionMM(1_000, 500, 0), 180_000),
                100,
                300,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(LEFT_PORT, "left-source"),
            EmbodimentPort(RIGHT_PORT, "right-source"),
        ),
    )
    emitter = W1AcousticEmitterAuthority(
        authority_key=EMITTER_KEY,
        world_authority=world,
    )
    owner = W1AuthenticatedMultiEmitterCaptureOwner(
        authority_key=CAPTURE_KEY,
        world_authority=world,
        acoustic_emitter=emitter,
    )
    owner.open(
        epoch_token=EPOCH,
        source_sample_start=0,
        source_sample_count=SAMPLES,
    )
    for sequence, port, pcm in (
        (0, LEFT_PORT, _pcm(440)),
        (1, RIGHT_PORT, _pcm(730)),
    ):
        command = VocalizeCommand(
            epoch_commitment_sha256=hashlib.sha256(
                EPOCH.encode("utf-8")
            ).hexdigest(),
            sequence=sequence,
            source_sample_start=0,
            pcm_sha256=hashlib.sha256(pcm).hexdigest(),
            sample_count=SAMPLES,
        )
        payload = encode_command(command)
        execution = world.execute_port_command(
            port_id=port,
            command_payload=payload,
            causal_intent_receipt_sha256=f"{sequence + 1:x}" * 64,
            expected_revision=world.observation_snapshot().revision,
        )
        observation = world.observation_snapshot()
        emission = emitter.emit(
            epoch_token=EPOCH,
            sequence=sequence,
            source_sample_start=0,
            observation_snapshot=observation,
            execution_receipt=execution,
            command_payload=payload,
            emitter_port_id=port,
            pcm_s16le=pcm,
        )
        owner.admit(
            emission=emission,
            observation_snapshot=observation,
            execution_receipt=execution,
        )
    return owner.close()


def _browser_chunk():
    registry = BrowserBinauralPCMStreamRegistry()
    opened = registry.open()
    lineage = registry.register_lineage(
        stream_id=opened["stream_id"],
        capture_session_sha256="1" * 64,
        worklet_source_sha256="2" * 64,
        media_track_settings_sha256="3" * 64,
        mode=BrowserBinauralLineageMode.DISCRETE_SOURCE_CHANNELS,
        media_track_channel_count=2,
        worklet_input_channel_count=2,
        channel_order=BINAURAL_CHANNEL_ORDER,
    )
    return registry.accept(
        stream_id=opened["stream_id"],
        lineage_receipt_sha256=lineage.receipt_sha256,
        sequence=0,
        first_sample_index=0,
        render_frame_start=48_000,
        sample_rate_hz=16_000,
        source_epoch_start_ns=8_000_000_000,
        left_pcm_s16le=_pcm(440),
        right_pcm_s16le=_pcm(730),
    )


def test_current_production_source_audit_reports_exact_unwired_boundary():
    root = Path(__file__).resolve().parents[1]
    audit = audit_live_hearing_sources(
        app_source=(root / "dsf_ai_service/app.py").read_text(),
        browser_source=(
            root / "dsf_ai_service/static/gualaloom.html"
        ).read_text(),
        engine_source=(
            root / "dsf_ai_service/v4/gualaloom_v5_engine.py"
        ).read_text(),
    )

    assert audit.browser_channel_average_present is False
    assert audit.app_mono_pcm_registry_present is True
    assert audit.app_binaural_pcm_registry_present is True
    assert audit.app_exact_room_coordinator_present is False
    assert audit.engine_recurrent_q_authority_present is True
    assert audit.engine_exact_room_coordinator_present is False
    assert audit.exact_room_hearing_source_cutover_present is False
    assert audit.live_runtime_receipt_observed is False
    audit.verify()


def test_authenticated_w1_room_exposes_two_complete_fields_but_not_live_cutover():
    view = _integrator().hear_authenticated_w1_room(_capture())

    assert view.route is LiveHearingEvidenceRoute.AUTHENTICATED_W1_ROOM
    assert view.room_hearing_authority is True
    assert len(view.full_field_occurrence_receipt_sha256s) == 2
    assert view.production_live_wired is False
    assert view.cognition_authority is False
    assert view.meaning_authority is False
    assert view.loom_projection.cognition["status"] == "not_observed"
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for occurrence in view.room_outcome.occurrences
        for channel in occurrence.separated_field.auditory_l5.channels
        for component in (
            channel.pressure,
            channel.carrier_phase_advance,
        )
        for field_tuple in component.l4_field_tuples
    )
    view.verify(
        authority_key=INTEGRATION_KEY,
        room_authority_key=ROOM_KEY,
        loom_authority_key=LOOM_KEY,
    )


def test_unproven_browser_binaural_releases_no_room_authority():
    chunk = _browser_chunk()
    view = _integrator().hear_browser_binaural(chunk)

    assert view.route is (
        LiveHearingEvidenceRoute.BROWSER_BINAURAL_UNPROVEN
    )
    assert view.room_hearing_authority is False
    assert view.full_field_occurrence_receipt_sha256s == ()
    assert view.production_live_wired is False
    assert view.loom_projection.binaural_transport == {
        "cognition_admitted": False,
        "hardware_authority_proven": False,
        "status": "discrete_transport_hardware_unproven",
        "transport_receipt_sha256": chunk.receipt.receipt_sha256,
    }
    view.verify(
        authority_key=INTEGRATION_KEY,
        room_authority_key=ROOM_KEY,
        loom_authority_key=LOOM_KEY,
    )


def test_mono_pressure_releases_no_room_authority():
    view = _integrator().hear_mono(_pcm(440))

    assert view.route is LiveHearingEvidenceRoute.MONO_PRESSURE
    assert view.room_hearing_authority is False
    assert view.full_field_occurrence_receipt_sha256s == ()
    assert view.cognition_authority is False
    assert view.meaning_authority is False


def test_integration_receipt_rejects_fabricated_live_cutover():
    view = _integrator().hear_mono(_pcm(440))
    changed = replace(view, production_live_wired=True)

    with pytest.raises(
        ValueError,
        match="live hearing integration authority changed",
    ):
        changed.verify(
            authority_key=INTEGRATION_KEY,
            room_authority_key=ROOM_KEY,
            loom_authority_key=LOOM_KEY,
        )
