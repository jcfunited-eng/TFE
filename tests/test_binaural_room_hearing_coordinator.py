from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.binaural_room_hearing_coordinator import (
    BinauralRoomHearingCoordinator,
    BinauralRoomHearingState,
)
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
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_authenticated_multi_emitter_capture import (
    W1AuthenticatedMultiEmitterCaptureOwner,
)


WORLD_KEY = b"room-coordinator-world-authority"
EMITTER_KEY = b"room-coordinator-emitter-authority"
CAPTURE_KEY = b"room-coordinator-capture-authority"
COORDINATOR_KEY = b"room-coordinator-hearing-authority"
EPOCH = "room-coordinator-concurrent-interval"
SAMPLES = 960
LEFT_PORT = "room.external.left"
RIGHT_PORT = "room.external.right"


def _pcm(frequency: int, amplitude: int = 4_000) -> bytes:
    values = tuple(
        int(
            amplitude
            * math.sin(2 * math.pi * frequency * index / 16_000)
        )
        for index in range(SAMPLES)
    )
    return struct.pack(f"<{SAMPLES}h", *values)


def _world() -> EmbodimentWorldAuthority:
    return EmbodimentWorldAuthority(
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


def _capture(first: bytes, second: bytes):
    world = _world()
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
        (0, LEFT_PORT, first),
        (1, RIGHT_PORT, second),
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


def _coordinator() -> BinauralRoomHearingCoordinator:
    return BinauralRoomHearingCoordinator(
        authority_key=COORDINATOR_KEY,
        w1_capture_authority_key=CAPTURE_KEY,
    )


def test_authenticated_w1_capture_yields_two_verified_full_field_occurrences():
    coordinator = _coordinator()
    capture = _capture(_pcm(440), _pcm(730))

    outcome = coordinator.hear_authenticated_w1_capture(capture)

    assert outcome.state is (
        BinauralRoomHearingState.SEPARATED_OCCURRENCES
    )
    assert outcome.mixture_auditory_l5 is not None
    assert len(outcome.occurrences) == 2
    assert tuple(value.source_ordinal for value in outcome.occurrences) == (
        0,
        1,
    )
    outcome.verify(COORDINATOR_KEY)
    for occurrence in outcome.occurrences:
        occurrence.verify(COORDINATOR_KEY)
        assert all(
            tuple(name for name, _field in field_tuple.fields)
            == DSF_FIELD_ORDER
            for channel in occurrence.separated_field.auditory_l5.channels
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            )
            for field_tuple in component.l4_field_tuples
        )
    assert coordinator.status()["separated"] == 1
    assert coordinator.status()["retained_raw_media_bytes"] == 0


def test_unproven_discrete_browser_transport_releases_no_cognition():
    coordinator = _coordinator()

    outcome = coordinator.hear_browser_transport(_browser_chunk())

    assert outcome.state is (
        BinauralRoomHearingState
        .REFUSED_UNPROVEN_BROWSER_HARDWARE
    )
    assert outcome.mixture_auditory_l5 is None
    assert outcome.separation_receipt_sha256 is None
    assert outcome.occurrences == ()
    outcome.verify(COORDINATOR_KEY)


def test_mono_pressure_is_refused_without_duplication():
    coordinator = _coordinator()

    outcome = coordinator.hear_mono_pcm(_pcm(440))

    assert outcome.state is BinauralRoomHearingState.REFUSED_MONO
    assert outcome.occurrences == ()
    assert outcome.evidence_kind == "mono_pressure"
    outcome.verify(COORDINATOR_KEY)


def test_unknown_paths_and_blind_separation_are_distinct_refusals():
    coordinator = _coordinator()
    left = _pcm(440)
    right = _pcm(730)

    unknown = coordinator.hear_unattributed_binaural_pcm(
        left_pcm_s16le=left,
        right_pcm_s16le=right,
        request_blind_separation=False,
    )
    blind = coordinator.hear_unattributed_binaural_pcm(
        left_pcm_s16le=left,
        right_pcm_s16le=right,
        request_blind_separation=True,
    )

    assert unknown.state is (
        BinauralRoomHearingState.REFUSED_UNKNOWN_PATHS
    )
    assert blind.state is (
        BinauralRoomHearingState.REFUSED_BLIND_SEPARATION
    )
    assert unknown.occurrences == blind.occurrences == ()
    unknown.verify(COORDINATOR_KEY)
    blind.verify(COORDINATOR_KEY)


def test_indeterminate_authenticated_pressure_releases_no_occurrence():
    coordinator = _coordinator()
    overloaded = struct.pack(
        f"<{SAMPLES}h",
        *((20_000,) * SAMPLES),
    )
    capture = _capture(overloaded, overloaded)

    outcome = coordinator.hear_authenticated_w1_capture(capture)

    assert outcome.state is (
        BinauralRoomHearingState
        .INDETERMINATE_PHYSICAL_SEPARATION
    )
    assert outcome.occurrences == ()
    assert outcome.mixture_auditory_l5 is None
    outcome.verify(COORDINATOR_KEY)


def test_outcome_authority_rejects_occurrence_removal():
    coordinator = _coordinator()
    outcome = coordinator.hear_authenticated_w1_capture(
        _capture(_pcm(440), _pcm(730))
    )
    changed = replace(
        outcome,
        occurrences=outcome.occurrences[:1],
    )

    with pytest.raises(
        ValueError,
        match="successful binaural room hearing is incomplete",
    ):
        changed.verify(COORDINATOR_KEY)
