from __future__ import annotations

import json
import math
import struct
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SIGHT_SUBSTREAMS,
)
import dsf_ai_service.substrate.w1_audiovisual_physical_evidence as evidence_module
from dsf_ai_service.substrate.embodiment_world import (
    DEFAULT_MAX_BODIES,
    DEFAULT_MAX_OBJECTS,
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
    _AnonymousDetection,
    _BODY_AXES,
    _TOUCH_AXES,
    _anonymous_detections,
    _visual_inputs,
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
                position=PositionMM(1_500, 1_000, 0),
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
        port_id=PORT_ID,
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
        observation_snapshot=execution.after,
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
        result.evidence_receipt.acoustic_emission_receipt_sha256s
        == (emission.receipt.authority_receipt_sha256,)
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
    assert set(observed) == {"sight", "sound", "touch", "body"}
    assert len(observed["sight"].substreams) == 8
    assert len(observed["sound"].substreams) == 2
    assert len(observed["touch"].substreams) == len(_TOUCH_AXES)
    assert len(observed["body"].substreams) == len(_BODY_AXES)
    encoded_settlement = json.dumps(
        [
            {
                "sensor_id": substream.sensor_id,
                "substream_id": substream.substream_id,
                "coordinates": substream.coordinates,
            }
            for interpretation in settlement.interpretations
            for substream in interpretation.substreams
        ],
        sort_keys=True,
    )
    for forbidden in (
        "external-body",
        "guala-body-1",
        "teaching-object",
        EMITTER_PORT,
    ):
        assert forbidden not in encoded_settlement
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


def test_action_outcome_settles_anonymous_body_contact_without_fake_sound():
    accepted = []
    world = _world()
    owner = _owner(accepted.append)
    authority = _authority(world, owner)
    execution = _execution(world)

    result = authority.mount_action_outcome(execution)

    assert result.state is W1EvidenceState.OBSERVED
    assert result.reason == "anonymous_action_outcome_observed"
    assert result.binaural_pcm is None
    assert result.evidence_receipt is not None
    assert result.evidence_receipt.acoustic_emission_receipt_sha256s == ()
    assert result.evidence_receipt.binaural_commitment == {}
    assert result.evidence_receipt.world_execution_receipt_sha256 == (
        execution.authority_receipt_sha256
    )
    assert len(accepted) == 1
    settlement = result.causal_settlement
    assert settlement is not None
    assert settlement.source_tags == ()
    assert settlement.routing_chis == ()
    observed = {
        item.sense for item in settlement.interpretations
        if item.state == "observed"
    }
    unavailable = {
        item.sense for item in settlement.interpretations
        if item.state == "sensor_unavailable"
    }
    assert observed == {"sight", "touch", "body"}
    assert unavailable == {"sound", "smell", "taste"}
    with pytest.raises(ValueError, match="mount differs"):
        authority.verify_mount(replace(result, reason="changed"))


def test_current_observation_can_be_reproduced_without_committing_state():
    accepted = []
    world = _world()
    owner = _owner(accepted.append)
    authority = _authority(world, owner)

    first = authority.mount_current_observation(commit=False)
    second = authority.mount_current_observation(commit=False)

    assert first.state is W1EvidenceState.OBSERVED
    assert second.state is W1EvidenceState.OBSERVED
    assert first.evidence_receipt is not None
    assert first.evidence_receipt.world_execution_receipt_sha256 is None
    assert first.causal_settlement is not None
    assert second.causal_settlement is not None
    assert first.causal_settlement.structural_fingerprint == (
        second.causal_settlement.structural_fingerprint
    )
    assert accepted == []
    assert owner.status()["settled"] == 0


def test_action_outcome_reservation_commits_or_discards_atomically():
    accepted = []
    world = _world()
    owner = _owner(accepted.append)
    authority = _authority(world, owner)
    execution = _execution(world)
    prepared = authority.mount_action_outcome(
        execution,
        commit=False,
        reserve=True,
    )
    assert owner.status()["settled"] == 0
    assert owner.status()["prepared_reservation"] == 1
    authority.discard_prepared_mount(prepared)
    assert owner.status()["settled"] == 0
    assert owner.status()["prepared_reservation"] == 0
    assert accepted == []

    prepared_again = authority.mount_action_outcome(
        execution,
        commit=False,
        reserve=True,
    )
    authority.commit_prepared_mount(prepared_again)
    assert owner.status()["settled"] == 1
    assert owner.status()["prepared_reservation"] == 0
    assert accepted == [prepared_again.causal_settlement]


def test_authenticated_historical_action_can_be_reproduced_after_world_advances():
    world = _world()
    authority = _authority(world)
    picked = _execution(world)
    original = authority.mount_action_outcome(picked, commit=False)
    current = world.observation_snapshot()
    placed = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(
            PlaceCommand("teaching-object", PositionMM(1_600, 1_000, 0))
        ),
        causal_intent_receipt_sha256="2" * 64,
        expected_revision=current.revision,
    )
    assert placed.disposition == "applied"

    with pytest.raises(ValueError, match="not the current world"):
        authority.mount_action_outcome(picked, commit=False)
    reproduced = authority.mount_authenticated_action_outcome(
        picked, commit=False
    )

    assert original.causal_settlement is not None
    assert reproduced.causal_settlement is not None
    assert reproduced.causal_settlement.structural_fingerprint == (
        original.causal_settlement.structural_fingerprint
    )


def test_rejected_world_command_cannot_be_mounted_as_an_action_outcome():
    world = _world()
    authority = _authority(world)
    before = world.observation_snapshot()
    rejected = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(PickCommand("missing-object")),
        causal_intent_receipt_sha256="3" * 64,
        expected_revision=before.revision,
    )
    assert rejected.disposition == "rejected"

    with pytest.raises(ValueError, match="applied"):
        authority.mount_action_outcome(rejected, commit=False)
    with pytest.raises(ValueError, match="applied"):
        authority.mount_authenticated_action_outcome(
            rejected, commit=False
        )


def test_visual_transport_capacity_equals_exact_W1_inventory() -> None:
    assert MAX_NATIVE_SIGHT_SUBSTREAMS == (
        (DEFAULT_MAX_BODIES - 1 + DEFAULT_MAX_OBJECTS) * 4
    )


def test_max_inventory_mount_preserves_all_sight_ports_and_full_fields():
    center = PositionMM(2_500, 2_500, 0)
    points = tuple(
        PositionMM(
            2_500 + round(1_500 * math.cos(2 * math.pi * index / 19)),
            2_500 + round(1_500 * math.sin(2 * math.pi * index / 19)),
            0,
        )
        for index in range(19)
    )
    bodies = [EmbodiedBody("self", PoseMM(center, 0), 50, 800)]
    ports = [EmbodimentPort(PORT_ID, "self")]
    for index, position in enumerate(points[:3]):
        body_id = f"external-{index:02d}"
        bodies.append(
            EmbodiedBody(body_id, PoseMM(position, 180_000), 1, 100)
        )
        ports.append(
            EmbodimentPort(f"w1.external-{index:02d}", body_id)
        )
    objects = tuple(
        EmbodiedObject(f"object-{index:02d}", 1, 1, position)
        for index, position in enumerate(points[3:])
    )
    world = EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        bodies=tuple(bodies),
        self_body_id="self",
        actor_ports=tuple(ports),
        initial_objects=objects,
    )
    authority = _authority(world)
    assert len(_anonymous_detections(world.observation_snapshot())) == 19

    first = authority.mount_current_observation(commit=False)
    second = authority.mount_current_observation(commit=False)

    assert first.causal_settlement is not None
    assert second.causal_settlement is not None
    sight = next(
        item for item in first.causal_settlement.interpretations
        if item.sense == "sight"
    )
    assert len(sight.substreams) == MAX_NATIVE_SIGHT_SUBSTREAMS
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for substream in sight.substreams
        for field_tuple in substream.field_tuples
    )
    assert first.causal_settlement.structural_fingerprint == (
        second.causal_settlement.structural_fingerprint
    )
    settlement_payload = first.causal_settlement.receipt_registry.resolve(
        first.causal_settlement.authority_receipt_sha256,
        "maximum W1 causal settlement",
    )
    assert len(settlement_payload) <= 2 * 1024 * 1024
    assert len(json.dumps(first.persistence_record()).encode("utf-8")) <= 4096


def test_visual_appearance_disappearance_is_exact_anonymous_and_fail_closed(
    monkeypatch,
) -> None:
    def detection(control_id: str, x: int) -> _AnonymousDetection:
        return _AnonymousDetection(
            control_id,
            (
                Fraction(x, 8),
                Fraction(0),
                Fraction(0),
                Fraction(1, 8),
            ),
        )

    def probe(before, after):
        sequences = iter((before, after))
        monkeypatch.setattr(
            evidence_module,
            "_anonymous_detections",
            lambda _snapshot: next(sequences),
        )
        return _visual_inputs(
            object(),
            object(),
            source_time_start=Fraction(0),
            source_time_end=Fraction(1),
        )

    appeared, _commitment, appeared_ambiguous = probe(
        (
            detection("control-A-identity", 1),
            detection("control-C-identity", 3),
        ),
        (
            detection("control-A-identity", 1),
            detection("control-B-identity", 2),
            detection("control-C-identity", 3),
        ),
    )
    assert appeared_ambiguous is False
    assert len(appeared) == 12
    radius_signals = tuple(
        item.normalized_signal for item in appeared
        if item.substream_id.endswith("-radius")
    )
    assert (-1.0, 0.125) in radius_signals
    assert all(
        "control-" not in json.dumps({
            "coordinates": [
                [item.axis_id, item.coordinate_id]
                for item in value.coordinates
            ],
            "sensor_id": value.sensor_id,
            "substream_id": value.substream_id,
        })
        for value in appeared
    )

    disappeared, _commitment, disappeared_ambiguous = probe(
        (
            detection("control-A-identity", 1),
            detection("control-C-identity", 3),
        ),
        (
            detection("control-C-identity", 3),
            detection("control-B-identity", 4),
        ),
    )
    assert disappeared_ambiguous is False
    assert len(disappeared) == 12
    assert (0.125, -1.0) in tuple(
        item.normalized_signal for item in disappeared
        if item.substream_id.endswith("-radius")
    )

    incomparable, _commitment, incomparable_ambiguous = probe(
        (
            detection("control-A-identity", 1),
            detection("control-C-identity", 3),
        ),
        (
            detection("control-B-identity", 1),
            detection("control-C-identity", 3),
        ),
    )
    assert incomparable_ambiguous is True
    assert incomparable == ()

    crossed, _commitment, crossed_ambiguous = probe(
        (
            detection("control-A-identity", 1),
            detection("control-B-identity", 2),
        ),
        (
            detection("control-B-identity", 1),
            detection("control-A-identity", 2),
        ),
    )
    assert crossed_ambiguous is True
    assert crossed == ()


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


def test_maximum_valid_body_reach_has_its_own_exact_physical_scale():
    world = EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        bodies=(
            EmbodiedBody(
                "external-body",
                PoseMM(PositionMM(3_500, 2_500, 0), 180_000),
                radius_mm=200,
                reach_mm=600,
            ),
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                radius_mm=250,
                reach_mm=1_000_000,
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
                position=PositionMM(1_500, 1_000, 0),
            ),
        ),
    )
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=_emission(authority, epoch, execution),
    )

    assert result.state is W1EvidenceState.OBSERVED
    assert result.causal_settlement is not None


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
    first_emission = _emission(
        authority,
        epoch,
        execution,
        pcm=emitted,
    )

    first = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=first_emission,
    )

    assert first.state is W1EvidenceState.UNKNOWN
    assert first.reason == "received_pressure_is_silent"
    assert first.binaural_pcm is None
    assert first.causal_settlement is None
    assert authority.status()["active_epochs"] == 1
    second_execution = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(PlaceCommand(
            "teaching-object",
            PositionMM(1_500, 1_200, 0),
        )),
        causal_intent_receipt_sha256="4" * 64,
        expected_revision=execution.after.revision,
    )
    assert second_execution.disposition == "applied"
    second_emission = _emission(
        authority,
        epoch,
        second_execution,
        sequence=1,
        source_sample_start=len(emitted) // 2,
        pcm=b"\x00\x00" * (len(emitted) // 2),
    )
    second = authority.mount(
        epoch_token=epoch,
        sequence=1,
        execution_receipt=second_execution,
        acoustic_emission=second_emission,
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
    assert second.evidence_receipt is not None
    assert second.evidence_receipt.acoustic_emission_receipt_sha256s == (
        first_emission.receipt.authority_receipt_sha256,
        second_emission.receipt.authority_receipt_sha256,
    )


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
        port_id=PORT_ID,
        command_payload=encode_command(PlaceCommand(
            "teaching-object",
            PositionMM(1_500, 1_200, 0),
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

    with pytest.raises(ValueError, match="current world"):
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
    assert result.binaural_pcm is None
    assert result.causal_settlement is None
    assert authority.status()["active_epochs"] == 0


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


def test_external_sound_and_self_action_share_one_authenticated_outcome():
    world = _world()
    authority = _authority(world)
    epoch = authority.open_epoch()
    execution = _execution(world)
    emission = _emission(authority, epoch, execution)

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=emission,
    )

    assert execution.port_id == PORT_ID
    assert emission.receipt.emitter_port_id == EMITTER_PORT
    assert emission.receipt.world_observation_receipt_sha256 == (
        execution.after.authority_receipt_sha256
    )
    assert result.state is W1EvidenceState.OBSERVED
    assert result.causal_settlement is not None
    observed = {
        item.sense: item for item in result.causal_settlement.interpretations
        if item.state == "observed"
    }
    assert any(
        field_tuple.fields != substream.field_tuples[0].fields
        for sense in ("touch", "body")
        for substream in observed[sense].substreams
        for field_tuple in substream.field_tuples[1:]
    )


def test_self_navigation_and_external_sound_share_post_action_receptors():
    world = _world()
    before = world.observation_snapshot()
    execution = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(MoveCommand(PoseMM(
            PositionMM(1_000, 1_200, 0), 0
        ))),
        causal_intent_receipt_sha256=INTENT_RECEIPT,
        expected_revision=before.revision,
    )
    assert execution.disposition == "applied"
    authority = _authority(world)
    epoch = authority.open_epoch()

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=_emission(authority, epoch, execution),
    )

    assert execution.port_id == PORT_ID
    assert execution.before.bodies != execution.after.bodies
    assert result.state is W1EvidenceState.OBSERVED
    assert result.causal_settlement is not None
    observed = {
        item.sense: item for item in result.causal_settlement.interpretations
        if item.state == "observed"
    }
    assert set(observed) == {"sight", "sound", "touch", "body"}


def test_visual_order_crossing_fails_closed_without_causal_settlement():
    accepted = []
    world = EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        bodies=(
            EmbodiedBody(
                "external-body",
                PoseMM(PositionMM(1_500, 1_400, 0), 180_000),
                radius_mm=100,
                reach_mm=500,
            ),
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                radius_mm=250,
                reach_mm=800,
                held_object_id="teaching-object",
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(EMITTER_PORT, "external-body"),
        ),
        initial_objects=(
            EmbodiedObject(
                "teaching-object",
                radius_mm=50,
                mass_grams=100,
                position=None,
                held_by_body_id="guala-body-1",
            ),
        ),
    )
    before = world.observation_snapshot()
    execution = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(PlaceCommand(
            "teaching-object",
            PositionMM(1_650, 1_400, 0),
        )),
        causal_intent_receipt_sha256=INTENT_RECEIPT,
        expected_revision=before.revision,
    )
    assert execution.disposition == "applied"
    owner = _owner(accepted.append)
    authority = _authority(world, owner)
    epoch = authority.open_epoch()

    result = authority.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=_emission(authority, epoch, execution),
    )

    assert result.state is W1EvidenceState.AMBIGUOUS
    assert result.reason == "anonymous_visual_order_crossed"
    assert result.evidence_receipt is None
    assert result.causal_settlement is None
    assert accepted == []
    assert owner.status()["settled"] == 0
    assert owner.status()["prepared_reservation"] == 0
    assert authority.status()["active_epochs"] == 0


def test_changed_acoustic_path_cannot_relabel_delayed_pressure():
    accepted = []
    source_a = "w1.source-a"
    source_b = "w1.source-b"
    world = EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        max_bodies=3,
        bodies=(
            EmbodiedBody(
                "source-a-body",
                PoseMM(PositionMM(3_500, 2_500, 0), 180_000),
                radius_mm=1,
                reach_mm=100,
            ),
            EmbodiedBody(
                "source-b-body",
                PoseMM(PositionMM(3_503, 2_500, 0), 180_000),
                radius_mm=1,
                reach_mm=100,
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
            EmbodimentPort(source_a, "source-a-body"),
            EmbodimentPort(source_b, "source-b-body"),
        ),
        initial_objects=(
            EmbodiedObject(
                "teaching-object",
                radius_mm=100,
                mass_grams=500,
                position=PositionMM(1_500, 1_000, 0),
            ),
        ),
    )
    owner = _owner(accepted.append)
    authority = _authority(world, owner)
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
            emitter_port_id=source_a,
        ),
    )
    assert first.state is W1EvidenceState.OBSERVED
    second_execution = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(PlaceCommand(
            "teaching-object", PositionMM(1_500, 1_200, 0)
        )),
        causal_intent_receipt_sha256="9" * 64,
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
            source_sample_start=1_024,
            emitter_port_id=source_b,
        ),
    )

    assert second.state is W1EvidenceState.UNKNOWN
    assert second.reason == "acoustic_path_changed_closed_the_epoch"
    assert second.causal_settlement is None
    assert len(accepted) == 1
    assert owner.status()["settled"] == 1
    assert authority.status()["active_epochs"] == 0


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
            observation_snapshot=execution.after,
            emitter_port_id=EMITTER_PORT,
            source_sample_start=0,
            pcm_s16le=_pcm(MAX_EMITTED_PCM_SAMPLES + 1),
        )
    status = authority.status()
    assert 0 < status["retained_raw_media_bytes"] <= (
        status["max_retained_raw_media_bytes"]
    )
