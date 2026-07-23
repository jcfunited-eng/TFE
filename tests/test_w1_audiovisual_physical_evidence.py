from __future__ import annotations

import json
import struct
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodiedBody,
    EmbodiedObject,
    EmbodimentPort,
    EmbodimentWorldAuthority,
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    MAX_EMITTED_PCM_SAMPLES,
    W1AudiovisualPhysicalEvidenceAuthority,
    W1EvidenceState,
    _anonymous_detections,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    AuthenticatedW1AcousticEmission,
    W1AcousticEmitterAuthority,
)


WORLD_KEY = b"world-authority-key-for-w1-tests"
EVIDENCE_KEY = b"evidence-authority-key-for-w1-tests"
EMISSION_KEY = b"emission-authority-key-for-w1-tests"
INTENT_RECEIPT = "1" * 64
EMITTER_PORT = "w1.external-emitter"


def _pcm(sample_count: int = 1_024) -> bytes:
    samples = tuple(
        12_000 if index % 16 < 8 else -12_000
        for index in range(sample_count)
    )
    return struct.pack(f"<{sample_count}h", *samples)


def _last_sample_impulse_pcm(sample_count: int = 1_024) -> bytes:
    return struct.pack(
        f"<{sample_count}h",
        *(0 for _index in range(sample_count - 1)),
        32_767,
    )


def _world(
    *,
    external_position: PositionMM = PositionMM(3_500, 2_500, 0),
    self_heading_millidegrees: int = 0,
) -> EmbodimentWorldAuthority:
    return EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        bodies=(
            EmbodiedBody(
                "external-body",
                PoseMM(external_position, 180_000),
                radius_mm=200,
                reach_mm=600,
            ),
            EmbodiedBody(
                "guala-body-1",
                PoseMM(
                    PositionMM(1_000, 1_000, 0),
                    self_heading_millidegrees,
                ),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(EMITTER_PORT, "external-body"),
        ),
        initial_objects=(
            EmbodiedObject(
                "teaching-object",
                radius_mm=100,
                mass_grams=500,
                position=PositionMM(
                    external_position.x - 300,
                    external_position.y,
                    external_position.z,
                ),
            ),
        ),
    )


def _owner(on_settlement=None) -> ExactCausalExperienceOwner:
    return ExactCausalExperienceOwner(
        on_settlement=on_settlement or (lambda _settlement: None),
        log_event=lambda *_args, **_kwargs: None,
    )


def _execution(world: EmbodimentWorldAuthority):
    before = world.observation_snapshot()
    receipt = world.execute_port_command(
        port_id=EMITTER_PORT,
        command_payload=encode_command(PickCommand("teaching-object")),
        causal_intent_receipt_sha256=INTENT_RECEIPT,
        expected_revision=before.revision,
    )
    assert receipt.disposition == "applied"
    return receipt


def _authority(world, owner=None):
    return W1AudiovisualPhysicalEvidenceAuthority(
        authority_key=EVIDENCE_KEY,
        world_authority=world,
        causal_owner=owner or _owner(),
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=EMISSION_KEY,
            world_authority=world,
        ),
    )


def _emission(
    authority,
    epoch,
    execution,
    *,
    sequence=0,
    source_sample_start=0,
    emitter_port_id=EMITTER_PORT,
    pcm=None,
):
    return authority.emit_acoustic_pressure(
        epoch_token=epoch,
        sequence=sequence,
        source_sample_start=source_sample_start,
        execution_receipt=execution,
        emitter_port_id=emitter_port_id,
        pcm_s16le=pcm or _pcm(),
    )


def test_mount_retains_full_fields_but_no_perceptual_identity_or_raw_media():
    accepted = []
    world = _world()
    authority = _authority(world, _owner(accepted.append))
    epoch = authority.open_epoch()
    execution = _execution(world)
    emission = _emission(authority, epoch, execution)

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=emission,
    )

    assert result.state is W1EvidenceState.OBSERVED
    result.verify(EVIDENCE_KEY)
    assert result.evidence_receipt is not None
    assert (
        result.evidence_receipt.acoustic_emission_receipt_sha256
        == emission.receipt.authority_receipt_sha256
    )
    assert len(accepted) == 1
    assert result.binaural_pcm is not None
    assert (
        result.binaural_pcm.left_pcm_s16le
        != result.binaural_pcm.right_pcm_s16le
    )
    settlement = result.causal_settlement
    assert settlement is not None
    assert settlement.source_tags == ()
    assert settlement.routing_chis == ()
    observed = {
        item.sense: item
        for item in settlement.interpretations
        if item.state == "observed"
    }
    assert set(observed) == {"sight", "sound"}
    assert len(observed["sight"].substreams) == 4
    assert len(observed["sound"].substreams) == 2
    for interpretation in settlement.interpretations:
        for substream in interpretation.substreams:
            for field_tuple in substream.field_tuples:
                assert tuple(
                    name for name, _value in field_tuple.fields
                ) == DSF_FIELD_ORDER

    persisted = json.dumps(result.persistence_record(), sort_keys=True)
    for forbidden in (
        "external-body",
        EMITTER_PORT,
        "guala-body-1",
        "teaching-object",
        "pcm_s16le",
    ):
        assert forbidden not in persisted
    status = authority.status()
    assert 0 < status["retained_raw_media_bytes"] <= (
        status["max_retained_raw_media_bytes"]
    )
    assert authority.close_epoch(epoch)
    assert authority.status()["retained_raw_media_bytes"] == 0


def test_visual_geometry_is_exactly_binary_representable_at_native_boundary():
    world = _world()
    values = tuple(
        value
        for detection in _anonymous_detections(
            world.observation_snapshot()
        )
        for value in detection.values
    )

    assert values
    assert all(Fraction.from_float(float(value)) == value for value in values)


def test_tampered_world_receipt_is_rejected_before_mounting():
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)
    tampered = replace(execution, authority_hmac_sha256="0" * 64)
    emission = _emission(authority, epoch, execution)

    with pytest.raises(ValueError, match="execution HMAC"):
        authority.mount(
            epoch_token=epoch,
            sequence=0,
            execution_receipt=tampered,
            acoustic_emission=emission,
        )

    assert authority.status()["active_epochs"] == 1
    assert authority.status()["retained_raw_media_bytes"] == 0


def test_sequence_gap_and_process_restart_fail_unknown_and_close_state():
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)

    gap = authority.mount(
        epoch_token=epoch,
        sequence=1,
        execution_receipt=execution,
        acoustic_emission=_emission(
            authority,
            epoch,
            execution,
            sequence=1,
        ),
    )
    assert gap.state is W1EvidenceState.UNKNOWN
    assert gap.reason == "audiovisual_sequence_gap_closed_the_epoch"
    assert authority.status()["active_epochs"] == 0

    replacement = _authority(world)
    restarted = replacement.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=_emission(replacement, epoch, execution),
    )
    assert restarted.state is W1EvidenceState.UNKNOWN
    assert restarted.reason == "audiovisual_epoch_unknown_after_gap_or_restart"


def test_pcm_tamper_is_rejected_before_perceptual_settlement():
    accepted = []
    world = _world()
    authority = _authority(world, _owner(accepted.append))
    epoch = authority.open_epoch()
    execution = _execution(world)
    emission = _emission(authority, epoch, execution)
    tampered = AuthenticatedW1AcousticEmission(
        receipt=emission.receipt,
        pcm_s16le=bytes([emission.pcm_s16le[0] ^ 1]) + emission.pcm_s16le[1:],
    )

    with pytest.raises(ValueError, match="authenticated emission"):
        authority.mount(
            epoch_token=epoch,
            sequence=0,
            execution_receipt=execution,
            acoustic_emission=tampered,
        )

    assert accepted == []
    assert authority.status()["active_epochs"] == 1


def test_propagation_delay_retains_the_entire_received_waveform():
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)
    emitted = _last_sample_impulse_pcm()

    first = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=_emission(
            authority,
            epoch,
            execution,
            pcm=emitted,
        ),
    )

    assert first.binaural_pcm is not None
    assert not any(
        value[0] for value in struct.iter_unpack(
            "<h", first.binaural_pcm.left_pcm_s16le
        )
    )
    assert not any(
        value[0] for value in struct.iter_unpack(
            "<h", first.binaural_pcm.right_pcm_s16le
        )
    )
    second_execution = world.execute_port_command(
        port_id=EMITTER_PORT,
        command_payload=encode_command(PlaceCommand(
            "teaching-object",
            PositionMM(3_200, 2_500, 0),
        )),
        causal_intent_receipt_sha256="4" * 64,
        expected_revision=execution.after.revision,
    )
    assert second_execution.disposition == "applied"
    second = authority.mount(
        epoch_token=epoch,
        sequence=1,
        execution_receipt=second_execution,
        acoustic_emission=_emission(
            authority,
            epoch,
            second_execution,
            sequence=1,
            source_sample_start=len(emitted) // 2,
            pcm=b"\x00\x00" * (len(emitted) // 2),
        ),
    )

    assert second.binaural_pcm is not None
    assert any(
        value[0] for value in struct.iter_unpack(
            "<h", second.binaural_pcm.left_pcm_s16le
        )
    )
    assert any(
        value[0] for value in struct.iter_unpack(
            "<h", second.binaural_pcm.right_pcm_s16le
        )
    )
    assert second.state is W1EvidenceState.OBSERVED


def test_consecutive_captures_keep_one_exact_emitted_sample_clock():
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    first_execution = _execution(world)
    first = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=first_execution,
        acoustic_emission=_emission(
            authority,
            epoch,
            first_execution,
        ),
    )
    assert first.binaural_pcm is not None
    first_emitted_count = max(
        first.binaural_pcm.left_sample_count,
        first.binaural_pcm.right_sample_count,
    )
    second_execution = world.execute_port_command(
        port_id=EMITTER_PORT,
        command_payload=encode_command(PlaceCommand(
            "teaching-object",
            PositionMM(3_200, 2_500, 0),
        )),
        causal_intent_receipt_sha256="3" * 64,
        expected_revision=first_execution.after.revision,
    )
    assert second_execution.disposition == "applied"

    second = authority.mount(
        epoch_token=epoch,
        sequence=1,
        execution_receipt=second_execution,
        acoustic_emission=_emission(
            authority,
            epoch,
            second_execution,
            sequence=1,
            source_sample_start=first_emitted_count,
        ),
    )

    assert first.evidence_receipt is not None
    assert second.evidence_receipt is not None
    assert second.evidence_receipt.source_time_start == (
        first.evidence_receipt.source_time_end
    )
    assert second.evidence_receipt.prior_evidence_receipt_sha256 == (
        first.evidence_receipt.authority_receipt_sha256
    )


def test_advertised_maximum_emission_is_mountable_with_propagation():
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)
    maximum = _pcm(MAX_EMITTED_PCM_SAMPLES)

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=_emission(
            authority,
            epoch,
            execution,
            pcm=maximum,
        ),
    )

    assert result.binaural_pcm is not None
    assert result.binaural_pcm.left_sample_count == (
        MAX_EMITTED_PCM_SAMPLES
    )
    assert result.binaural_pcm.right_sample_count == (
        MAX_EMITTED_PCM_SAMPLES
    )
    assert result.state is W1EvidenceState.OBSERVED


def test_superseded_world_execution_cannot_be_replayed_as_current_sound():
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)
    superseding = world.execute_port_command(
        port_id=EMITTER_PORT,
        command_payload=encode_command(MoveCommand(
            PoseMM(PositionMM(3_500, 3_000, 0), 180_000)
        )),
        causal_intent_receipt_sha256="2" * 64,
        expected_revision=execution.after.revision,
    )
    assert superseding.disposition == "applied"

    with pytest.raises(ValueError, match="authenticated emission"):
        _emission(authority, epoch, execution)

    assert authority.status()["active_epochs"] == 1


def test_acoustic_sample_gap_closes_epoch_without_settlement():
    accepted = []
    world = _world()
    authority = _authority(world, _owner(accepted.append))
    epoch = authority.open_epoch()
    execution = _execution(world)
    emission = _emission(
        authority,
        epoch,
        execution,
        source_sample_start=1,
    )

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=emission,
    )

    assert result.state is W1EvidenceState.UNKNOWN
    assert result.reason == "acoustic_sample_gap_closed_the_epoch"
    assert accepted == []
    assert authority.status()["active_epochs"] == 0


def test_symmetric_two_ear_field_is_explicitly_ambiguous():
    world = _world(external_position=PositionMM(3_500, 1_000, 0))
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=_emission(authority, epoch, execution),
    )

    assert result.state is W1EvidenceState.AMBIGUOUS
    assert result.reason == "two_ear_field_is_spatially_symmetric"
    assert result.binaural_pcm is not None
    assert (
        result.binaural_pcm.left_pcm_s16le
        == result.binaural_pcm.right_pcm_s16le
    )


def test_unsettled_physical_capture_closes_continuity_epoch():
    world = _world(self_heading_millidegrees=1_000)
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=_emission(
            authority,
            epoch,
            execution,
        ),
    )

    assert result.state is W1EvidenceState.UNAVAILABLE
    assert result.reason == (
        "noncardinal_two_ear_calibration_is_unavailable"
    )
    assert authority.status()["active_epochs"] == 0


def test_self_port_cannot_authenticate_external_pressure():
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)

    with pytest.raises(ValueError, match="self port"):
        _emission(
            authority,
            epoch,
            execution,
            emitter_port_id=PORT_ID,
        )

    assert authority.status()["active_epochs"] == 1


def test_emission_actor_and_control_port_must_be_the_same_body():
    world = EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        max_bodies=3,
        bodies=(
            EmbodiedBody(
                "body-a",
                PoseMM(PositionMM(2_000, 4_000, 0), 0),
                radius_mm=100,
                reach_mm=500,
            ),
            EmbodiedBody(
                "body-b",
                PoseMM(PositionMM(4_000, 2_000, 0), 0),
                radius_mm=100,
                reach_mm=500,
            ),
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort("w1.body-a", "body-a"),
            EmbodimentPort("w1.body-b", "body-b"),
        ),
        initial_objects=(
            EmbodiedObject(
                "remote-object",
                radius_mm=50,
                mass_grams=100,
                position=PositionMM(2_300, 4_000, 0),
            ),
        ),
    )
    before = world.observation_snapshot()
    execution = world.execute_port_command(
        port_id="w1.body-a",
        command_payload=encode_command(PickCommand("remote-object")),
        causal_intent_receipt_sha256=INTENT_RECEIPT,
        expected_revision=before.revision,
    )
    assert execution.disposition == "applied"
    authority = _authority(world)
    epoch = authority.open_epoch()

    with pytest.raises(ValueError, match="acting emitter"):
        _emission(
            authority,
            epoch,
            execution,
            emitter_port_id="w1.body-b",
        )


def test_resource_bounds_and_transaction_rollback_preserve_epoch():
    failures = [True]

    def fail_once(_settlement):
        if failures:
            failures.pop()
            raise RuntimeError("downstream settlement rejected")

    owner = _owner(fail_once)
    world = _world()
    authority = _authority(world, owner)
    epoch = authority.open_epoch()
    execution = _execution(world)
    emission = _emission(authority, epoch, execution)

    with pytest.raises(RuntimeError, match="downstream settlement rejected"):
        authority.mount(
            epoch_token=epoch,
            sequence=0,
            execution_receipt=execution,
            acoustic_emission=emission,
        )
    assert owner.status()["prepared_reservation"] == 0

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=emission,
    )
    assert result.state is W1EvidenceState.OBSERVED

    second = authority.open_epoch()
    with pytest.raises(RuntimeError, match="epoch capacity"):
        authority.open_epoch()
    assert authority.close_epoch(second)

    with pytest.raises(ValueError, match="sample boundary"):
        authority.emit_acoustic_pressure(
            epoch_token=second,
            sequence=1,
            execution_receipt=execution,
            emitter_port_id=EMITTER_PORT,
            source_sample_start=0,
            pcm_s16le=_pcm(MAX_EMITTED_PCM_SAMPLES + 1),
        )
    status = authority.status()
    assert 0 < status["retained_raw_media_bytes"] <= (
        status["max_retained_raw_media_bytes"]
    )
