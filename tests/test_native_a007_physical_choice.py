from __future__ import annotations

from copy import deepcopy

from dsf_ai_service import native_production_app as production


FORMATION = "01" * 16
ORDERING = "02" * 16
POSITIVE_MOTOR = "03" * 16
NEGATIVE_MOTOR = "04" * 16
FOREGONE = "05" * 16


def _transfer(sender: str, sender_layer: int, receiver: str, receiver_layer: int):
    return {
        "sender_lineage": sender,
        "sender_layer": sender_layer,
        "receiver_lineage": receiver,
        "receiver_layer": receiver_layer,
        "parallel_ordinal": 0,
        "transferred_whole_carriers": 3,
    }


def _transition() -> dict[str, object]:
    reached = (ORDERING, 11, 0, POSITIVE_MOTOR, 12, 0, 0, 3)
    foregone = (ORDERING, 11, 0, FOREGONE, 12, 2, 0, 0)
    transition = {
        "organism_tick": 12,
        "state_sha256": "10" * 32,
        "physical_frontier_routes": (reached,),
        "preceding_distinct_physical_frontier_routes": (foregone,),
        "reached_and_foregone_physical_frontier_routes": (reached, foregone),
        "motor_unit_recruitments": (
            (
                POSITIVE_MOTOR,
                0,
                7,
                ((ORDERING, 11, POSITIVE_MOTOR, 12, 0, 3),),
                (),
            ),
            (
                NEGATIVE_MOTOR,
                1,
                2,
                ((ORDERING, 11, NEGATIVE_MOTOR, 12, 0, 3),),
                (),
            ),
        ),
        "causal_cross_context_use": {
            "origin_kind": "retained_formation",
            "formation_receipt_sha256": "11" * 32,
            "motor_unit_recruitment": {"motor_lineage": POSITIVE_MOTOR},
        },
        "motor_action": {
            "causal_intent_receipt_sha256": "12" * 32,
            "signed_yaw_millidegrees": 5,
            "prepared_recruitments": (
                {
                    "motor_lineage": POSITIVE_MOTOR,
                    "motor_topology_index": 0,
                    "outward_elementary_carriers": 7,
                    "preparation_transfers": (
                        _transfer(ORDERING, 11, POSITIVE_MOTOR, 12),
                    ),
                },
                {
                    "motor_lineage": NEGATIVE_MOTOR,
                    "motor_topology_index": 1,
                    "outward_elementary_carriers": 2,
                    "preparation_transfers": (
                        _transfer(ORDERING, 11, NEGATIVE_MOTOR, 12),
                    ),
                },
            ),
        },
    }
    transition["attention_motor_binding"] = (
        production._attention_motor_binding_from_hop(transition)
    )
    return transition


def test_attention_enters_opposed_motor_settlement_and_prepares_one_intent() -> None:
    evidence = production._physical_choice_evidence_from_transition(_transition())

    assert evidence is not None
    assert evidence["matched_attention_route_count"] == 1
    assert evidence["positive_antagonist_carriers"] == 7
    assert evidence["negative_antagonist_carriers"] == 2
    assert evidence["settled_signed_yaw_millidegrees"] == 5
    assert evidence["prepared_intent_count"] == 1
    assert evidence["internal_cause_motor_lineage"] == POSITIVE_MOTOR


def test_completed_transaction_supplies_the_later_route_comparison() -> None:
    earlier_hop = _transition()
    earlier_hop["preceding_distinct_physical_frontier_routes"] = ()
    earlier_hop["attention_motor_binding"] = None

    assert production._attention_motor_binding_from_hop(earlier_hop) is None

    completed_transaction = deepcopy(earlier_hop)
    completed_transaction["preceding_distinct_physical_frontier_routes"] = (
        (FOREGONE, 12, 2, ORDERING, 11, 0, 0, 2),
    )
    completed_transaction["attention_motor_binding"] = (
        production._advance_bounded_attention_motor_binding(
            None,
            completed_transaction,
        )
    )

    evidence = production._physical_choice_evidence_from_transition(
        completed_transaction
    )

    assert evidence is not None
    assert evidence["matched_attention_route_count"] == 1


def test_completed_transaction_preserves_earlier_motor_preparation() -> None:
    earlier_hop = _transition()
    motor_unit_recruitments = earlier_hop["motor_unit_recruitments"]
    completed_transaction = deepcopy(earlier_hop)
    completed_transaction["motor_unit_recruitments"] = ()
    completed_transaction["attention_motor_binding"] = None

    assert (
        production._attention_motor_binding_from_hop(completed_transaction)
        is None
    )

    completed_transaction["attention_motor_binding"] = (
        production._completed_transaction_attention_motor_binding(
            None,
            completed_transaction,
            motor_unit_recruitments,
        )
    )
    evidence = production._physical_choice_evidence_from_transition(
        completed_transaction
    )

    assert evidence is not None
    assert evidence["matched_attention_route_count"] == 1


def test_coexisting_attention_without_motor_contact_is_not_choice() -> None:
    transition = _transition()
    transition["reached_and_foregone_physical_frontier_routes"] = (
        (ORDERING, 11, 0, FOREGONE, 12, 2, 0, 3),
        (ORDERING, 11, 0, "06" * 16, 12, 3, 0, 0),
    )
    transition["attention_motor_binding"] = (
        production._attention_motor_binding_from_hop(transition)
    )

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_exact_antagonist_cancellation_is_not_one_prepared_continuation() -> None:
    transition = deepcopy(_transition())
    transition["motor_action"]["prepared_recruitments"][1][
        "outward_elementary_carriers"
    ] = 7
    transition["motor_action"]["signed_yaw_millidegrees"] = 0

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_choice_projection_has_no_selector_or_semantic_authority(monkeypatch) -> None:
    evidence = production._physical_choice_evidence_from_transition(_transition())
    monkeypatch.setattr(production, "_last_tested_physical_choice_evidence", evidence)

    record = production._physical_choice_record()

    assert record["available"] is True
    assert record["authored_goal_authority"] is False
    assert record["python_cognition_authority"] is False
    assert record["random_selector_authority"] is False
    assert record["score_selector_authority"] is False
    assert record["semantic_command_authority"] is False
