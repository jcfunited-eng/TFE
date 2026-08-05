from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
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
    MAX_MULTI_EMITTER_RETAINED_RAW_BYTES,
    W1AuthenticatedMultiEmitterCaptureOwner,
    W1MultiEmitterCaptureState,
    mount_authenticated_multi_emitter_binaural_hearing,
    mount_authenticated_multi_emitter_binaural_l5,
    separate_authenticated_multi_emitter_capture,
)
from dsf_ai_service.substrate.w1_exact_binaural_source_separation import (
    ExactBinauralSeparationState,
    mount_exact_separated_auditory_fields,
)


WORLD_KEY = b"multi-emitter-world-authority-key"
EMITTER_KEY = b"multi-emitter-acoustic-authority-key"
CAPTURE_KEY = b"multi-emitter-capture-authority-key"
EPOCH_TOKEN = "w1-concurrent-acoustic-interval"
SOURCE_SAMPLE_COUNT = 960
FIRST_PORT = "w1.external-emitter.left"
SECOND_PORT = "w1.external-emitter.right"


def _world() -> EmbodimentWorldAuthority:
    return EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        bodies=(
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                radius_mm=250,
                reach_mm=800,
            ),
            EmbodiedBody(
                "external-left",
                PoseMM(PositionMM(1_000, 1_500, 0), 180_000),
                radius_mm=100,
                reach_mm=300,
            ),
            EmbodiedBody(
                "external-right",
                PoseMM(PositionMM(1_000, 500, 0), 180_000),
                radius_mm=100,
                reach_mm=300,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(FIRST_PORT, "external-left"),
            EmbodimentPort(SECOND_PORT, "external-right"),
        ),
    )


def _tone(frequency_hz: int, amplitude: int = 4_000) -> bytes:
    values = tuple(
        int(
            amplitude * math.sin(
                2 * math.pi * frequency_hz * index / 16_000
            )
        )
        for index in range(SOURCE_SAMPLE_COUNT)
    )
    return struct.pack(f"<{SOURCE_SAMPLE_COUNT}h", *values)


def _constant(value: int) -> bytes:
    return struct.pack(
        f"<{SOURCE_SAMPLE_COUNT}h",
        *((value,) * SOURCE_SAMPLE_COUNT),
    )


def _execute_emission(
    *,
    world: EmbodimentWorldAuthority,
    emitter: W1AcousticEmitterAuthority,
    port_id: str,
    pcm_s16le: bytes,
    sequence: int,
    epoch_token: str = EPOCH_TOKEN,
):
    command = VocalizeCommand(
        epoch_commitment_sha256=hashlib.sha256(
            epoch_token.encode("utf-8")
        ).hexdigest(),
        sequence=sequence,
        source_sample_start=0,
        pcm_sha256=hashlib.sha256(pcm_s16le).hexdigest(),
        sample_count=SOURCE_SAMPLE_COUNT,
    )
    payload = encode_command(command)
    before = world.observation_snapshot()
    execution = world.execute_port_command(
        port_id=port_id,
        command_payload=payload,
        causal_intent_receipt_sha256=f"{sequence + 1:x}" * 64,
        expected_revision=before.revision,
    )
    after = world.observation_snapshot()
    emission = emitter.emit(
        epoch_token=epoch_token,
        sequence=sequence,
        source_sample_start=0,
        observation_snapshot=after,
        execution_receipt=execution,
        command_payload=payload,
        emitter_port_id=port_id,
        pcm_s16le=pcm_s16le,
    )
    return emission, after, execution


def _captured(
    first_pcm: bytes,
    second_pcm: bytes,
):
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
        epoch_token=EPOCH_TOKEN,
        source_sample_start=0,
        source_sample_count=SOURCE_SAMPLE_COUNT,
    )
    first = _execute_emission(
        world=world,
        emitter=emitter,
        port_id=FIRST_PORT,
        pcm_s16le=first_pcm,
        sequence=0,
    )
    owner.admit(
        emission=first[0],
        observation_snapshot=first[1],
        execution_receipt=first[2],
    )
    second = _execute_emission(
        world=world,
        emitter=emitter,
        port_id=SECOND_PORT,
        pcm_s16le=second_pcm,
        sequence=1,
    )
    owner.admit(
        emission=second[0],
        observation_snapshot=second[1],
        execution_receipt=second[2],
    )
    return owner, owner.close()


def test_two_authenticated_emitters_mix_separate_and_mount_complete_fields():
    first_pcm = _tone(440)
    second_pcm = _tone(730)
    owner, capture = _captured(first_pcm, second_pcm)

    assert capture.state is W1MultiEmitterCaptureState.CAPTURED
    assert capture.capture_sample_count > SOURCE_SAMPLE_COUNT
    assert capture.paths[0] != capture.paths[1]
    assert not hasattr(capture, "emitter_port_ids")
    capture.verify(CAPTURE_KEY)
    persistence = capture.persistence_record(CAPTURE_KEY)
    assert "pcm_s16le" not in str(persistence)
    assert owner.status()["retained_raw_media_bytes"] == 0
    assert owner.status()["captured"] == 1

    mixture_field = mount_authenticated_multi_emitter_binaural_l5(
        capture,
        authority_key=CAPTURE_KEY,
    )
    mixture_field.verify()
    assert mixture_field.source_time_start == Fraction(0)
    assert mixture_field.source_time_end == Fraction(7, 100)
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for ear in mixture_field.ears
        for channel in ear.channels
        for component in (
            channel.pressure,
            channel.carrier_phase_advance,
        )
        for field_tuple in component.field_tuples
    )

    separation = separate_authenticated_multi_emitter_capture(
        capture,
        authority_key=CAPTURE_KEY,
    )
    assert separation.state is ExactBinauralSeparationState.SEPARATED
    assert {
        hashlib.sha256(value).hexdigest()
        for value in separation.separated_pcm_s16le
    } == {
        hashlib.sha256(first_pcm).hexdigest(),
        hashlib.sha256(second_pcm).hexdigest(),
    }
    separated_fields = mount_exact_separated_auditory_fields(
        separation,
        source_time_start=Fraction(0),
    )
    assert len(separated_fields) == 2
    for value in separated_fields:
        value.verify()


def test_multi_emitter_hearing_retains_ordered_typed_ear_receptors() -> None:
    _owner, capture = _captured(_tone(440), _tone(730))
    hearing = mount_authenticated_multi_emitter_binaural_hearing(
        capture,
        authority_key=CAPTURE_KEY,
    )
    hearing.verify()
    assert tuple(value.ear_id for value in hearing.ears) == (
        "left",
        "right",
    )
    assert all(
        value.event.auditory_l5_authority_receipt_sha256
        == hearing.upstream_w1_l5.authority_receipt_sha256
        for value in hearing.ears
    )
    assert all(
        value.experience.source_event_receipt_sha256
        == value.event.authority_receipt_sha256
        for value in hearing.ears
    )
    assert (
        hearing.ears[0].source_pcm_sha256
        != hearing.ears[1].source_pcm_sha256
    )


def test_control_execution_order_cannot_change_perceptual_structure():
    first_pcm = _tone(440)
    second_pcm = _tone(730)
    _owner, forward = _captured(first_pcm, second_pcm)

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
        epoch_token=EPOCH_TOKEN,
        source_sample_start=0,
        source_sample_count=SOURCE_SAMPLE_COUNT,
    )
    for sequence, port_id, pcm in (
        (0, SECOND_PORT, second_pcm),
        (1, FIRST_PORT, first_pcm),
    ):
        emission, observation, execution = _execute_emission(
            world=world,
            emitter=emitter,
            port_id=port_id,
            pcm_s16le=pcm,
            sequence=sequence,
        )
        owner.admit(
            emission=emission,
            observation_snapshot=observation,
            execution_receipt=execution,
        )
    reverse = owner.close()

    assert reverse.structural_fingerprint == (
        forward.structural_fingerprint
    )
    assert reverse.capture_id == forward.capture_id
    assert reverse.left_pcm_s16le == forward.left_pcm_s16le
    assert reverse.right_pcm_s16le == forward.right_pcm_s16le
    assert reverse.authority_receipt_sha256 != (
        forward.authority_receipt_sha256
    )


def test_each_emission_is_verified_while_current_and_raw_state_is_bounded():
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
        epoch_token=EPOCH_TOKEN,
        source_sample_start=0,
        source_sample_count=SOURCE_SAMPLE_COUNT,
    )
    emission, observation, execution = _execute_emission(
        world=world,
        emitter=emitter,
        port_id=FIRST_PORT,
        pcm_s16le=_tone(440),
        sequence=0,
    )
    owner.admit(
        emission=emission,
        observation_snapshot=observation,
        execution_receipt=execution,
    )

    status = owner.status()
    assert status["admitted_causes"] == 1
    assert status["retained_raw_media_bytes"] == SOURCE_SAMPLE_COUNT * 2
    assert (
        status["retained_raw_media_bytes"]
        <= MAX_MULTI_EMITTER_RETAINED_RAW_BYTES
    )
    assert owner.abort()
    assert owner.status()["retained_raw_media_bytes"] == 0


def test_wrong_epoch_emission_is_rejected_without_capture_mutation():
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
        epoch_token=EPOCH_TOKEN,
        source_sample_start=0,
        source_sample_count=SOURCE_SAMPLE_COUNT,
    )
    emission, observation, execution = _execute_emission(
        world=world,
        emitter=emitter,
        port_id=FIRST_PORT,
        pcm_s16le=_tone(440),
        sequence=0,
        epoch_token="another-physical-interval",
    )

    with pytest.raises(
        ValueError,
        match="shared source interval",
    ):
        owner.admit(
            emission=emission,
            observation_snapshot=observation,
            execution_receipt=execution,
        )

    assert owner.status()["admitted_causes"] == 0
    assert owner.status()["retained_raw_media_bytes"] == 0


def test_pressure_overflow_is_typed_and_releases_no_mixture():
    owner, capture = _captured(
        _constant(20_000),
        _constant(20_000),
    )

    assert capture.state is (
        W1MultiEmitterCaptureState
        .INDETERMINATE_PRESSURE_RANGE
    )
    assert capture.left_pcm_s16le == b""
    assert capture.right_pcm_s16le == b""
    assert owner.status()["indeterminate"] == 1
    assert owner.status()["retained_raw_media_bytes"] == 0
    capture.verify(CAPTURE_KEY)
    with pytest.raises(
        ValueError,
        match="cannot be separated",
    ):
        separate_authenticated_multi_emitter_capture(
            capture,
            authority_key=CAPTURE_KEY,
        )


def test_capture_authority_rejects_altered_binaural_pressure():
    _owner, capture = _captured(
        _tone(440),
        _tone(730),
    )
    samples = list(struct.unpack(
        f"<{capture.capture_sample_count}h",
        capture.left_pcm_s16le,
    ))
    samples[100] += 1
    changed = replace(
        capture,
        left_pcm_s16le=struct.pack(
            f"<{len(samples)}h",
            *samples,
        ),
    )

    with pytest.raises(
        ValueError,
        match="structural authority changed",
    ):
        changed.verify(CAPTURE_KEY)
