from __future__ import annotations

import hashlib
import json
import math
import struct

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.binaural_room_hearing_coordinator import (
    BinauralRoomHearingCoordinator,
    BinauralRoomHearingState,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodiedBody,
    EmbodimentPort,
    EmbodimentWorldAuthority,
    MoveCommand,
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
    separate_authenticated_multi_emitter_capture,
)
from dsf_ai_service.substrate.w1_moving_multi_emitter_continuity import (
    AuthenticatedMoveStep,
    W1MovingMultiEmitterContinuityOwner,
)


WORLD_KEY = b"moving-room-world-authority-key"
EMITTER_KEY = b"moving-room-emitter-authority-key"
CAPTURE_KEY = b"moving-room-capture-authority-key"
HEARING_KEY = b"moving-room-hearing-authority-key"
CONTINUITY_KEY = b"moving-room-continuity-authority-key"
MOVING_PORT = "room.external.moving"
OTHER_PORT = "room.external.other"
SAMPLES = 960


def _pressure(
    frequency: int,
    *,
    amplitude: int,
    phase_samples: int,
) -> bytes:
    values = tuple(
        int(
            amplitude
            * math.sin(
                2
                * math.pi
                * frequency
                * (index + phase_samples)
                / 16_000
            )
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
                "moving-source",
                PoseMM(PositionMM(1_000, 1_500, 0), 180_000),
                100,
                300,
            ),
            EmbodiedBody(
                "other-source",
                PoseMM(PositionMM(1_000, 500, 0), 180_000),
                100,
                300,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(MOVING_PORT, "moving-source"),
            EmbodimentPort(OTHER_PORT, "other-source"),
        ),
    )


def _capture(
    *,
    world: EmbodimentWorldAuthority,
    emitter: W1AcousticEmitterAuthority,
    owner: W1AuthenticatedMultiEmitterCaptureOwner,
    epoch: str,
    pressures: tuple[bytes, bytes],
):
    owner.open(
        epoch_token=epoch,
        source_sample_start=0,
        source_sample_count=SAMPLES,
    )
    epoch_commitment = hashlib.sha256(epoch.encode("utf-8")).hexdigest()
    for sequence, (port, pressure) in enumerate(zip(
        (MOVING_PORT, OTHER_PORT),
        pressures,
        strict=True,
    )):
        command = VocalizeCommand(
            epoch_commitment_sha256=epoch_commitment,
            sequence=sequence,
            source_sample_start=0,
            pcm_sha256=hashlib.sha256(pressure).hexdigest(),
            sample_count=SAMPLES,
        )
        payload = encode_command(command)
        execution = world.execute_port_command(
            port_id=port,
            command_payload=payload,
            causal_intent_receipt_sha256=(
                hashlib.sha256(
                    f"{epoch}:{sequence}".encode("utf-8")
                ).hexdigest()
            ),
            expected_revision=world.observation_snapshot().revision,
        )
        observation = world.observation_snapshot()
        emission = emitter.emit(
            epoch_token=epoch,
            sequence=sequence,
            source_sample_start=0,
            observation_snapshot=observation,
            execution_receipt=execution,
            command_payload=payload,
            emitter_port_id=port,
            pcm_s16le=pressure,
        )
        owner.admit(
            emission=emission,
            observation_snapshot=observation,
            execution_receipt=execution,
        )
    return owner.close()


def _move(
    world: EmbodimentWorldAuthority,
    *,
    sequence: int,
    position: PositionMM,
) -> AuthenticatedMoveStep:
    payload = encode_command(MoveCommand(
        PoseMM(position, 180_000),
        duration_microseconds=200_000,
    ))
    receipt = world.execute_port_command(
        port_id=MOVING_PORT,
        command_payload=payload,
        causal_intent_receipt_sha256=hashlib.sha256(
            f"physical-movement:{sequence}".encode("utf-8")
        ).hexdigest(),
        expected_revision=world.observation_snapshot().revision,
    )
    assert receipt.disposition == "applied"
    return AuthenticatedMoveStep(
        command_payload=payload,
        execution_receipt=receipt,
    )


def test_causal_source_continues_when_anonymous_order_and_pressure_change():
    world = _world()
    emitter = W1AcousticEmitterAuthority(
        authority_key=EMITTER_KEY,
        world_authority=world,
    )
    capture_owner = W1AuthenticatedMultiEmitterCaptureOwner(
        authority_key=CAPTURE_KEY,
        world_authority=world,
        acoustic_emitter=emitter,
    )
    hearing = BinauralRoomHearingCoordinator(
        authority_key=HEARING_KEY,
        w1_capture_authority_key=CAPTURE_KEY,
    )
    continuity = W1MovingMultiEmitterContinuityOwner(
        authority_key=CONTINUITY_KEY,
        world_authority=world,
        capture_authority_key=CAPTURE_KEY,
        room_hearing_authority_key=HEARING_KEY,
        max_transitions=2,
    )

    prior_pressures = (
        _pressure(347, amplitude=3_200, phase_samples=0),
        _pressure(691, amplitude=2_800, phase_samples=7),
    )
    prior_capture = _capture(
        world=world,
        emitter=emitter,
        owner=capture_owner,
        epoch="moving-room-prior",
        pressures=prior_pressures,
    )
    prior_hearing = hearing.hear_authenticated_w1_capture(
        prior_capture
    )

    movements = (
        _move(
            world,
            sequence=0,
            position=PositionMM(500, 1_500, 0),
        ),
    )

    current_pressures = (
        _pressure(521, amplitude=3_600, phase_samples=11),
        _pressure(809, amplitude=2_400, phase_samples=3),
    )
    current_capture = _capture(
        world=world,
        emitter=emitter,
        owner=capture_owner,
        epoch="moving-room-current",
        pressures=current_pressures,
    )
    current_hearing = hearing.hear_authenticated_w1_capture(
        current_capture
    )
    settled = continuity.settle(
        prior_capture=prior_capture,
        current_capture=current_capture,
        prior_hearing=prior_hearing,
        current_hearing=current_hearing,
        movement_steps=movements,
    )

    assert prior_hearing.state is (
        BinauralRoomHearingState.SEPARATED_OCCURRENCES
    )
    assert current_hearing.state is (
        BinauralRoomHearingState.SEPARATED_OCCURRENCES
    )
    assert settled.prior_source_ordinal != (
        settled.current_source_ordinal
    )
    settled.verify(CONTINUITY_KEY)

    prior_separation = separate_authenticated_multi_emitter_capture(
        prior_capture,
        authority_key=CAPTURE_KEY,
    )
    current_separation = separate_authenticated_multi_emitter_capture(
        current_capture,
        authority_key=CAPTURE_KEY,
    )
    prior_index = prior_capture.paths.index(settled.prior_path)
    current_index = current_capture.paths.index(settled.current_path)
    assert (
        prior_separation.separated_pcm_s16le[prior_index]
        == prior_pressures[0]
    )
    assert (
        current_separation.separated_pcm_s16le[current_index]
        == current_pressures[0]
    )
    assert (
        prior_separation.separated_pcm_s16le[prior_index]
        != current_separation.separated_pcm_s16le[current_index]
    )

    for outcome in (prior_hearing, current_hearing):
        for occurrence in outcome.occurrences:
            assert all(
                tuple(name for name, _value in field_tuple.fields)
                == DSF_FIELD_ORDER
                for channel in occurrence.separated_field.auditory_l5.channels
                for component in (
                    channel.pressure,
                    channel.carrier_phase_advance,
                )
                for field_tuple in component.l4_field_tuples
            )

    return_movement = (
        _move(
            world,
            sequence=3,
            position=PositionMM(1_000, 1_500, 0),
        ),
    )
    return_pressures = (
        _pressure(947, amplitude=3_000, phase_samples=5),
        _pressure(271, amplitude=2_600, phase_samples=13),
    )
    return_capture = _capture(
        world=world,
        emitter=emitter,
        owner=capture_owner,
        epoch="moving-room-return",
        pressures=return_pressures,
    )
    return_hearing = hearing.hear_authenticated_w1_capture(
        return_capture
    )
    returned = continuity.settle(
        prior_capture=current_capture,
        current_capture=return_capture,
        prior_hearing=current_hearing,
        current_hearing=return_hearing,
        movement_steps=return_movement,
    )
    assert returned.lineage_token_sha256 == (
        settled.lineage_token_sha256
    )
    assert returned.prior_continuity_receipt_sha256 == (
        settled.authority_receipt_sha256
    )
    returned.verify(CONTINUITY_KEY)

    encoded = json.dumps(
        returned.authority_payload(),
        sort_keys=True,
    )
    for forbidden in (
        "body_id",
        "port_id",
        "source_tag",
        "transcript",
        "pcm_s16le",
        "routing_chi",
    ):
        assert forbidden not in encoded
    assert continuity.status() == {
        "active_lineage": True,
        "max_transitions": 2,
        "retained_raw_media_bytes": 0,
        "retained_transitions": 2,
        "schema": (
            "guala.w1.moving_multi_emitter_continuity_status.v1"
        ),
    }
