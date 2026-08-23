"""A-006 exact new-impression-to-later-action causal observation."""

from __future__ import annotations

from dsf_ai_service import native_production_app as production


def _plasticity(ordinal: int) -> tuple[object, ...]:
    return (
        ordinal,
        "2",
        "2",
        (1, 8),
        (7, 8),
        (0, 1),
        (1, 1),
        (4, 3),
        ((1, 1), (0, 1), (0, 1)),
        ((7, 8), (1, 8), (0, 1)),
    )


class _FrontierObserver:
    def __init__(self) -> None:
        self.transfers: tuple[tuple[str, str, int, int, str], ...] = ()
        self.filters: list[tuple[str, ...]] = []

    def observe_active_electrical_frontier_advances_from(
        self, lineages: tuple[str, ...]
    ) -> tuple[tuple[str, str, int, int, str], ...]:
        self.filters.append(lineages)
        return tuple(
            transfer
            for transfer in self.transfers
            if (transfer[1] if transfer[4] == transfer[0] else transfer[0])
            in lineages
        )


def _hop(
    predecessor_tick: int,
    *,
    emitted: tuple[str, ...] = (),
    cues: tuple[tuple[str, tuple[str, ...], str | None], ...] = (),
    motors: tuple[
        tuple[str, int, int, tuple[object, ...], tuple[object, ...]], ...
    ] = (),
) -> dict[str, object]:
    return {
        "predecessor_organism_tick": predecessor_tick,
        "organism_tick": predecessor_tick + 1,
        "emitted_neuron_fractals": tuple(
            {"neuron_lineage": lineage} for lineage in emitted
        ),
        "internally_reassembled_formation_cues": cues,
        "motor_unit_recruitments": motors,
    }


def test_new_impression_crosses_intake_boundaries_only_while_advancing_to_motor() -> None:
    impression = "01" * 16
    association = "02" * 16
    motor = "03" * 16
    observer = _FrontierObserver()
    active = {}
    completed = {}

    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(10, emitted=(impression,)),
    )
    assert completed == {}
    assert observer.filters == []
    active = production._retain_cross_intake_causal_motor_traces(active)
    assert tuple(key[0] for key in active) == ("new_neuronal_fractal",)

    first = (association, impression, 0, 29)
    observer.transfers = ((*first, association),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(11),
    )
    assert completed == {}
    active = production._retain_cross_intake_causal_motor_traces(active)
    assert tuple(key[0] for key in active) == ("new_neuronal_fractal",)

    second = (association, motor, 0, 7)
    observer.transfers = ()
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            12,
            motors=(
                (
                    motor,
                    4,
                    7,
                    ((association, 11, motor, 12, 0, 7),),
                    (),
                ),
            ),
        ),
    )

    proof = completed["new_neuronal_fractal"]
    assert proof["emitted_neuron_lineages"] == (impression,)
    assert proof["impression_organism_tick"] == 11
    assert proof["motor_organism_tick"] == 13
    assert proof["directed_physical_transfers"] == (first, second)
    assert proof["motor_unit_recruitment"]["motor_lineage"] == motor
    assert observer.filters == [(impression,), (association,)]


def test_new_and_recurrent_roots_share_one_frontier_query_per_hop() -> None:
    impression = "01" * 16
    cue = "02" * 16
    observer = _FrontierObserver()
    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        _hop(20, emitted=(impression,)),
    )

    observer.transfers = ()
    production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(21, cues=(("11" * 32, (cue,), cue),)),
    )

    assert observer.filters == [(impression, cue)]


def test_external_participant_receptor_pulse_crosses_intervals_to_motor() -> None:
    receptor = "09" * 16
    association = "02" * 16
    motor = "03" * 16
    participant_receipt = "a" * 64
    observer = _FrontierObserver()

    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        {
            **_hop(30),
            "external_participant_action_receipt": participant_receipt,
            "externally_perturbed_neuron_lineages": (receptor,),
        },
    )
    assert completed == {}

    first = (association, receptor, 0, 13)
    observer.transfers = ((*first, association),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(31),
    )
    assert "external_participant_sensory" not in completed

    second = (association, motor, 0, 5)
    observer.transfers = ()
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            32,
            motors=(
                (
                    motor,
                    4,
                    5,
                    ((association, 11, motor, 12, 0, 5),),
                    (),
                ),
            ),
        ),
    )

    assert active == {}
    proof = completed["external_participant_sensory"]
    assert proof["participant_action_causal_intent_receipt_sha256"] == (
        participant_receipt
    )
    assert proof["perturbed_receptor_lineages"] == (receptor,)
    assert proof["directed_physical_transfers"] == (first, second)


def test_one_seal_trajectory_preserves_external_cause_across_exact_intervals() -> None:
    receptor = "09" * 16
    association = "02" * 16
    motor = "03" * 16
    participant_receipt = "a" * 64
    first = (association, receptor, 0, 13)
    second = (association, motor, 0, 5)
    observer = _FrontierObserver()

    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        {
            "predecessor_organism_tick": 30,
            "organism_tick": 33,
            "external_participant_action_receipt": participant_receipt,
            "causal_interval_evidence": (
                {
                    **_hop(30),
                    "externally_perturbed_neuron_lineages": (receptor,),
                    "causal_frontier_advances": (),
                },
                {
                    **_hop(31),
                    "causal_frontier_advances": ((*first, association),),
                },
                {
                    **_hop(
                        32,
                        motors=(
                            (
                                motor,
                                4,
                                5,
                                ((association, 11, motor, 12, 0, 5),),
                                (),
                            ),
                        ),
                    ),
                    "causal_frontier_advances": (),
                },
            ),
        },
    )

    assert active == {}
    assert observer.filters == []
    proof = completed["external_participant_sensory"]
    assert proof["participant_action_causal_intent_receipt_sha256"] == (
        participant_receipt
    )
    assert proof["perturbed_receptor_lineages"] == (receptor,)
    assert proof["directed_physical_transfers"] == (first, second)


def test_retained_contact_change_is_bound_only_to_its_later_motor_path() -> None:
    cue = "01" * 16
    association = "02" * 16
    motor = "03" * 16
    observer = _FrontierObserver()
    changed = (
        11,
        cue,
        association,
        0,
        (50, (0, 1), (1, 1)),
        (51, (0, 1), (51, 50)),
    )

    first = (association, cue, 0, 29)
    observer.transfers = ((*first, association),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        {
            **_hop(10, cues=(("11" * 32, (cue,), cue),)),
            "changed_contact_channel_states": (changed,),
        },
    )
    assert "retained_formation" not in completed

    second = (association, motor, 0, 7)
    observer.transfers = ()
    _active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            11,
            motors=(
                (
                    motor,
                    4,
                    7,
                    ((association, 11, motor, 12, 0, 7),),
                    (),
                ),
            ),
        ),
    )

    proof = completed["retained_formation"]
    assert proof["directed_physical_transfers"] == (first, second)
    assert proof["changed_contact_channel_state"] == {
        "change_organism_tick": 11,
        "contact_cognitive_ordinal": 11,
        "left_lineage": cue,
        "right_lineage": association,
        "parallel_ordinal": 0,
        "predecessor_state": changed[4],
        "successor_state": changed[5],
    }


def test_complete_affective_trajectory_reaches_motor_by_exact_carrier_path() -> None:
    affective = "0a" * 16
    ordering = "0b" * 16
    motor = "0c" * 16
    trajectory = (
        affective,
        10,
        2,
        (30, ("07" * 16, affective, 0, 11)),
        (30, (affective, "08" * 16, 0, 7)),
        (31, -9, -7, -8, 2, 2, 0, (3, 1), (5, 1), (1, 1)),
        _plasticity(30),
    )
    observer = _FrontierObserver()

    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        {
            **_hop(30),
            "affective_balance_trajectories": (trajectory,),
        },
    )
    assert completed == {}
    assert observer.filters == []

    first = (affective, ordering, 0, 13)
    observer.transfers = ((*first, ordering),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(31),
        (trajectory,),
    )
    assert completed == {}

    second = (ordering, motor, 0, 5)
    observer.transfers = ()
    _active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            32,
            motors=(
                (
                    motor,
                    3,
                    5,
                    ((ordering, 11, motor, 12, 0, 5),),
                    (),
                ),
            ),
        ),
        (trajectory,),
    )

    proof = completed["affective_gradient"]
    assert proof["affective_neuron_lineage"] == affective
    assert proof["localized_gradient_settlement_organism_tick"] == 31
    assert proof["localized_recovery_settlement_organism_tick"] == 30
    assert proof["motor_organism_tick"] == 33
    assert proof["directed_physical_transfers"] == (first, second)
    assert proof["motor_unit_recruitment"]["motor_lineage"] == motor
    assert proof["affective_trajectory_receipt_sha256"] == production._receipt(
        trajectory
    )
    assert observer.filters == [(affective,), (ordering,)]


def test_transaction_assembled_affective_trajectory_reaches_motor() -> None:
    affective = "0a" * 16
    ordering = "0b" * 16
    motor = "0c" * 16
    association = (31, ("07" * 16, affective, 0, 11))
    body = (31, (affective, "08" * 16, 0, 7))
    gradient = (32, -9, -7, -8, 2, 2, 0, (3, 1), (5, 1), (1, 1))
    plasticity = _plasticity(31)
    association_hop = {
        **_hop(30),
        "affective_balance_trajectories": (
            (affective, 10, 2, association, body, None, plasticity),
        ),
    }
    gradient_hop = {
        **_hop(31),
        "affective_balance_trajectories": (
            (affective, 10, 2, None, None, gradient, None),
        ),
    }
    observer = _FrontierObserver()
    retained = production._advance_bounded_affective_balance_evidence(
        (), association_hop
    )
    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        association_hop,
        retained,
    )
    assert active == {}

    retained = production._advance_bounded_affective_balance_evidence(
        retained, gradient_hop
    )
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        gradient_hop,
        retained,
    )
    assert len(active) == 1

    first = (affective, ordering, 0, 13)
    observer.transfers = ((*first, ordering),)
    propagation_hop = {
        **_hop(32),
        "affective_balance_trajectories": (),
    }
    retained = production._advance_bounded_affective_balance_evidence(
        retained, propagation_hop
    )
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        propagation_hop,
        retained,
    )

    observer.transfers = ()
    motor_hop = {
        **_hop(
            33,
            motors=(
                (
                    motor,
                    3,
                    5,
                    ((ordering, 11, motor, 12, 0, 5),),
                    (),
                ),
            ),
        ),
        "affective_balance_trajectories": (),
    }
    retained = production._advance_bounded_affective_balance_evidence(
        retained, motor_hop
    )
    _active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        motor_hop,
        retained,
    )

    proof = completed["affective_gradient"]
    assert proof["localized_gradient_settlement_organism_tick"] == 32
    assert proof["localized_recovery_settlement_organism_tick"] == 31
    assert proof["directed_physical_transfers"] == (
        first,
        (ordering, motor, 0, 5),
    )


def test_exact_witness_credits_curiosity_without_a_score(monkeypatch) -> None:
    source = "01" * 16
    shared = "02" * 16
    motor = "03" * 16
    prediction = "04" * 16
    other = "05" * 16
    first_transfer = (source, shared, 0, 13)
    motor_transfer = (shared, motor, 0, 5)
    alternatives = (
        ((source, prediction, 0, 7), (prediction, shared, 0, 3)),
        ((source, other, 0, 6), (other, "06" * 16, 0, 2)),
    )
    association = (1, ("07" * 16, shared, 0, 2))
    body = (1, ("08" * 16, shared, 0, 2))
    gradient = (2, 0, 0, 0, 0, 1, 0, (0, 1), (0, 1), (0, 1))
    transition = {
        "affective_balance_trajectories": (
            (shared, 10, 1, association, body, gradient, _plasticity(2)),
        ),
        "intake": "continuous-environment:test",
        "new_impression_causal_use": {
            "action": {
                "command_sha256": "a" * 64,
                "world_state_before_sha256": "b" * 64,
                "world_state_after_sha256": "c" * 64,
            },
            "directed_physical_transfers": (first_transfer, motor_transfer),
            "emitted_neuron_lineages": (source,),
            "impression_organism_tick": 11,
            "motor_organism_tick": 13,
            "sensed_consequence": {
                "externally_perturbed_body_receptor_count": 1,
                "vestibular_tick_count": 0,
            },
        },
        "organism_identity": "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1",
        "organism_tick": 14,
        "physical_frontier_routes": (
            ("a", "b", "c", "d", 0, 0, 0, 1),
            ("e", "f", "g", "h", 0, 0, 0, 0),
        ),
        "physical_prediction_alternatives": alternatives,
        "preceding_distinct_physical_frontier_routes": (
            ("i", "j", "k", "l", 0, 0, 0, 1),
        ),
        "reached_and_foregone_physical_frontier_routes": (
            ("a", "b", "c", "d", 0, 0, 0, 1),
            ("e", "f", "g", "h", 0, 0, 0, 0),
        ),
        "state_sha256": "d" * 64,
    }

    evidence = production._intrinsic_curiosity_evidence_from_transition(transition)
    assert evidence is not None
    assert evidence["shared_causal_lineages"] == (shared,)
    monkeypatch.setattr(production, "_last_intrinsic_curiosity_evidence", evidence)
    curiosity = production._intrinsic_curiosity_record()
    assert curiosity["available"] is True
    assert curiosity["curiosity_score_authority"] is False
    assert curiosity["reward_authority"] is False
    assert curiosity["social_experience_claimed"] is False

    # Observer arity and the stronger lineage overlap are evidence details,
    # not invented vetoes on a genuine novelty-to-action occurrence.
    unshared = production._intrinsic_curiosity_evidence_from_transition(
        {
            **transition,
            "affective_balance_trajectories": (),
            "physical_prediction_alternatives": alternatives[:1],
        }
    )
    assert unshared is not None
    assert unshared["shared_causal_lineages"] == ()
    assert unshared["possible_consequence_junction_observed"] is True

    participant_receipt = "e" * 64
    social_evidence = production._intrinsic_curiosity_evidence_from_transition(
        {
            **transition,
            "participant_sensory_causal_use": {
                "action": transition["new_impression_causal_use"]["action"],
                "directed_physical_transfers": (
                    ("09" * 16, shared, 0, 11),
                    motor_transfer,
                ),
                "motor_organism_tick": 13,
                "origin_kind": "external_participant_sensory",
                "participant_action_causal_intent_receipt_sha256": (
                    participant_receipt
                ),
                "perturbed_receptor_lineages": ("09" * 16,),
                "receptor_settlement_organism_tick": 10,
                "sensed_consequence": {
                    "externally_perturbed_body_receptor_count": 1,
                },
            },
        }
    )
    assert social_evidence is not None
    assert social_evidence["social_experience"] == {
        "directed_physical_transfers": (
            ("09" * 16, shared, 0, 11),
            motor_transfer,
        ),
        "motor_organism_tick": 13,
        "participant_action_causal_intent_receipt_sha256": participant_receipt,
        "perturbed_receptor_lineages": ("09" * 16,),
        "receptor_settlement_organism_tick": 10,
    }
    monkeypatch.setattr(
        production, "_last_intrinsic_curiosity_evidence", social_evidence
    )
    assert production._intrinsic_curiosity_record()[
        "social_experience_claimed"
    ] is True

    mismatched_social = production._intrinsic_curiosity_evidence_from_transition(
        {
            **transition,
            "participant_sensory_causal_use": {
                **{
                    key: value
                    for key, value in social_evidence["social_experience"].items()
                },
                "action": {"command_sha256": "f" * 64},
                "origin_kind": "external_participant_sensory",
            },
        }
    )
    assert mismatched_social is not None
    assert "social_experience" not in mismatched_social

    independent_social = production._social_experience_evidence_from_transition(
        {
            **transition,
            "participant_sensory_causal_use": {
                **{
                    key: value
                    for key, value in social_evidence["social_experience"].items()
                },
                "action": {"command_sha256": "f" * 64},
                "origin_kind": "external_participant_sensory",
                "sensed_consequence": {
                    "externally_perturbed_body_receptor_count": 1,
                },
            },
        }
    )
    assert independent_social is not None
    monkeypatch.setattr(production, "_last_intrinsic_curiosity_evidence", evidence)
    monkeypatch.setattr(
        production, "_last_social_experience_evidence", independent_social
    )
    assert production._intrinsic_curiosity_record()[
        "social_experience_claimed"
    ] is True

    unavailable = {"available": False, "status": "unproved"}
    record = {
        "identity": unavailable,
        "sensory": {
            modality: unavailable
            for modality in (
                "visual",
                "auditory",
                "touch",
                "temperature",
                "smell",
                "taste",
                "proprioception",
                "vestibular",
                "interoception",
            )
        },
        "fractals": unavailable,
        "formations": {**unavailable, "mosaic_count": 0},
        "persistence": unavailable,
        "recall": unavailable,
        "body": unavailable,
        "attention": unavailable,
        "working_causal_state": unavailable,
        "prediction": unavailable,
        "affective_balance": unavailable,
        "articulation": unavailable,
        "intrinsic_curiosity": curiosity,
    }
    monkeypatch.setattr(production, "_last_transition_evidence", None)
    capital = production._cognitive_capital_record(record)
    credits = {
        (cell["capability"], cell["dimension"])
        for cell in capital["credits"]
    }
    assert credits == {
        ("Motivation, needs, and curiosity", "availability"),
        ("Motivation, needs, and curiosity", "participation"),
        ("Motivation, needs, and curiosity", "causal_use"),
        ("Motivation, needs, and curiosity", "autonomous_use"),
        ("Motivation, needs, and curiosity", "integration_depth"),
    }
