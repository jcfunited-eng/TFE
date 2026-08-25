from __future__ import annotations

from copy import deepcopy

from dsf_ai_service import native_production_app as production


FORMATION = "01" * 16
ORDERING = "02" * 16
FLEXOR_MOTOR = "03" * 16
EXTENSOR_MOTOR = "04" * 16
FOREGONE = "05" * 16
AXIS = "right_elbow_flexion"


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
    """One completed transition in the living articulated-body action schema.

    The retired yaw body's ``signed_yaw_millidegrees`` and even/odd topology
    partition are deliberately absent: the antagonist identity lives on each
    terminal's declared axis and direction, and the settled record follows the
    body's own law — intent = toward_maximum - toward_minimum, applied =
    min(|intent|, remaining travel), remainder stalled.
    """

    reached = (ORDERING, 11, 0, FLEXOR_MOTOR, 12, 0, 0, 3)
    foregone = (ORDERING, 11, 0, FOREGONE, 12, 2, 0, 0)
    transition = {
        "organism_tick": 12,
        "state_sha256": "10" * 32,
        "physical_frontier_routes": (reached,),
        "preceding_distinct_physical_frontier_routes": (foregone,),
        "reached_and_foregone_physical_frontier_routes": (reached, foregone),
        "motor_unit_recruitments": (
            (
                FLEXOR_MOTOR,
                0,
                7,
                ((ORDERING, 11, FLEXOR_MOTOR, 12, 0, 3),),
                (),
            ),
            (
                EXTENSOR_MOTOR,
                1,
                2,
                ((ORDERING, 11, EXTENSOR_MOTOR, 12, 0, 3),),
                (),
            ),
        ),
        "causal_cross_context_use": {
            "origin_kind": "retained_formation",
            "formation_receipt_sha256": "11" * 32,
            "motor_unit_recruitment": {"motor_lineage": FLEXOR_MOTOR},
        },
        "motor_action": {
            "causal_intent_receipt_sha256": "12" * 32,
            "prepared_recruitments": (
                {
                    "motor_lineage": FLEXOR_MOTOR,
                    "motor_topology_index": 0,
                    "outward_elementary_carriers": 7,
                    "preparation_transfers": (
                        _transfer(ORDERING, 11, FLEXOR_MOTOR, 12),
                    ),
                },
                {
                    "motor_lineage": EXTENSOR_MOTOR,
                    "motor_topology_index": 1,
                    "outward_elementary_carriers": 2,
                    "preparation_transfers": (
                        _transfer(ORDERING, 11, EXTENSOR_MOTOR, 12),
                    ),
                },
            ),
            "body_effector_bindings": (
                {
                    "source_tick": 11,
                    "motor_lineage": FLEXOR_MOTOR,
                    "axis": AXIS,
                    "direction": "toward_minimum",
                    "outward_elementary_carriers": 7,
                },
                {
                    "source_tick": 11,
                    "motor_lineage": EXTENSOR_MOTOR,
                    "axis": AXIS,
                    "direction": "toward_maximum",
                    "outward_elementary_carriers": 2,
                },
            ),
            "articulated_body_consequences": (
                {
                    "source_tick": 11,
                    "axis": AXIS,
                    "unit": "millidegrees",
                    "predecessor_position": 40_000,
                    "successor_position": 39_995,
                    "signed_displacement": -5,
                    "toward_minimum_carriers": 7,
                    "toward_maximum_carriers": 2,
                    "opposed_carriers_per_terminal": 2,
                    "applied_displacement_quanta": 5,
                    "stalled_carriers": 0,
                },
            ),
        },
    }
    transition["attention_motor_binding"] = (
        production._attention_motor_binding_from_hop(transition)
    )
    return transition


def test_attention_enters_opposed_antagonist_settlement_and_applies_one_intent() -> None:
    evidence = production._physical_choice_evidence_from_transition(_transition())

    assert evidence is not None
    assert evidence["matched_attention_route_count"] == 1
    assert evidence["axis"] == AXIS
    assert evidence["toward_minimum_antagonist_carriers"] == 7
    assert evidence["toward_maximum_antagonist_carriers"] == 2
    assert evidence["settled_signed_intent_carriers"] == -5
    assert evidence["applied_signed_displacement_quanta"] == -5
    assert evidence["stalled_carriers"] == 0
    assert evidence["prepared_intent_count"] == 1
    assert evidence["internal_cause_motor_lineage"] == FLEXOR_MOTOR
    assert "settled_signed_yaw_millidegrees" not in evidence


def test_retired_yaw_law_evidence_cannot_pass() -> None:
    """The removed yaw body's action shape must never witness a choice again."""

    transition = _transition()
    transition["motor_action"] = {
        "causal_intent_receipt_sha256": "12" * 32,
        "signed_yaw_millidegrees": 5,
        "prepared_recruitments": transition["motor_action"][
            "prepared_recruitments"
        ],
    }

    assert production._physical_choice_evidence_from_transition(transition) is None


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


def test_exact_antagonist_cancellation_is_not_one_applied_continuation() -> None:
    transition = deepcopy(_transition())
    consequence = dict(transition["motor_action"]["articulated_body_consequences"][0])
    consequence["toward_maximum_carriers"] = 7
    consequence["signed_displacement"] = 0
    consequence["applied_displacement_quanta"] = 0
    consequence["stalled_carriers"] = 0
    consequence["opposed_carriers_per_terminal"] = 7
    consequence["successor_position"] = consequence["predecessor_position"]
    transition["motor_action"]["articulated_body_consequences"] = (consequence,)

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_fully_stalled_intent_is_not_an_applied_choice() -> None:
    """A settled intent absorbed entirely by the joint's stop moved nothing."""

    transition = deepcopy(_transition())
    consequence = dict(transition["motor_action"]["articulated_body_consequences"][0])
    consequence["signed_displacement"] = 0
    consequence["applied_displacement_quanta"] = 0
    consequence["stalled_carriers"] = 5
    consequence["successor_position"] = consequence["predecessor_position"]
    transition["motor_action"]["articulated_body_consequences"] = (consequence,)

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_settlement_must_decompose_by_the_bodys_own_law() -> None:
    """|applied| + stalled must equal |intent| exactly, or the record lies."""

    transition = deepcopy(_transition())
    consequence = dict(transition["motor_action"]["articulated_body_consequences"][0])
    consequence["signed_displacement"] = -3
    consequence["applied_displacement_quanta"] = 3
    consequence["stalled_carriers"] = 0
    transition["motor_action"]["articulated_body_consequences"] = (consequence,)

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_severed_formation_origin_removes_the_witness() -> None:
    transition = deepcopy(_transition())
    transition["causal_cross_context_use"]["origin_kind"] = "affective_gradient"

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_severed_antagonist_pairing_removes_the_witness() -> None:
    """With only one direction bound on the causal axis there is no opposition."""

    transition = deepcopy(_transition())
    consequence = dict(transition["motor_action"]["articulated_body_consequences"][0])
    consequence["toward_maximum_carriers"] = 0
    consequence["signed_displacement"] = -7
    consequence["applied_displacement_quanta"] = 7
    transition["motor_action"]["articulated_body_consequences"] = (consequence,)

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_severed_antagonist_binding_alone_removes_the_witness() -> None:
    """Removing one antagonist's BINDING severs the witness even though the
    consequence record still reports both pools — the settled totals can no
    longer be accounted for by the discharges in evidence."""

    transition = deepcopy(_transition())
    transition["motor_action"]["body_effector_bindings"] = (
        transition["motor_action"]["body_effector_bindings"][0],
    )

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_severed_antagonist_recruitment_alone_removes_the_witness() -> None:
    """Removing one antagonist's RECRUITMENT severs the witness even though
    its binding and the consequence record are left untouched."""

    transition = deepcopy(_transition())
    transition["motor_action"]["prepared_recruitments"] = (
        transition["motor_action"]["prepared_recruitments"][0],
    )

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_binding_and_consequence_carrier_mismatch_is_refused() -> None:
    transition = deepcopy(_transition())
    bindings = tuple(
        dict(binding)
        for binding in transition["motor_action"]["body_effector_bindings"]
    )
    bindings[0]["outward_elementary_carriers"] = 6
    transition["motor_action"]["body_effector_bindings"] = bindings

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_corrupted_applied_displacement_quanta_is_refused() -> None:
    transition = deepcopy(_transition())
    consequence = dict(transition["motor_action"]["articulated_body_consequences"][0])
    consequence["applied_displacement_quanta"] = 4
    transition["motor_action"]["articulated_body_consequences"] = (consequence,)

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_corrupted_position_difference_is_refused() -> None:
    transition = deepcopy(_transition())
    consequence = dict(transition["motor_action"]["articulated_body_consequences"][0])
    consequence["successor_position"] = consequence["predecessor_position"] - 4
    transition["motor_action"]["articulated_body_consequences"] = (consequence,)

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_corrupted_opposed_carrier_count_is_refused() -> None:
    transition = deepcopy(_transition())
    consequence = dict(transition["motor_action"]["articulated_body_consequences"][0])
    consequence["opposed_carriers_per_terminal"] = 3
    transition["motor_action"]["articulated_body_consequences"] = (consequence,)

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_binding_from_a_different_tick_cannot_account_for_the_settlement() -> None:
    transition = deepcopy(_transition())
    bindings = tuple(
        dict(binding)
        for binding in transition["motor_action"]["body_effector_bindings"]
    )
    bindings[1]["source_tick"] = 10
    transition["motor_action"]["body_effector_bindings"] = bindings

    assert production._physical_choice_evidence_from_transition(transition) is None


def test_causal_lineage_absent_from_the_settlement_tick_is_not_the_cause() -> None:
    """A consequence whose tick does not carry the causal motor's own
    discharge is not the caused settlement, even on the causal axis."""

    transition = deepcopy(_transition())
    bindings = tuple(
        dict(binding)
        for binding in transition["motor_action"]["body_effector_bindings"]
    )
    bindings[0]["source_tick"] = 10
    consequence = dict(transition["motor_action"]["articulated_body_consequences"][0])
    consequence["toward_minimum_carriers"] = 0
    consequence["toward_maximum_carriers"] = 2
    consequence["signed_displacement"] = 2
    consequence["applied_displacement_quanta"] = 2
    consequence["opposed_carriers_per_terminal"] = 0
    consequence["successor_position"] = consequence["predecessor_position"] + 2
    transition["motor_action"]["body_effector_bindings"] = bindings
    transition["motor_action"]["articulated_body_consequences"] = (consequence,)

    assert production._physical_choice_evidence_from_transition(transition) is None


def _interval(predecessor_tick: int, recruitments) -> dict[str, object]:
    return {
        "predecessor_organism_tick": predecessor_tick,
        "organism_tick": predecessor_tick + 1,
        "motor_unit_recruitments": tuple(recruitments),
    }


def test_binding_ticks_come_from_each_settling_interval() -> None:
    """The single-interval case: the binding must carry the PREDECESSOR tick
    (matching the native consequence record), never the hop's final tick."""

    hop = {
        "organism_tick": 12,
        "body_effector_bindings": (
            (FLEXOR_MOTOR, AXIS, "toward_minimum", 7),
        ),
        "causal_interval_evidence": (
            _interval(11, ((FLEXOR_MOTOR, 0, 7, ()),)),
        ),
    }

    assert production._tick_attributed_effector_bindings(hop) == (
        (11, FLEXOR_MOTOR, AXIS, "toward_minimum", 7),
    )


def test_multi_interval_discharges_keep_their_own_ticks() -> None:
    hop = {
        "organism_tick": 14,
        "body_effector_bindings": (
            (FLEXOR_MOTOR, AXIS, "toward_minimum", 7),
            (EXTENSOR_MOTOR, AXIS, "toward_maximum", 2),
        ),
        "causal_interval_evidence": (
            _interval(11, ((FLEXOR_MOTOR, 0, 7, ()),)),
            _interval(12, ()),
            _interval(13, ((EXTENSOR_MOTOR, 1, 2, ()),)),
        ),
    }

    assert production._tick_attributed_effector_bindings(hop) == (
        (11, FLEXOR_MOTOR, AXIS, "toward_minimum", 7),
        (13, EXTENSOR_MOTOR, AXIS, "toward_maximum", 2),
    )


def test_discharge_without_a_terminal_is_refused() -> None:
    hop = {
        "organism_tick": 12,
        "body_effector_bindings": (
            (FLEXOR_MOTOR, AXIS, "toward_minimum", 7),
        ),
        "causal_interval_evidence": (
            _interval(11, ((EXTENSOR_MOTOR, 1, 2, ()),)),
        ),
    }

    try:
        production._tick_attributed_effector_bindings(hop)
    except RuntimeError as error:
        assert "lost its effector terminal" in str(error)
    else:
        raise AssertionError("unknown discharge lineage must refuse")


def test_bindings_without_interval_evidence_are_refused() -> None:
    hop = {
        "organism_tick": 12,
        "body_effector_bindings": (
            (FLEXOR_MOTOR, AXIS, "toward_minimum", 7),
        ),
        "causal_interval_evidence": (),
    }

    try:
        production._tick_attributed_effector_bindings(hop)
    except RuntimeError as error:
        assert "lost their causal interval evidence" in str(error)
    else:
        raise AssertionError("tickless bindings must refuse, never guess")


def test_shadowed_attention_binding_is_counted_not_witnessed(monkeypatch) -> None:
    monkeypatch.setattr(production, "_choice_attention_binding_miss_count", 0)
    transition = deepcopy(_transition())
    transition["attention_motor_binding"] = {
        "attention": transition["attention_motor_binding"]["attention"],
        "matched_attention_route_count": 1,
        "matched_motor_lineages": (EXTENSOR_MOTOR,),
        "organism_tick": 12,
    }

    assert production._physical_choice_evidence_from_transition(transition) is None
    assert production._choice_attention_binding_miss_count == 1


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
    assert isinstance(record["attention_binding_miss_count"], int)
