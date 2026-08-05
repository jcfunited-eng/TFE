"""Production proofs for the W1 physical-receptor sensory firewall."""

from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.embodiment_sensory_outcome import (
    RETINA_SUBSTREAM_COUNT,
    EmbodimentSensoryOutcomeAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    EmbodiedBody,
    EmbodiedObject,
    EmbodimentPort,
    EmbodimentWorldAuthority,
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)


AUTHORITY_KEY = "embodied-physical-receptor-test-key"


def _owner() -> ExactCausalExperienceOwner:
    return ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )


def _execute(
    world: EmbodimentWorldAuthority,
    command: MoveCommand | PickCommand,
    intent: int,
    *,
    port_id: str = PORT_ID,
):
    before = world.observation_snapshot()
    return world.execute_port_command(
        port_id=port_id,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=f"{intent:064x}",
        expected_revision=before.revision,
    )


def _sense(settlement, name: str):
    return next(
        interpretation
        for interpretation in settlement.interpretations
        if interpretation.sense == name
    )


def _raw(outcome, sense: str):
    return tuple(
        (
            substream.substream_id,
            substream.coordinates,
            substream.normalized_signal,
        )
        for substream in outcome.physical_substreams
        if substream.sense.value == sense
    )


def _custom_world(
    *,
    key: str,
    self_id: str,
    other_id: str,
    object_id: str,
    object_mass: int = 500,
    object_reflectance: tuple[int, ...] = (
        700_000,
        300_000,
        180_000,
        120_000,
        90_000,
        70_000,
    ),
) -> EmbodimentWorldAuthority:
    bodies = (
        EmbodiedBody(
            self_id,
            PoseMM(PositionMM(1000, 1000, 0), 0),
            radius_mm=250,
            reach_mm=800,
        ),
        EmbodiedBody(
            other_id,
            PoseMM(PositionMM(4750, 4750, 0), 180_000),
            radius_mm=250,
            reach_mm=800,
        ),
    )
    return EmbodimentWorldAuthority(
        authority_key=key,
        self_body_id=self_id,
        bodies=bodies,
        actor_ports=(
            EmbodimentPort(PORT_ID, self_id),
            EmbodimentPort(SECOND_BODY_PORT_ID, other_id),
        ),
        initial_objects=(
            EmbodiedObject(
                object_id,
                100,
                object_mass,
                PositionMM(1500, 1000, 0),
                reflectance_ppm=object_reflectance,
            ),
        ),
    )


def test_heading_and_fov_change_retinotopic_light_through_full_dsf() -> None:
    world = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    execution = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1000, 1000, 0), 180_000),
            200_000,
        ),
        1,
    )
    outcome = EmbodimentSensoryOutcomeAuthority(
        authority_key=AUTHORITY_KEY
    ).transduce(
        execution.after,
        causal_owner=_owner(),
        execution_receipt=execution,
        commit=False,
    )

    sight = tuple(
        substream
        for substream in outcome.physical_substreams
        if substream.sense.value == "sight"
    )
    assert len(sight) == RETINA_SUBSTREAM_COUNT == 162
    assert any(
        substream.normalized_signal[0] != substream.normalized_signal[1]
        for substream in sight
    )
    assert all(
        tuple(axis.axis_id for axis in substream.coordinates)
        == ("retinal-row", "retinal-column", "optical-band")
        for substream in sight
    )
    assert _sense(outcome.causal_settlement, "sight").state == "observed"
    for interpretation in outcome.causal_settlement.interpretations:
        for substream in interpretation.substreams:
            for field_tuple in substream.field_tuples:
                assert tuple(
                    name for name, _value in field_tuple.fields
                ) == DSF_FIELD_ORDER
    assert outcome.causal_settlement.routing_chis == ()


def test_nearer_surface_occludes_far_surface_without_object_identity() -> None:
    near = EmbodiedObject(
        "near-control-id",
        200,
        500,
        PositionMM(1500, 1000, 0),
        reflectance_ppm=(700_000, 200_000, 100_000, 80_000, 60_000, 40_000),
    )
    far_left = EmbodiedObject(
        "far-left-control-id",
        100,
        900,
        PositionMM(2500, 1000, 0),
        reflectance_ppm=(0, 0, 1_000_000, 0, 0, 0),
    )
    far_right = replace(
        far_left,
        object_id="far-right-control-id",
        reflectance_ppm=(1_000_000, 0, 0, 0, 0, 0),
    )
    left = EmbodimentWorldAuthority(
        authority_key=AUTHORITY_KEY,
        initial_objects=(near, far_left),
    )
    right = EmbodimentWorldAuthority(
        authority_key=AUTHORITY_KEY,
        initial_objects=(near, far_right),
    )
    transducer = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY)
    left_outcome = transducer.transduce(
        left.observation_snapshot(), causal_owner=_owner(), commit=False
    )
    right_outcome = transducer.transduce(
        right.observation_snapshot(), causal_owner=_owner(), commit=False
    )

    assert _raw(left_outcome, "sight") == _raw(right_outcome, "sight")
    assert (
        _sense(left_outcome.causal_settlement, "sight").structural_fingerprint
        == _sense(right_outcome.causal_settlement, "sight").structural_fingerprint
    )


def test_control_ids_labels_and_object_mass_never_enter_receptor_values() -> None:
    left = _custom_world(
        key=AUTHORITY_KEY,
        self_id="left-self-control-id",
        other_id="left-other-control-id",
        object_id="left-object-control-id",
        object_mass=500,
    )
    right = _custom_world(
        key=AUTHORITY_KEY,
        self_id="right-self-control-id",
        other_id="right-other-control-id",
        object_id="right-object-control-id",
        object_mass=999_999,
    )
    left_pick = _execute(
        left,
        PickCommand("left-object-control-id", 200_000),
        2,
    )
    right_pick = _execute(
        right,
        PickCommand("right-object-control-id", 200_000),
        2,
    )
    transducer = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY)
    left_outcome = transducer.transduce(
        left_pick.after,
        causal_owner=_owner(),
        execution_receipt=left_pick,
        commit=False,
    )
    right_outcome = transducer.transduce(
        right_pick.after,
        causal_owner=_owner(),
        execution_receipt=right_pick,
        commit=False,
    )

    assert _raw(left_outcome, "sight") == _raw(right_outcome, "sight")
    assert _raw(left_outcome, "body") == _raw(right_outcome, "body")
    assert _raw(left_outcome, "touch") == _raw(right_outcome, "touch")
    forbidden = (
        "left-self-control-id",
        "left-other-control-id",
        "left-object-control-id",
        "right-self-control-id",
        "right-other-control-id",
        "right-object-control-id",
    )
    rendered = repr(left_outcome.physical_substreams) + repr(
        right_outcome.physical_substreams
    )
    assert all(value not in rendered for value in forbidden)


def test_body_displacement_requires_authenticated_causal_substream() -> None:
    world = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    transducer = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY)
    passive = transducer.transduce(
        world.observation_snapshot(), causal_owner=_owner(), commit=False
    )
    assert _sense(passive.causal_settlement, "body").state == "sensor_unavailable"
    assert _raw(passive, "body") == ()

    execution = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1000, 1400, 0), 90_000),
            200_000,
        ),
        3,
    )
    causal = transducer.transduce(
        execution.after,
        causal_owner=_owner(),
        execution_receipt=execution,
        commit=False,
    )
    body = _raw(causal, "body")
    assert len(body) == 4
    assert all(values[0] == 0.0 for _name, _coordinates, values in body)
    assert body[1][2][1] == 0.08
    assert body[3][2][1] == 0.5
    assert (
        causal.observation_receipt.execution_receipt_sha256
        == execution.authority_receipt_sha256
    )

    with pytest.raises(ValueError, match="does not end"):
        transducer.transduce(
            execution.before,
            causal_owner=_owner(),
            execution_receipt=execution,
            commit=False,
        )


def test_body_receptors_are_translation_invariant_not_global_coordinates() -> None:
    def world_at(x: int, y: int) -> EmbodimentWorldAuthority:
        return EmbodimentWorldAuthority(
            authority_key=AUTHORITY_KEY,
            bodies=(
                EmbodiedBody(
                    "guala-body-1",
                    PoseMM(PositionMM(x, y, 0), 0),
                    radius_mm=250,
                    reach_mm=800,
                ),
                EmbodiedBody(
                    "w1-body-2",
                    PoseMM(PositionMM(4750, 4750, 0), 180_000),
                    radius_mm=250,
                    reach_mm=800,
                ),
            ),
            initial_objects=(
                EmbodiedObject(
                    "physical-object",
                    100,
                    500,
                    PositionMM(x + 500, y, 0),
                ),
            ),
        )

    left = world_at(1000, 1000)
    right = world_at(2000, 2000)
    left_execution = _execute(
        left,
        MoveCommand(
            PoseMM(PositionMM(1000, 1400, 0), 90_000),
            200_000,
        ),
        40,
    )
    right_execution = _execute(
        right,
        MoveCommand(
            PoseMM(PositionMM(2000, 2400, 0), 90_000),
            200_000,
        ),
        40,
    )
    transducer = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY)
    left_outcome = transducer.transduce(
        left_execution.after,
        causal_owner=_owner(),
        execution_receipt=left_execution,
        commit=False,
    )
    right_outcome = transducer.transduce(
        right_execution.after,
        causal_owner=_owner(),
        execution_receipt=right_execution,
        commit=False,
    )

    assert _raw(left_outcome, "body") == _raw(right_outcome, "body")
    assert all(
        "position" not in repr(coordinates)
        for _name, coordinates, _values in _raw(left_outcome, "body")
    )


def test_cold_restore_reproduces_receptor_and_full_field_identity() -> None:
    world = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    execution = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1000, 1400, 0), 90_000),
            200_000,
        ),
        4,
    )
    encoded = world.encoded_snapshot()
    restored = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    restored.restore_encoded(encoded)
    restored_execution = restored.latest_execution_snapshot()
    assert restored_execution == execution
    transducer = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY)
    before_restart = transducer.transduce(
        execution.after,
        causal_owner=_owner(),
        execution_receipt=execution,
        commit=False,
    )
    after_restart = transducer.transduce(
        restored.observation_snapshot(),
        causal_owner=_owner(),
        execution_receipt=restored_execution,
        commit=False,
    )

    assert before_restart.physical_substreams == after_restart.physical_substreams
    assert before_restart.observation_receipt == after_restart.observation_receipt
    assert (
        before_restart.causal_settlement.structural_fingerprint
        == after_restart.causal_settlement.structural_fingerprint
    )


def test_receptors_are_fixed_bounded_and_absent_senses_remain_truthful() -> None:
    world = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    execution = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1000, 1000, 0), 180_000),
            200_000,
        ),
        5,
    )
    transducer = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY)
    first = transducer.transduce(
        execution.after,
        causal_owner=_owner(),
        execution_receipt=execution,
        commit=False,
    )
    for _ in range(20):
        repeated = transducer.transduce(
            execution.after,
            causal_owner=_owner(),
            execution_receipt=execution,
            commit=False,
        )
        assert repeated.physical_substreams == first.physical_substreams

    counts = {
        sense: len(_raw(first, sense))
        for sense in ("sight", "touch", "body")
    }
    assert counts == {"sight": 162, "touch": 3, "body": 4}
    assert sum(
        len(substream.normalized_signal)
        for substream in first.physical_substreams
    ) == 338
    assert transducer.__dict__ == {"_key": AUTHORITY_KEY.encode("utf-8")}
    for sense in ("sound", "smell", "taste"):
        assert (
            _sense(first.causal_settlement, sense).state
            == "sensor_unavailable"
        )
    first.built_full_field.boundary.verify(
        first.built_full_field.receipt_registry
    )
    first.causal_settlement.verify()
