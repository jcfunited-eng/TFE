"""A-011 bounded observation of genuine sensorimotor play."""

from __future__ import annotations

from dsf_ai_service import native_production_app as production


FORMATION = "f" * 64


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
        "directed_physical_transfers": (("01" * 16, "02" * 16, 0, 3),),
        "formation_receipt_sha256": FORMATION,
        "internal_cue_lineages": ("01" * 16,),
        "motor_organism_tick": motor_tick,
        "motor_unit_recruitment": {
            "motor_layer": 12,
            "motor_lineage": "02" * 16,
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
        "causal_cross_context_use": causal,
        "motor_action": {
            **causal_action,
            "internally_reassembled_formation_motor_path": causal,
            "moved": True,
            "signed_yaw_millidegrees": yaw,
        },
        "organism_tick": consequence_tick,
        "state_sha256": "d" * 64,
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
    assert observed["fun"]["available"] is False
    assert observed["social_joy"]["available"] is False
    assert observed["laughter"]["available"] is False
    assert observed["python_action_authority"] is False
    assert observed["reward_authority"] is False
