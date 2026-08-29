"""L-009 source selection belongs only to Guala's physical grip action."""

from __future__ import annotations

from copy import deepcopy

from dsf_ai_service import native_production_app as production


MOTOR = "12" * 16
OPPONENT = "23" * 16
FORMATION = "34" * 32
THOUGHT_SOURCE = "45" * 32
RECURRENT = "56" * 16


def _transition() -> dict[str, object]:
    thought_transfer = (RECURRENT, MOTOR, 0, 5)
    return {
        "organism_tick": 44,
        "state_sha256": "67" * 32,
        "causal_cross_context_use": {
            "origin_kind": "retained_formation",
            "formation_receipt_sha256": FORMATION,
            "causal_thought_transitions": (
                (
                    THOUGHT_SOURCE,
                    FORMATION,
                    RECURRENT,
                    MOTOR,
                    thought_transfer,
                ),
            ),
            "directed_physical_transfers": (thought_transfer,),
            "motor_unit_recruitment": {"motor_lineage": MOTOR},
        },
        "externally_reassembled_formation_causal_use": {
            "origin_kind": "externally_reassembled_retained_formation",
            "formation_receipt_sha256": FORMATION,
            "reassembly_organism_tick": 41,
            "motor_organism_tick": 43,
            "motor_unit_recruitment": {"motor_lineage": MOTOR},
        },
        "motor_action": {
            "causal_intent_receipt_sha256": "78" * 32,
            "prepared_recruitments": (
                {
                    "motor_lineage": MOTOR,
                    "outward_elementary_carriers": 5,
                    "preparation_transfers": ({"physical": "exact"},),
                },
                {
                    "motor_lineage": OPPONENT,
                    "outward_elementary_carriers": 2,
                    "preparation_transfers": ({"physical": "exact"},),
                },
            ),
            "body_effector_bindings": (
                {
                    "source_tick": 43,
                    "motor_lineage": MOTOR,
                    "axis": "left_grip_aperture",
                    "direction": "toward_minimum",
                    "outward_elementary_carriers": 5,
                },
                {
                    "source_tick": 43,
                    "motor_lineage": OPPONENT,
                    "axis": "left_grip_aperture",
                    "direction": "toward_maximum",
                    "outward_elementary_carriers": 2,
                },
            ),
            "articulated_body_consequences": (
                {
                    "source_tick": 43,
                    "axis": "left_grip_aperture",
                    "unit": "micrometre",
                    "predecessor_position": 10,
                    "successor_position": 7,
                    "signed_displacement": -3,
                    "toward_minimum_carriers": 5,
                    "toward_maximum_carriers": 2,
                    "opposed_carriers_per_terminal": 2,
                    "applied_displacement_quanta": 3,
                    "stalled_carriers": 0,
                },
            ),
        },
    }


def test_exact_source_caused_native_grip_selects_the_offered_book() -> None:
    selection = production._gutenberg_grip_selection_from_transition(
        _transition(),
        predecessor_tick=40,
    )

    assert selection == {
        "axis": "left_grip_aperture",
        "causal_motor_lineage": MOTOR,
        "formation_receipt_sha256": FORMATION,
        "grip_closing_displacement": -3,
        "motor_organism_tick": 43,
        "reassembly_organism_tick": 41,
        "selection_authority": "source-caused-thought-owned-native-grip-choice",
        "thought_source_formation_receipts": (THOUGHT_SOURCE,),
    }


def test_coincident_or_unapplied_grip_cannot_select_a_book() -> None:
    stale = _transition()
    stale["externally_reassembled_formation_causal_use"][
        "reassembly_organism_tick"
    ] = 40
    assert production._gutenberg_grip_selection_from_transition(
        stale,
        predecessor_tick=40,
    ) is None

    unrelated = deepcopy(_transition())
    unrelated["motor_action"]["body_effector_bindings"][0][
        "motor_lineage"
    ] = "56" * 16
    assert production._gutenberg_grip_selection_from_transition(
        unrelated,
        predecessor_tick=40,
    ) is None

    unapplied = deepcopy(_transition())
    unapplied["motor_action"]["articulated_body_consequences"][0][
        "signed_displacement"
    ] = 0
    unapplied["motor_action"]["articulated_body_consequences"][0][
        "successor_position"
    ] = 10
    unapplied["motor_action"]["articulated_body_consequences"][0][
        "applied_displacement_quanta"
    ] = 0
    assert production._gutenberg_grip_selection_from_transition(
        unapplied,
        predecessor_tick=40,
    ) is None


def test_non_grip_motor_action_cannot_select_a_book() -> None:
    transition = deepcopy(_transition())
    transition["motor_action"]["body_effector_bindings"][0]["axis"] = (
        "right_elbow_flexion"
    )
    transition["motor_action"]["articulated_body_consequences"][0]["axis"] = (
        "right_elbow_flexion"
    )

    assert production._gutenberg_grip_selection_from_transition(
        transition,
        predecessor_tick=40,
    ) is None


def test_source_reflex_without_internal_thought_cannot_select_a_book() -> None:
    transition = deepcopy(_transition())
    transition["causal_cross_context_use"]["causal_thought_transitions"] = ()

    assert production._gutenberg_grip_selection_from_transition(
        transition,
        predecessor_tick=40,
    ) is None
