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
        "organism_tick": tick,
        "receptor_ingress_sense_counts": {
            sense.value: 0 for sense in production.SENSE_ORDER
        },
        "receptor_ingress_changing_count": 0,
        "receptor_ingress_quiescent_count": 0,
        "motor_unit_recruitments": (),
        "physical_frontier_routes": (),
        "preceding_distinct_physical_frontier_routes": (),
        "reached_and_foregone_physical_frontier_routes": (),
        "working_causal_continuations": (),
        "settled_working_frontier": (),
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
    hops = iter((_hop(11, (relation,)), _hop(12, ())))
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
        physically_transitioned_neuron_count=2,
        metabolically_perturbed_body_receptor_count=0,
        receptor_ingress_sense_counts=(0,) * len(production.SENSE_ORDER),
        receptor_ingress_changing_count=0,
        receptor_ingress_quiescent_count=0,
        motor_unit_recruitments=(),
        physical_frontier_routes=(),
        preceding_distinct_physical_frontier_routes=(),
        reached_and_foregone_physical_frontier_routes=(),
        working_causal_continuations=(),
        settled_working_frontier=(),
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
