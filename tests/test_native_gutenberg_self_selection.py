"""L-009 source selection belongs only to Guala's physical grip action."""

from __future__ import annotations

from copy import deepcopy

from dsf_ai_service import native_production_app as production


MOTOR = "12" * 16
FORMATION = "34" * 32


def _transition() -> dict[str, object]:
    return {
        "externally_reassembled_formation_causal_use": {
            "origin_kind": "externally_reassembled_retained_formation",
            "formation_receipt_sha256": FORMATION,
            "reassembly_organism_tick": 41,
            "motor_organism_tick": 43,
            "motor_unit_recruitment": {"motor_lineage": MOTOR},
        },
        "motor_action": {
            "body_effector_bindings": (
                {
                    "source_tick": 43,
                    "motor_lineage": MOTOR,
                    "axis": "left_grip_aperture",
                    "direction": "toward_minimum",
                    "outward_elementary_carriers": 5,
                },
            ),
            "articulated_body_consequences": (
                {
                    "source_tick": 43,
                    "axis": "left_grip_aperture",
                    "signed_displacement": -5,
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
        "grip_closing_displacement": -5,
        "motor_organism_tick": 43,
        "reassembly_organism_tick": 41,
        "selection_authority": "source-caused-native-grip-closure",
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
