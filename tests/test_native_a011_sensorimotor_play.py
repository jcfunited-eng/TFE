"""A-011 bounded observation of genuine sensorimotor play."""

from __future__ import annotations

import json

from dsf_ai_service import native_production_app as production
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)


FORMATION = "f" * 64
SHARED_AFFECTIVE_LINEAGE = "02" * 16
BODY_RECEPTOR_LINEAGE = "05" * 16


def _plasticity(ordinal: int) -> tuple[object, ...]:
    return (
        ordinal,
        "2",
        "2",
        (1, 8),
        (7, 8),
        (0, 1),
        (4, 3),
        (4, 3),
        ((1, 1), (0, 1), (0, 1)),
        ((7, 8), (1, 8), (0, 1)),
    )


def _transition(
    *,
    action_receipt: str,
    origin_tick: int,
    yaw: int,
    world_revision: int,
    participant_action_receipt: str | None = None,
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
        "world_state_after_sha256": f"{world_revision + 1:064x}",
        "world_state_before_sha256": f"{world_revision:064x}",
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
    affective_trajectory = (
        SHARED_AFFECTIVE_LINEAGE,
        10,
        4,
        (origin_tick, ("07" * 16, SHARED_AFFECTIVE_LINEAGE, 0, 3)),
        (origin_tick, (SHARED_AFFECTIVE_LINEAGE, "08" * 16, 0, 2)),
        (
            origin_tick + 1,
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
        _plasticity(origin_tick),
    )
    transition = {
        "affective_balance_trajectories": (affective_trajectory,),
        "affective_motor_causal_use": {
            "action": causal_action,
            "affective_neuron_lineage": SHARED_AFFECTIVE_LINEAGE,
            "affective_trajectory_receipt_sha256": production._receipt(
                affective_trajectory
            ),
            "directed_physical_transfers": (
                (SHARED_AFFECTIVE_LINEAGE, "03" * 16, 0, 4),
                ("03" * 16, "04" * 16, 0, 3),
            ),
            "changed_contact_channel_state": {
                "change_organism_tick": origin_tick,
                "contact_cognitive_ordinal": origin_tick,
                "left_lineage": SHARED_AFFECTIVE_LINEAGE,
                "right_lineage": "03" * 16,
                "parallel_ordinal": 0,
                "predecessor_state": (50, (0, 1), (1, 1)),
                "successor_state": (51, (0, 1), (51, 50)),
            },
            "localized_gradient_settlement_organism_tick": origin_tick + 1,
            "localized_plasticity_settlement_organism_tick": origin_tick,
            "motor_organism_tick": motor_tick,
            "motor_unit_recruitment": {
                "motor_layer": 12,
                "motor_lineage": "04" * 16,
                "motor_topology_index": 1,
                "outward_elementary_carriers": abs(yaw),
            },
            "origin_kind": "affective_gradient",
            "origin_lineages": (SHARED_AFFECTIVE_LINEAGE,),
            "origin_organism_tick": origin_tick + 1,
        },
        "causal_cross_context_use": causal,
        "dissipation_capacity_energy_zeptojoules": (100, 1),
        "hop_count": 4,
        "localized_metabolic_strain_evaluated_body_receptor_lineages": (
            BODY_RECEPTOR_LINEAGE,
        ),
        "localized_metabolic_strain": (),
        "organic_mosaic_relations": (),
        "motor_action": {
            **causal_action,
            "internally_reassembled_formation_motor_path": causal,
            "moved": True,
            "signed_yaw_millidegrees": yaw,
        },
        "organism_tick": consequence_tick,
        "state_sha256": "d" * 64,
        "unmet_dissipation_quanta": 0,
        "totals": {
            "energy_exhausted_interval_count": 0,
            "rest_drained_dissipation_quanta": 7,
        },
    }
    if participant_action_receipt is not None:
        transition["participant_sensory_causal_use"] = {
            "action": causal_action,
            "directed_physical_transfers": (
                ("09" * 16, "03" * 16, 0, 5),
                ("03" * 16, "04" * 16, 0, 3),
            ),
            "motor_organism_tick": motor_tick,
            "motor_unit_recruitment": {
                "motor_layer": 12,
                "motor_lineage": "04" * 16,
                "motor_topology_index": 1,
                "outward_elementary_carriers": abs(yaw),
            },
            "origin_kind": "external_participant_sensory",
            "origin_lineages": ("09" * 16,),
            "origin_organism_tick": origin_tick - 1,
            "participant_action_causal_intent_receipt_sha256": (
                participant_action_receipt
            ),
            "perturbed_receptor_lineages": ("09" * 16,),
            "receptor_settlement_organism_tick": origin_tick - 1,
            "sensed_consequence": consequence,
        }
    choice = {
        "causal_intent_receipt_sha256": action_receipt,
        "formation_receipt_sha256": FORMATION,
        "organism_tick": consequence_tick,
        "settled_signed_yaw_millidegrees": yaw,
        "state_sha256": "d" * 64,
    }
    return transition, choice


def _accepted_external_intake(*_args, **_kwargs) -> dict[str, object]:
    return {
        "accepted": True,
        "hop_count": 1,
        "persisted": {
            "organism_tick": 1,
            "state_sha256": "7" * 64,
        },
    }


def _with_articulation(
    transition: dict[str, object],
    *,
    pressure_sha256: str,
) -> dict[str, object]:
    motor_lineage = transition["causal_cross_context_use"][
        "motor_unit_recruitment"
    ]["motor_lineage"]
    transition["motor_action"]["sensory_consequence"] = {
        "visual": {"changed": 0, "transported": 27},
    }
    transition["articulation"] = {
        "applied_motor_quanta": 8,
        "articulatory_body_nonquiescent_port_count": 4,
        "articulatory_body_perturbed_neuron_count": 12,
        "articulatory_body_port_count": 4,
        "glottal_open_samples_at_apex": 144,
        "layer_13_recruitment_count": 1,
        "mouth_area_square_millimetres_at_apex": 305,
        "peak_breath_flow_pcm": 4000,
        "perioral_area_displacement_square_millimetres": 40,
        "pressure_sample_count": 16000,
        "pressure_sha256": pressure_sha256,
        "recruitments": (
            (
                "0a" * 16,
                0,
                8,
                ((motor_lineage, 12, "0a" * 16, 13, 0, 4),),
            ),
        ),
        "self_hearing_hop_count": 4,
        "self_hearing_transitioned_neuron_count": 1192,
    }
    return transition


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
    ] == 115
    assert len(
        completed["return_episode"]["affective_body_participation"][
            "whole_episode_binding_receipt_sha256"
        ]
    ) == 64
    assert completed["first_episode"]["metabolic_overload_exclusion"][
        "unmet_dissipation_quanta"
    ] == 0
    assert completed["return_episode"]["metabolic_overload_exclusion"][
        "energy_exhausted_interval_count"
    ] == 0
    assert completed["first_episode"]["localized_metabolic_strain"][
        "localized_nonzero_strain_count"
    ] == 0
    assert len(completed["evidence_receipt_sha256"]) == 64


def test_exact_other_guala_other_guala_chain_proves_reciprocal_social_play(
    monkeypatch,
) -> None:
    invitation_receipt = "1" * 64
    return_receipt = "3" * 64
    first, first_choice = _transition(
        action_receipt="a" * 64,
        origin_tick=800,
        yaw=-31,
        world_revision=80,
        participant_action_receipt=invitation_receipt,
    )
    second, second_choice = _transition(
        action_receipt="b" * 64,
        origin_tick=814,
        yaw=-17,
        world_revision=82,
        participant_action_receipt=return_receipt,
    )
    return_formation = "f" * 64
    second["causal_cross_context_use"]["formation_receipt_sha256"] = (
        return_formation
    )
    second_choice["formation_receipt_sha256"] = return_formation
    invitation = {
        "actor_body_id": "person-body-1",
        "authority_receipt_sha256": "1" * 64,
        "causal_intent_receipt_sha256": invitation_receipt,
        "evidence_receipt_sha256": "2" * 64,
        "world_revision_after": 80,
        "world_revision_before": 79,
        "world_state_before_sha256": f"{79:064x}",
        "world_state_after_sha256": f"{80:064x}",
    }
    other_return = {
        "actor_body_id": "person-body-1",
        "authority_receipt_sha256": "3" * 64,
        "causal_intent_receipt_sha256": return_receipt,
        "evidence_receipt_sha256": "4" * 64,
        "world_revision_after": 82,
        "world_revision_before": 81,
        "world_state_before_sha256": f"{81:064x}",
        "world_state_after_sha256": f"{82:064x}",
    }

    candidate = production._advance_social_play_on_other_body_action(
        None,
        invitation,
    )
    candidate, completed = (
        production._advance_bounded_reciprocal_social_play_evidence(
            candidate,
            None,
            first,
            first_choice,
            "external-participant-world-action:first-social-turn",
        )
    )
    assert candidate["stage"] == "awaiting_other_return"
    assert completed is None
    candidate = production._advance_social_play_on_other_body_action(
        candidate,
        other_return,
    )
    assert candidate["stage"] == "awaiting_guala_return"
    candidate, completed = (
        production._advance_bounded_reciprocal_social_play_evidence(
            candidate,
            None,
            second,
            second_choice,
            "external-participant-world-action:return-social-turn",
        )
    )

    assert candidate is None
    assert completed is not None
    assert completed["other_body_id"] == "person-body-1"
    assert completed["first_formation_receipt_sha256"] == FORMATION
    assert completed["return_formation_receipt_sha256"] == return_formation
    assert completed["first_guala_episode"]["signed_yaw_millidegrees"] == -31
    assert completed["return_guala_episode"]["signed_yaw_millidegrees"] == -17
    monkeypatch.setattr(
        production,
        "_last_reciprocal_social_play_evidence",
        completed,
    )
    observed = production._reciprocal_social_joy_section()
    assert observed["available"] is True
    assert observed["status"] == "reciprocal_social_positive_engagement_observed"
    assert observed["named_emotion_authority"] is False
    assert observed["other_participant_enjoyment_authority"] is False


def test_social_play_waits_when_a_guala_episode_predates_the_invitation() -> None:
    transition, choice = _transition(
        action_receipt="c" * 64,
        origin_tick=900,
        yaw=-23,
        world_revision=90,
    )
    invitation = {
        "actor_body_id": "person-body-1",
        "world_revision_after": 91,
        "world_revision_before": 90,
        "world_state_before_sha256": f"{88:064x}",
        "world_state_after_sha256": f"{89:064x}",
    }
    candidate = production._advance_social_play_on_other_body_action(
        None,
        invitation,
    )

    candidate_after, completed = (
        production._advance_bounded_reciprocal_social_play_evidence(
            candidate,
            None,
            transition,
            choice,
            "continuous-environment:unrelated",
        )
    )
    assert candidate_after == candidate
    assert completed is None


def test_social_play_allows_gualas_own_intervening_world_actions() -> None:
    invitation_receipt = "6" * 64
    return_receipt = "7" * 64
    first, first_choice = _transition(
        action_receipt="d" * 64,
        origin_tick=1_000,
        yaw=-23,
        world_revision=102,
        participant_action_receipt=invitation_receipt,
    )
    second, second_choice = _transition(
        action_receipt="e" * 64,
        origin_tick=1_014,
        yaw=-11,
        world_revision=106,
        participant_action_receipt=return_receipt,
    )
    invitation = {
        "actor_body_id": "person-body-1",
        "causal_intent_receipt_sha256": invitation_receipt,
        "world_revision_before": 99,
        "world_revision_after": 100,
        "world_state_before_sha256": f"{99:064x}",
        "world_state_after_sha256": f"{100:064x}",
    }
    other_return = {
        "actor_body_id": "person-body-1",
        "causal_intent_receipt_sha256": return_receipt,
        "world_revision_before": 104,
        "world_revision_after": 105,
        "world_state_before_sha256": f"{104:064x}",
        "world_state_after_sha256": f"{105:064x}",
    }

    candidate = production._advance_social_play_on_other_body_action(
        None,
        invitation,
    )
    candidate, completed = (
        production._advance_bounded_reciprocal_social_play_evidence(
            candidate,
            None,
            first,
            first_choice,
            "continuous-environment:first-response",
        )
    )
    assert candidate["stage"] == "awaiting_other_return"
    assert completed is None
    candidate = production._advance_social_play_on_other_body_action(
        candidate,
        other_return,
    )
    assert candidate["stage"] == "awaiting_guala_return"
    candidate, completed = (
        production._advance_bounded_reciprocal_social_play_evidence(
            candidate,
            None,
            second,
            second_choice,
            "continuous-environment:return-response",
        )
    )

    assert candidate is None
    assert completed is not None
    assert completed["first_guala_episode"]["world_revision"] == 102
    assert completed["return_guala_episode"]["world_revision"] == 106


def test_temporal_proximity_without_participant_circuit_path_is_rejected() -> None:
    transition, choice = _transition(
        action_receipt="8" * 64,
        origin_tick=1_100,
        yaw=-19,
        world_revision=111,
    )
    invitation = {
        "actor_body_id": "person-body-1",
        "causal_intent_receipt_sha256": "9" * 64,
        "world_revision_before": 110,
        "world_revision_after": 111,
    }
    candidate = production._advance_social_play_on_other_body_action(
        None,
        invitation,
    )

    candidate_after, completed = (
        production._advance_bounded_reciprocal_social_play_evidence(
            candidate,
            None,
            transition,
            choice,
            "continuous-environment:temporal-coincidence",
        )
    )

    assert candidate_after == candidate
    assert completed is None


def test_other_participant_moves_only_its_authenticated_world_body(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    monkeypatch.setattr(production, "WORLD_AUTHORIZED", True)
    monkeypatch.setattr(production, "_world_authority", None)
    monkeypatch.setattr(
        production,
        "_reciprocal_social_play_candidate",
        None,
    )
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)
    monkeypatch.setattr(
        production,
        "_perform_admitted_intake_locked",
        _accepted_external_intake,
    )

    response = production.world_other_body_move(
        {
            "heading_millidegrees": 170_000,
            "signed_yaw_millidegrees": -10_000,
            "x_mm": 3_500,
            "y_mm": 7_600,
        }
    )
    value = json.loads(response.body)

    assert response.status_code == 200
    assert value["action"]["actor_body_id"] == "person-body-1"
    assert value["action"]["port_id"] == SECOND_BODY_PORT_ID
    assert value["action"]["world_revision_after"] == 1
    assert value["action"]["world_state_before_sha256"] != value["action"][
        "world_state_after_sha256"
    ]
    assert (tmp_path / production.WORLD_STATE_FILE).is_file()


def test_other_participant_action_physically_changes_gualas_retina(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    monkeypatch.setattr(production, "WORLD_AUTHORIZED", True)
    monkeypatch.setattr(production, "_world_authority", None)
    monkeypatch.setattr(
        production,
        "_reciprocal_social_play_candidate",
        None,
    )
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)
    observed_candidate_stages: list[str | None] = []
    observed_admissions: list[object] = []

    def accepted_with_candidate(*args, **kwargs):
        observed_admissions.append(args[0][0][1])
        observed_candidate_stages.append(
            (production._reciprocal_social_play_candidate or {}).get("stage")
        )
        return _accepted_external_intake(*args, **kwargs)

    monkeypatch.setattr(
        production,
        "_perform_admitted_intake_locked",
        accepted_with_candidate,
    )

    authority = production._world()
    for ordinal, (x, y, heading) in enumerate(
        (
            (3_000, 2_000, 0),
            (2_500, 3_000, 0),
            (2_300, 3_750, 0),
            (2_300, 4_500, 65_000),
        ),
        start=1,
    ):
        before = authority.observation_snapshot()
        moved = authority.execute_port_command(
            port_id=PORT_ID,
            command_payload=encode_command(
                MoveCommand(
                    PoseMM(PositionMM(x, y, 0), heading),
                    200_000,
                )
            ),
            causal_intent_receipt_sha256=f"{ordinal:064x}",
            expected_revision=before.revision,
        )
        assert moved.disposition == "applied"

    response = production.world_other_body_move(
        {
            "heading_millidegrees": 180_000,
            "signed_yaw_millidegrees": 0,
            "x_mm": 3_750,
            "y_mm": 7_600,
        }
    )
    value = json.loads(response.body)

    assert response.status_code == 200
    assert value["social_play_opportunity_reached_vision"] is True
    assert value["action"]["visual_changed_receptor_count"] == 1
    assert production._reciprocal_social_play_candidate is not None
    assert production._reciprocal_social_play_candidate["stage"] == (
        "awaiting_guala_response"
    )
    assert observed_candidate_stages == ["awaiting_guala_response"]
    assert observed_admissions == [[(1, 4)]]


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


def test_public_record_reports_behavioral_fun_without_inflating_joy_or_laughter(
    monkeypatch,
) -> None:
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
    assert observed["localized_metabolic_strain"]["available"] is True
    assert observed["localized_metabolic_strain"]["status"] == (
        "localized_metabolic_strain_path_evaluated_at_zero"
    )
    assert observed["distress_exclusion"]["available"] is True
    assert observed["distress_exclusion"]["exclusion_scope"] == (
        "localized_metabolic_strain_only"
    )
    assert observed["fun"]["available"] is True
    assert observed["fun"]["status"] == "positive_engagement_trajectory_observed"
    assert observed["fun"]["behavioral_evidence_only"] is True
    assert observed["fun"]["named_emotion_authority"] is False
    assert observed["fun"]["reward_authority"] is False
    assert observed["social_joy"]["available"] is False
    assert observed["laughter"]["available"] is False
    assert observed["python_action_authority"] is False
    assert observed["reward_authority"] is False


def test_playful_formation_vocal_body_chain_and_recurrence_form_laughter_witness(
    monkeypatch,
) -> None:
    first, first_choice = _transition(
        action_receipt="1" * 64,
        origin_tick=1000,
        yaw=-31,
        world_revision=100,
    )
    play_candidate, play_completed = (
        production._advance_bounded_sensorimotor_play_evidence(
            None,
            None,
            first,
            first_choice,
            "continuous-environment:first",
        )
    )
    second, second_choice = _transition(
        action_receipt="2" * 64,
        origin_tick=1014,
        yaw=-19,
        world_revision=101,
    )
    _with_articulation(second, pressure_sha256="a" * 64)
    _, play_completed = production._advance_bounded_sensorimotor_play_evidence(
        play_candidate,
        play_completed,
        second,
        second_choice,
        "continuous-environment:second",
    )
    laughter_candidate, laughter_completed = (
        production._advance_bounded_body_owned_laughter_evidence(
            None,
            None,
            second,
            play_completed,
            "continuous-environment:second",
        )
    )

    assert laughter_candidate is not None
    assert laughter_completed is None
    assert laughter_candidate["matched_articulator_count"] == 1
    assert laughter_candidate["visual_receptor_return_count"] == 27

    third, _third_choice = _transition(
        action_receipt="3" * 64,
        origin_tick=1028,
        yaw=-23,
        world_revision=102,
    )
    _with_articulation(third, pressure_sha256="b" * 64)
    laughter_candidate, laughter_completed = (
        production._advance_bounded_body_owned_laughter_evidence(
            laughter_candidate,
            None,
            third,
            play_completed,
            "continuous-environment:third",
        )
    )

    assert laughter_candidate is None
    assert laughter_completed is not None
    assert laughter_completed["context"] == (
        "learned_playful_formation_recurrence"
    )
    assert laughter_completed["varied_acoustic_pressure"] is True
    assert laughter_completed["varied_body_orientation"] is True
    monkeypatch.setattr(
        production, "_last_sensorimotor_play_evidence", play_completed
    )
    monkeypatch.setattr(
        production, "_last_body_owned_laughter_evidence", laughter_completed
    )

    observed = production._sensorimotor_play_record()["laughter"]

    assert observed["available"] is True
    assert observed["status"] == "body_owned_laughter_recurred"
    assert observed["canned_audio_authority"] is False
    assert observed["tts_authority"] is False
    assert observed["animation_authority"] is False
    assert observed["python_cognition_authority"] is False


def test_generic_or_unjoined_articulation_cannot_be_reported_as_laughter() -> None:
    first, first_choice = _transition(
        action_receipt="4" * 64,
        origin_tick=1100,
        yaw=-29,
        world_revision=110,
    )
    play_candidate, _ = production._advance_bounded_sensorimotor_play_evidence(
        None,
        None,
        first,
        first_choice,
        "continuous-environment:first",
    )
    second, second_choice = _transition(
        action_receipt="5" * 64,
        origin_tick=1114,
        yaw=-17,
        world_revision=111,
    )
    _with_articulation(second, pressure_sha256="c" * 64)
    _, play_completed = production._advance_bounded_sensorimotor_play_evidence(
        play_candidate,
        None,
        second,
        second_choice,
        "continuous-environment:second",
    )
    second["articulation"]["recruitments"] = (
        (
            "0a" * 16,
            0,
            8,
            (("0b" * 16, 12, "0a" * 16, 13, 0, 4),),
        ),
    )

    assert production._advance_bounded_body_owned_laughter_evidence(
        None,
        None,
        second,
        play_completed,
        "continuous-environment:second",
    ) == (None, None)

    _with_articulation(second, pressure_sha256="c" * 64)
    second["articulation"]["self_hearing_hop_count"] = 0
    assert production._body_owned_laughter_episode_from_transition(
        second,
        play_completed,
        "continuous-environment:second",
    ) is None


def test_affective_trajectory_from_another_ordinal_cannot_be_bound_to_play() -> None:
    transition, choice = _transition(
        action_receipt="7" * 64,
        origin_tick=400,
        yaw=22,
        world_revision=40,
    )
    trajectory = list(transition["affective_balance_trajectories"][0])
    trajectory[3] = (399, trajectory[3][1])
    trajectory[4] = (399, trajectory[4][1])
    transition["affective_balance_trajectories"] = (tuple(trajectory),)

    episode = production._sensorimotor_play_episode_from_transition(
        transition,
        choice,
        "continuous-environment:unshared",
    )

    assert episode is not None
    assert "affective_body_participation" not in episode


def test_affective_timing_without_a_carrier_path_cannot_be_bound_to_play() -> None:
    transition, choice = _transition(
        action_receipt="e" * 64,
        origin_tick=450,
        yaw=23,
        world_revision=45,
    )
    transition["affective_motor_causal_use"] = None

    episode = production._sensorimotor_play_episode_from_transition(
        transition,
        choice,
        "continuous-environment:timing-only",
    )

    assert episode is not None
    assert "affective_body_participation" not in episode


def test_local_plastic_contact_and_retained_formation_converge_by_motor_event() -> None:
    transition, choice = _transition(
        action_receipt="9" * 64,
        origin_tick=470,
        yaw=24,
        world_revision=47,
    )
    trajectory = list(transition["affective_balance_trajectories"][0])
    trajectory[6] = _plasticity(470)
    transition["affective_balance_trajectories"] = (tuple(trajectory),)
    transition["affective_motor_causal_use"] = None
    transition["new_impression_causal_use"] = {
        "action": transition["causal_cross_context_use"]["action"],
        "changed_contact_channel_state": {
            "change_organism_tick": 470,
            "contact_cognitive_ordinal": 470,
            "left_lineage": SHARED_AFFECTIVE_LINEAGE,
            "right_lineage": "03" * 16,
            "parallel_ordinal": 0,
            "predecessor_state": (50, (0, 1), (1, 1)),
            "successor_state": (51, (0, 1), (51, 50)),
        },
        "directed_physical_transfers": (
            (SHARED_AFFECTIVE_LINEAGE, "03" * 16, 0, 4),
            ("03" * 16, "06" * 16, 0, 3),
        ),
        "motor_organism_tick": 473,
        "motor_unit_recruitment": {
            "motor_layer": 12,
            "motor_lineage": "06" * 16,
            "motor_topology_index": 2,
            "outward_elementary_carriers": 24,
        },
        "origin_kind": "new_neuronal_fractal",
    }

    episode = production._sensorimotor_play_episode_from_transition(
        transition,
        choice,
        "continuous-environment:population-convergence",
    )

    assert episode is not None
    participation = episode["affective_body_participation"]
    assert participation["affective_neuron_lineage"] == SHARED_AFFECTIVE_LINEAGE
    assert participation["affective_motor_organism_tick"] == 473
    assert participation["retained_formation_motor_organism_tick"] == 472
    assert participation["active_contact_organism_tick"] == 470
    assert participation["active_contact_predecessor_state"] == (
        50,
        (0, 1),
        (1, 1),
    )
    assert participation["active_contact_successor_state"] == (
        51,
        (0, 1),
        (51, 50),
    )
    assert participation["localized_gradient_settlement_ordinal"] == 471

    new_impression = transition["new_impression_causal_use"]
    new_impression["action"] = {
        **new_impression["action"],
        "causal_intent_receipt_sha256": "8" * 64,
    }
    refused = production._sensorimotor_play_episode_from_transition(
        transition,
        choice,
        "continuous-environment:different-action",
    )
    assert refused is not None
    assert "affective_body_participation" not in refused

    new_impression["action"] = transition["causal_cross_context_use"]["action"]
    new_impression["changed_contact_channel_state"] = {
        **new_impression["changed_contact_channel_state"],
        "predecessor_state": (50, (0, 1), (1, 1)),
        "successor_state": (50, (1, 8), (1, 1)),
    }
    phase_only = production._sensorimotor_play_episode_from_transition(
        transition,
        choice,
        "continuous-environment:phase-only",
    )
    assert phase_only is not None
    assert "affective_body_participation" in phase_only
    assert phase_only["affective_body_participation"][
        "active_contact_predecessor_state"
    ] != phase_only["affective_body_participation"][
        "active_contact_successor_state"
    ]

    unchanged = new_impression["changed_contact_channel_state"]
    unchanged["successor_state"] = unchanged["predecessor_state"]
    refused = production._sensorimotor_play_episode_from_transition(
        transition,
        choice,
        "continuous-environment:unchanged-contact",
    )
    assert refused is not None
    assert "affective_body_participation" not in refused

    unchanged["successor_state"] = (51, (0, 1), (51, 50))
    new_impression["directed_physical_transfers"] = (
        (SHARED_AFFECTIVE_LINEAGE, "03" * 16, 1, 4),
        ("03" * 16, "06" * 16, 0, 3),
    )
    off_path = production._sensorimotor_play_episode_from_transition(
        transition,
        choice,
        "continuous-environment:off-path-contact",
    )
    assert off_path is not None
    assert "affective_body_participation" not in off_path


def test_unmet_dissipation_refuses_overload_exclusion() -> None:
    transition, choice = _transition(
        action_receipt="8" * 64,
        origin_tick=500,
        yaw=18,
        world_revision=50,
    )
    transition["unmet_dissipation_quanta"] = 1

    episode = production._sensorimotor_play_episode_from_transition(
        transition,
        choice,
        "continuous-environment:overloaded",
    )

    assert episode is not None
    assert "metabolic_overload_exclusion" not in episode


def test_nonzero_localized_metabolic_strain_refuses_narrow_exclusion(
    monkeypatch,
) -> None:
    first, first_choice = _transition(
        action_receipt="a" * 64,
        origin_tick=600,
        yaw=-23,
        world_revision=60,
    )
    first["localized_metabolic_strain"] = (
        (BODY_RECEPTOR_LINEAGE, 5, 2, 600, (0, 4, 0), "3", "0"),
    )
    candidate, _ = production._advance_bounded_sensorimotor_play_evidence(
        None,
        None,
        first,
        first_choice,
        "continuous-environment:first",
    )
    second, second_choice = _transition(
        action_receipt="b" * 64,
        origin_tick=614,
        yaw=-17,
        world_revision=61,
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

    assert observed["localized_metabolic_strain"]["available"] is True
    assert observed["localized_metabolic_strain"]["status"] == (
        "localized_metabolic_strain_observed"
    )
    assert observed["distress_exclusion"]["available"] is False
    assert observed["distress_exclusion"]["status"] == (
        "localized_metabolic_strain_observed"
    )
    assert observed["fun"]["available"] is True
    assert observed["fun"]["distress_absence_authority"] is False


def test_unchanged_world_context_refuses_positive_engagement_claim(
    monkeypatch,
) -> None:
    first, first_choice = _transition(
        action_receipt="9" * 64,
        origin_tick=700,
        yaw=-29,
        world_revision=70,
    )
    candidate, _ = production._advance_bounded_sensorimotor_play_evidence(
        None,
        None,
        first,
        first_choice,
        "continuous-environment:first",
    )
    second, second_choice = _transition(
        action_receipt="8" * 64,
        origin_tick=714,
        yaw=-17,
        world_revision=71,
    )
    same_context = first["causal_cross_context_use"]["action"][
        "world_state_before_sha256"
    ]
    second["causal_cross_context_use"]["action"][
        "world_state_before_sha256"
    ] = same_context
    second["motor_action"]["world_state_before_sha256"] = same_context
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
    assert observed["changed_world_context"] is False
    assert observed["fun"]["available"] is False
    assert observed["fun"]["status"] == "positive_engagement_trajectory_unproved"


def test_later_zero_evaluation_clears_prior_sparse_strain_without_summing() -> None:
    evaluated, retained = (
        production._advance_bounded_localized_metabolic_strain_evidence(
            (),
            (),
            {
                "localized_metabolic_strain_evaluated_body_receptor_lineages": (
                    BODY_RECEPTOR_LINEAGE,
                ),
                "localized_metabolic_strain": (
                    (BODY_RECEPTOR_LINEAGE, 5, 2, 700, (2,), "1", "0"),
                ),
            },
        )
    )
    evaluated, retained = (
        production._advance_bounded_localized_metabolic_strain_evidence(
            evaluated,
            retained,
            {
                "localized_metabolic_strain_evaluated_body_receptor_lineages": (
                    BODY_RECEPTOR_LINEAGE,
                ),
                "localized_metabolic_strain": (),
            },
        )
    )

    assert evaluated == (BODY_RECEPTOR_LINEAGE,)
    assert retained == ()


def test_incomplete_first_play_is_replaced_by_two_later_qualified_episodes() -> None:
    first, first_choice = _transition(
        action_receipt="c" * 64,
        origin_tick=800,
        yaw=-21,
        world_revision=80,
    )
    first["affective_balance_trajectories"] = ()
    candidate, completed = production._advance_bounded_sensorimotor_play_evidence(
        None,
        None,
        first,
        first_choice,
        "continuous-environment:first",
    )

    second, second_choice = _transition(
        action_receipt="d" * 64,
        origin_tick=814,
        yaw=-39,
        world_revision=81,
    )
    candidate, completed = production._advance_bounded_sensorimotor_play_evidence(
        candidate,
        completed,
        second,
        second_choice,
        "continuous-environment:second",
    )
    assert completed is not None
    assert "localized_metabolic_strain" not in completed["first_episode"]
    assert candidate == completed["return_episode"]

    third, third_choice = _transition(
        action_receipt="e" * 64,
        origin_tick=828,
        yaw=-27,
        world_revision=82,
    )
    candidate, completed = production._advance_bounded_sensorimotor_play_evidence(
        candidate,
        completed,
        third,
        third_choice,
        "continuous-environment:third",
    )

    assert candidate is None
    assert completed is not None
    assert completed["first_episode"]["signed_yaw_millidegrees"] == -39
    assert completed["return_episode"]["signed_yaw_millidegrees"] == -27
    assert completed["first_episode"]["localized_metabolic_strain"][
        "evaluated_body_receptor_count"
    ] == 1
    assert completed["return_episode"]["localized_metabolic_strain"][
        "evaluated_body_receptor_count"
    ] == 1
