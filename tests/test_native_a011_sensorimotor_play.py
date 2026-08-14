"""A-011 bounded observation of genuine sensorimotor play."""

from __future__ import annotations

from dsf_ai_service import native_production_app as production


FORMATION = "f" * 64
SHARED_AFFECTIVE_LINEAGE = "02" * 16
ORGANIC_RELATION = "9" * 64


def _transition(
    *,
    action_receipt: str,
    origin_tick: int,
    yaw: int,
    world_revision: int,
) -> tuple[dict[str, object], dict[str, object]]:
    motor_tick = origin_tick + 2
    consequence_tick = motor_tick + 1
    consequence = {
        "externally_perturbed_body_receptor_count": 1,
        "successor_organism_tick": consequence_tick,
        "successor_state_sha256": "d" * 64,
        "vestibular_tick_count": 1,
    }
    causal_action = {
        "causal_intent_receipt_sha256": action_receipt,
        "command_sha256": "c" * 64,
        "observed_world_revision": world_revision,
        "world_state_after_sha256": "b" * 64,
        "world_state_before_sha256": "a" * 64,
    }
    causal = {
        "action": causal_action,
        "directed_physical_transfers": (("03" * 16, "04" * 16, 0, 3),),
        "formation_receipt_sha256": FORMATION,
        "internal_cue_lineages": ("01" * 16,),
        "motor_organism_tick": motor_tick,
        "motor_unit_recruitment": {
            "motor_layer": 12,
            "motor_lineage": "04" * 16,
            "motor_topology_index": 1,
            "outward_elementary_carriers": abs(yaw),
        },
        "origin_kind": "retained_formation",
        "origin_lineages": ("01" * 16,),
        "origin_organism_tick": origin_tick,
        "recurrence_organism_tick": origin_tick,
        "sensed_consequence": consequence,
    }
    transition = {
        "affective_balance_trajectories": (
            (
                SHARED_AFFECTIVE_LINEAGE,
                10,
                4,
                (origin_tick - 1, ("07" * 16, SHARED_AFFECTIVE_LINEAGE, 0, 3)),
                (origin_tick - 1, (SHARED_AFFECTIVE_LINEAGE, "08" * 16, 0, 2)),
                (
                    origin_tick,
                    -5,
                    -3,
                    -4,
                    2,
                    2,
                    0,
                    (11, 2),
                    (13, 2),
                    (1, 1),
                ),
            ),
        ),
        "causal_cross_context_use": causal,
        "dissipation_capacity_energy_zeptojoules": (100, 1),
        "hop_count": 4,
        "organic_mosaic_relations": (
            {
                "active_physical_bonds": (
                    ("07" * 16, SHARED_AFFECTIVE_LINEAGE, 0),
                ),
                "formation_receipts": (FORMATION, "e" * 64),
                "organism_tick": origin_tick,
                "structural_relation_sha256": ORGANIC_RELATION,
            },
        ),
        "motor_action": {
            **causal_action,
            "internally_reassembled_formation_motor_path": causal,
            "moved": True,
            "signed_yaw_millidegrees": yaw,
        },
        "organism_tick": consequence_tick,
        "state_sha256": "d" * 64,
        "totals": {
            "energy_exhausted_interval_count": 0,
            "rest_drained_dissipation_quanta": 7,
            "unmet_dissipation_quanta": 0,
        },
    }
    choice = {
        "causal_intent_receipt_sha256": action_receipt,
        "formation_receipt_sha256": FORMATION,
        "organism_tick": consequence_tick,
        "settled_signed_yaw_millidegrees": yaw,
        "state_sha256": "d" * 64,
    }
    return transition, choice


def test_two_varied_retained_formation_actions_form_one_bounded_play_witness() -> None:
    first, first_choice = _transition(
        action_receipt="1" * 64,
        origin_tick=100,
        yaw=-58,
        world_revision=10,
    )
    candidate, completed = production._advance_bounded_sensorimotor_play_evidence(
        None,
        None,
        first,
        first_choice,
        "continuous-environment:first",
    )
    assert candidate is not None
    assert completed is None

    duplicate_candidate, duplicate_completed = (
        production._advance_bounded_sensorimotor_play_evidence(
            candidate,
            None,
            first,
            first_choice,
            "continuous-environment:first",
        )
    )
    assert duplicate_candidate == candidate
    assert duplicate_completed is None

    second, second_choice = _transition(
        action_receipt="2" * 64,
        origin_tick=114,
        yaw=-40,
        world_revision=11,
    )
    candidate, completed = production._advance_bounded_sensorimotor_play_evidence(
        candidate,
        None,
        second,
        second_choice,
        "continuous-environment:second",
    )

    assert candidate is None
    assert completed is not None
    assert completed["formation_receipt_sha256"] == FORMATION
    assert completed["movement_ceased_before_return"] is True
    assert completed["varied_displacement"] is True
    assert completed["return_gap_organism_ticks"] == 11
    assert completed["first_episode"]["signed_yaw_millidegrees"] == -58
    assert completed["return_episode"]["signed_yaw_millidegrees"] == -40
    assert completed["first_episode"]["affective_body_participation"][
        "affective_neuron_lineage"
    ] == SHARED_AFFECTIVE_LINEAGE
    assert completed["return_episode"]["affective_body_participation"][
        "localized_gradient_settlement_ordinal"
    ] == 114
    assert completed["return_episode"]["affective_body_participation"][
        "organic_relation_receipt_sha256"
    ] == ORGANIC_RELATION
    assert completed["first_episode"]["metabolic_overload_exclusion"][
        "unmet_dissipation_quanta"
    ] == 0
    assert completed["return_episode"]["metabolic_overload_exclusion"][
        "energy_exhausted_interval_count"
    ] == 0
    assert len(completed["evidence_receipt_sha256"]) == 64


def test_external_or_unvaried_activity_cannot_be_reported_as_play() -> None:
    first, first_choice = _transition(
        action_receipt="3" * 64,
        origin_tick=200,
        yaw=25,
        world_revision=20,
    )
    assert production._advance_bounded_sensorimotor_play_evidence(
        None,
        None,
        first,
        first_choice,
        "tutor-card:A",
    ) == (None, None)

    candidate, _ = production._advance_bounded_sensorimotor_play_evidence(
        None,
        None,
        first,
        first_choice,
        "continuous-environment:first",
    )
    repeated, repeated_choice = _transition(
        action_receipt="4" * 64,
        origin_tick=214,
        yaw=25,
        world_revision=21,
    )
    candidate_after, completed = production._advance_bounded_sensorimotor_play_evidence(
        candidate,
        None,
        repeated,
        repeated_choice,
        "continuous-environment:second",
    )
    assert candidate_after == candidate
    assert completed is None


def test_public_record_does_not_inflate_play_into_fun_or_laughter(monkeypatch) -> None:
    first, first_choice = _transition(
        action_receipt="5" * 64,
        origin_tick=300,
        yaw=-31,
        world_revision=30,
    )
    candidate, _ = production._advance_bounded_sensorimotor_play_evidence(
        None,
        None,
        first,
        first_choice,
        "continuous-environment:first",
    )
    second, second_choice = _transition(
        action_receipt="6" * 64,
        origin_tick=314,
        yaw=-19,
        world_revision=31,
    )
    _, completed = production._advance_bounded_sensorimotor_play_evidence(
        candidate,
        None,
        second,
        second_choice,
        "continuous-environment:second",
    )
    monkeypatch.setattr(production, "_last_sensorimotor_play_evidence", completed)

    observed = production._sensorimotor_play_record()

    assert observed["available"] is True
    assert observed["status"] == "sensorimotor_play_observed"
    assert observed["endogenous_initiation"] is True
    assert observed["voluntary_return"] is True
    assert observed["affective_engagement"]["available"] is True
    assert observed["affective_engagement"]["named_emotion_authority"] is False
    assert observed["overload_exclusion"]["available"] is True
    assert observed["distress_exclusion"]["available"] is False
    assert observed["fun"]["available"] is False
    assert observed["social_joy"]["available"] is False
    assert observed["laughter"]["available"] is False
    assert observed["python_action_authority"] is False
    assert observed["reward_authority"] is False


def test_unshared_affective_trajectory_cannot_be_bound_to_play() -> None:
    transition, choice = _transition(
        action_receipt="7" * 64,
        origin_tick=400,
        yaw=22,
        world_revision=40,
    )
    trajectory = list(transition["affective_balance_trajectories"][0])
    trajectory[0] = "09" * 16
    transition["affective_balance_trajectories"] = (tuple(trajectory),)

    episode = production._sensorimotor_play_episode_from_transition(
        transition,
        choice,
        "continuous-environment:unshared",
    )

    assert episode is not None
    assert "affective_body_participation" not in episode


def test_unmet_dissipation_refuses_overload_exclusion() -> None:
    transition, choice = _transition(
        action_receipt="8" * 64,
        origin_tick=500,
        yaw=18,
        world_revision=50,
    )
    transition["totals"]["unmet_dissipation_quanta"] = 1

    episode = production._sensorimotor_play_episode_from_transition(
        transition,
        choice,
        "continuous-environment:overloaded",
    )

    assert episode is not None
    assert "metabolic_overload_exclusion" not in episode
