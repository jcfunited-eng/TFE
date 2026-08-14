"""A-006 exact new-impression-to-later-action causal observation."""

from __future__ import annotations

from dsf_ai_service import native_production_app as production


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
    cues: tuple[tuple[str, tuple[str, ...]], ...] = (),
    motors: tuple[tuple[str, int, int, tuple[object, ...]], ...] = (),
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


def test_new_impression_advances_only_after_formation_then_reaches_motor() -> None:
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

    first = (association, impression, 0, 29)
    observer.transfers = ((*first, association),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(11),
    )
    assert completed == {}

    second = (association, motor, 0, 7)
    observer.transfers = ()
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            12,
            motors=((motor, 4, 7, ((association, 11, motor, 12, 0, 7),)),),
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
        _hop(21, cues=(("11" * 32, (cue,)),)),
    )

    assert observer.filters == [(impression, cue)]


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
            (shared, 10, 1, association, body, gradient),
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
                "vestibular_tick_count": 1,
            },
        },
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
