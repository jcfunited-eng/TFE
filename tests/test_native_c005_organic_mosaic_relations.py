"""C-005 truthful admitted-experience relation transport."""

from __future__ import annotations

from types import SimpleNamespace

from dsf_ai_service import native_production_app as production


def _hop(tick: int, relations: tuple[dict[str, object], ...]) -> dict[str, object]:
    counts = {
        "complete_neuron_fractal_count": 0,
        "current_cohort_evaluation_count": 1,
        "dsf_delivery_count": 1,
        "endogenous_partial_cue_reassembly_count": 0,
        "partial_cue_reassembly_count": 1,
        "physically_transitioned_neuron_count": 2,
        "metabolically_perturbed_body_receptor_count": 0,
        "rest_recovered_neuron_count": 0,
        "rest_drained_dissipation_quanta": 0,
        "unmet_dissipation_quanta": 0,
        "energy_exhausted_interval_count": 0,
        "externally_perturbed_body_receptor_count": 0,
        "recurrent_complete_neuron_fractal_count": 0,
    }
    return {
        **counts,
        "cognitive_mosaic_count": 2,
        "cognitive_trace_count": 0,
        "complete_neuron_count": 43,
        "developmental_resting_neuron_count": 196_509,
        "emitted_neuron_fractals": (),
        "formation_activation_count": 0,
        "predecessor_organism_tick": tick - 1,
        "organism_tick": tick,
        "internally_reassembled_formation_cues": (),
        "receptor_ingress_sense_counts": {
            sense.value: 0 for sense in production.SENSE_ORDER
        },
        "receptor_ingress_changing_count": 0,
        "receptor_ingress_quiescent_count": 0,
        "motor_unit_recruitments": (),
        "articulatory_unit_recruitments": (),
        "physical_frontier_routes": (),
        "preceding_distinct_physical_frontier_routes": (),
        "reached_and_foregone_physical_frontier_routes": (),
        "working_causal_continuations": (),
        "settled_working_frontier": (),
        "physical_prediction_alternatives": (),
        "body_consequence_transfers": (),
        "affective_balance_trajectories": (),
        "localized_fluid_chemistry": (),
        "localized_metabolic_strain_evaluated_body_receptor_lineages": (),
        "localized_metabolic_strain": (),
        "organic_mosaic_relations": relations,
        "state_sha256": f"{tick:064x}",
    }


def test_frontier_evidence_keeps_only_current_and_preceding_distinct_sets() -> None:
    first = (("01" * 16, 5, 0, "02" * 16, 8, 0, 0, 1),)
    second = (("01" * 16, 5, 0, "03" * 16, 8, 1, 0, 2),)

    current, preceding, reached_and_foregone = production._advance_bounded_frontier_evidence(
        (),
        (),
        (),
        {
            "physical_frontier_routes": first,
            "preceding_distinct_physical_frontier_routes": (),
            "reached_and_foregone_physical_frontier_routes": (),
        },
    )
    current, preceding, reached_and_foregone = production._advance_bounded_frontier_evidence(
        current,
        preceding,
        reached_and_foregone,
        {
            "physical_frontier_routes": second,
            "preceding_distinct_physical_frontier_routes": first,
            "reached_and_foregone_physical_frontier_routes": second,
        },
    )

    assert current == second
    assert preceding == first
    assert reached_and_foregone == second


def test_working_causal_evidence_keeps_one_path_until_that_cause_settles() -> None:
    first = ("01" * 16, "02" * 16, 0, 7)
    second = ("02" * 16, "03" * 16, 0, 5)
    continuation, settlement = production._advance_bounded_working_causal_evidence(
        (),
        (),
        {
            "working_causal_continuations": ((first, second),),
            "settled_working_frontier": (),
        },
    )
    continuation, settlement = production._advance_bounded_working_causal_evidence(
        continuation,
        settlement,
        {
            "working_causal_continuations": (),
            "settled_working_frontier": (first, second),
        },
    )

    assert continuation == ((first, second),)
    assert settlement == (second,)


def test_prediction_evidence_keeps_two_alternatives_until_body_consequence() -> None:
    intrinsic_cause = "01" * 16
    first = ((intrinsic_cause, "02" * 16, 0, 7), ("02" * 16, "04" * 16, 0, 5))
    second = ((intrinsic_cause, "03" * 16, 0, 6), ("03" * 16, "05" * 16, 0, 4))
    consequence = ("06" * 16, "04" * 16, 0, 3)
    alternatives, returned = production._advance_bounded_prediction_evidence(
        (),
        (),
        {
            "physical_prediction_alternatives": (first, second),
            "body_consequence_transfers": (),
        },
    )
    alternatives, returned = production._advance_bounded_prediction_evidence(
        alternatives,
        returned,
        {
            "physical_prediction_alternatives": (),
            "body_consequence_transfers": (consequence,),
        },
    )
    assert alternatives == (first, second)
    assert returned == (consequence,)


def test_prediction_evidence_preserves_later_consequence_inside_ordered_trajectory() -> None:
    intrinsic_cause = "01" * 16
    first = ((intrinsic_cause, "02" * 16, 0, 7), ("02" * 16, "04" * 16, 0, 5))
    second = ((intrinsic_cause, "03" * 16, 0, 6), ("03" * 16, "05" * 16, 0, 4))
    consequence = ("04" * 16, "06" * 16, 0, 3)

    alternatives, returned = production._advance_bounded_prediction_evidence(
        (),
        (),
        {
            "physical_prediction_alternatives": (first, second),
            "body_consequence_transfers": (consequence,),
        },
    )

    assert alternatives == (first, second)
    assert returned == (consequence,)


def test_admitted_experience_preserves_relation_from_nonfinal_hop(
    monkeypatch,
) -> None:
    relation = {
        "predecessor_organism_tick": 10,
        "organism_tick": 11,
        "formation_receipts": ("11" * 32, "22" * 32),
        "shared_neuron_lineages": (),
        "active_physical_bonds": (("01" * 16, "02" * 16, 0),),
        "structural_relation_sha256": "33" * 32,
        "ordered_physical_paths": (),
        "ordered_path_relations": (),
    }
    organism = object()
    predecessor = SimpleNamespace(state_sha256="aa" * 32)
    monkeypatch.setattr(
        production,
        "_runtime",
        lambda: (
            SimpleNamespace(organism=organism, pointer=predecessor),
            SimpleNamespace(),
        ),
    )
    first_hop = _hop(11, (relation,))
    first_hop["rest_recovered_neuron_count"] = 2
    second_hop = _hop(12, ())
    second_hop["rest_recovered_neuron_count"] = 3
    hops = iter((first_hop, second_hop))
    monkeypatch.setattr(
        production,
        "_commit_admitted_hop",
        lambda *_args: next(hops),
    )
    monkeypatch.setattr(production, "_prepare_motor_yaw_action", lambda *_: None)
    monkeypatch.setattr(
        production,
        "_publish_committed_organism",
        lambda *_args: SimpleNamespace(
            pointer=SimpleNamespace(
                organism_tick=12,
                state_bytes=100,
                state_sha256="bb" * 32,
            )
        ),
    )
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)

    result = production._perform_admitted_intake_locked(
        [(object(), []), (object(), [])],
        "c005-test",
    )

    assert result["observation"]["organism_tick"] == 12
    assert result["observation"]["organic_mosaic_relations"] == (relation,)
    assert result["totals"]["rest_recovered_neuron_count"] == 5
    assert "unmet_dissipation_quanta" not in result["totals"]
    assert result["observation"]["unmet_dissipation_quanta"] == 0


def test_layer_thirteen_discharge_commits_its_own_pressure_as_self_hearing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(production, "_last_tested_articulation_evidence", None)
    monkeypatch.setattr(production, "_last_transition_evidence", None)
    recruitment = (
        "13" * 16,
        0,
        13,
        (("12" * 16, 12, "13" * 16, 13, 0, 13),),
    )
    first = _hop(11, ())
    first["articulatory_unit_recruitments"] = (recruitment,)
    heard = _hop(12, ())
    heard["physically_transitioned_neuron_count"] = 4
    heard["complete_neuron_fractal_count"] = 1
    heard["externally_perturbed_body_receptor_count"] = 4
    # The production boundary deliberately exposes no direct ``organism_tick``
    # method.  The exact committed hop already carries the causal tick used to
    # name its self-hearing occurrence.
    organism = object()
    predecessor = SimpleNamespace(state_sha256="aa" * 32)
    monkeypatch.setattr(
        production,
        "_runtime",
        lambda: (
            SimpleNamespace(organism=organism, pointer=predecessor),
            SimpleNamespace(),
        ),
    )
    hops = iter((first, heard))
    monkeypatch.setattr(production, "_commit_admitted_hop", lambda *_: next(hops))
    monkeypatch.setattr(
        production,
        "_mono_pcm_hop_episodes",
        lambda **_kwargs: [(object(), [])],
    )
    monkeypatch.setattr(production, "_prepare_motor_yaw_action", lambda *_: None)
    monkeypatch.setattr(
        production,
        "_publish_committed_organism",
        lambda *_args: SimpleNamespace(
            pointer=SimpleNamespace(
                organism_tick=12,
                state_bytes=100,
                state_sha256="bb" * 32,
            )
        ),
    )
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)

    result = production._perform_admitted_intake_locked(
        [(object(), [])],
        "c020-test",
    )

    articulation = result["observation"]["articulation"]
    assert articulation["layer_13_recruitment_count"] == 1
    assert articulation["pressure_sample_count"] >= 16_000
    assert articulation["self_hearing_hop_count"] == 1
    assert articulation["self_hearing_transitioned_neuron_count"] == 4
    assert articulation["self_hearing_fractal_count"] == 1
    assert articulation["articulatory_body_port_count"] == 4
    assert articulation["articulatory_body_nonquiescent_port_count"] == 4
    assert articulation["articulatory_body_receptor_ingress_count"] == 4
    assert articulation["articulatory_body_perturbed_neuron_count"] == 4
    production._last_transition_evidence = {"articulation": None}
    retained_observation = production._articulation_record()
    assert retained_observation["available"] is True
    assert (
        retained_observation["status"]
        == "native_articulation_and_self_hearing_committed"
    )
    assert retained_observation["organism_tick"] == 12


def test_vestibular_trajectory_articulation_reaches_the_ordinary_aggregate(
    monkeypatch,
) -> None:
    monkeypatch.setattr(production, "_last_tested_articulation_evidence", None)
    monkeypatch.setattr(production, "_last_transition_evidence", None)
    recruitment = (
        "13" * 16,
        0,
        5,
        (("12" * 16, 12, "13" * 16, 13, 0, 5),),
    )
    trajectory = _hop(261, ())
    trajectory["articulatory_unit_recruitments"] = (recruitment,)
    heard = _hop(262, ())
    heard["physically_transitioned_neuron_count"] = 3
    heard["complete_neuron_fractal_count"] = 2
    heard["externally_perturbed_body_receptor_count"] = 4
    organism = object()
    predecessor = SimpleNamespace(state_sha256="aa" * 32)
    monkeypatch.setattr(
        production,
        "_runtime",
        lambda: (
            SimpleNamespace(organism=organism, pointer=predecessor),
            SimpleNamespace(),
        ),
    )
    monkeypatch.setattr(
        production,
        "_commit_vestibular_trajectory",
        lambda *_args: trajectory,
    )
    monkeypatch.setattr(
        production,
        "_commit_admitted_hop",
        lambda *_args: heard,
    )
    monkeypatch.setattr(
        production,
        "_mono_pcm_hop_episodes",
        lambda **_kwargs: [(object(), [])],
    )
    monkeypatch.setattr(production, "_prepare_motor_yaw_action", lambda *_: None)
    monkeypatch.setattr(
        production,
        "_publish_committed_organism",
        lambda *_args: SimpleNamespace(
            pointer=SimpleNamespace(
                organism_tick=262,
                state_bytes=100,
                state_sha256="bb" * 32,
            )
        ),
    )
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)

    result = production._perform_admitted_intake_locked(
        [],
        "c020-live-path-test",
        vestibular_yaw=(0, (360,)),
    )

    articulation = result["observation"]["articulation"]
    assert articulation["layer_13_recruitment_count"] == 1
    assert articulation["self_hearing_hop_count"] == 1
    assert articulation["self_hearing_transitioned_neuron_count"] == 3
    assert articulation["self_hearing_fractal_count"] == 2


def test_admitted_hop_carries_native_structure_receipt_after_commit() -> None:
    receipts = ("11" * 32, "22" * 32)
    left_members = ("01" * 16, "02" * 16, "03" * 16)
    right_members = ("04" * 16, "05" * 16, "06" * 16)
    bond = (left_members[0], right_members[0], 0)
    evidence = SimpleNamespace(
        token="commit-token",
        predecessor_organism_tick=10,
        organism_tick=11,
        complete_neuron_fractal_count=0,
        emitted_neuron_fractals=(),
        current_cohort_evaluation_count=1,
        dsf_delivery_count=1,
        partial_cue_reassembly_count=1,
        endogenous_partial_cue_reassembly_count=0,
        internally_reassembled_formation_cues=(),
        physically_transitioned_neuron_count=2,
        metabolically_perturbed_body_receptor_count=0,
        rest_recovered_neuron_count=7,
        rest_drained_dissipation_quanta=11,
        unmet_dissipation_quanta=0,
        externally_perturbed_body_receptor_count=0,
        receptor_ingress_sense_counts=(0,) * len(production.SENSE_ORDER),
        receptor_ingress_changing_count=0,
        receptor_ingress_quiescent_count=0,
        motor_unit_recruitments=(),
        articulatory_unit_recruitments=(),
        physical_frontier_routes=(),
        preceding_distinct_physical_frontier_routes=(),
        reached_and_foregone_physical_frontier_routes=(),
        working_causal_continuations=(),
        settled_working_frontier=(),
        physical_prediction_alternatives=(),
        body_consequence_transfers=(),
        affective_balance_trajectories=(),
        localized_fluid_chemistry=(),
        localized_metabolic_strain_evaluated_body_receptor_lineages=(),
        localized_metabolic_strain=(),
        organic_mosaic_relations=((receipts, (), (bond,), "33" * 32, (), ()),),
        recurrent_complete_neuron_fractal_count=2,
    )
    observed = SimpleNamespace(
        cognitive_mosaic_count=2,
        cognitive_trace_count=0,
        complete_neuron_count=43,
        developmental_resting_neuron_count=196_509,
        formation_activation_count=1,
        organism_tick=11,
        partial_cue_reassembly_count=1,
        endogenous_partial_cue_reassembly_count=0,
        energy_exhausted=False,
        dissipation_capacity_energy_zeptojoules=(100, 1),
        state_sha256="aa" * 32,
    )

    class Organism:
        committed = False

        @staticmethod
        def prepare_admitted(_episode, _intervals):
            return evidence

        def commit(self, token):
            assert token == "commit-token"
            self.committed = True
            return observed

    hop = production._commit_admitted_hop(Organism(), object(), [])

    assert hop["organic_mosaic_relations"][0]["structural_relation_sha256"] == (
        "33" * 32
    )
    assert hop["rest_recovered_neuron_count"] == 7
    assert hop["rest_drained_dissipation_quanta"] == 11
    assert hop["unmet_dissipation_quanta"] == 0
