from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

from dsf_ai_service import native_production_app as serving


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
STATE_SHA = hashlib.sha256(b"native-state").hexdigest()


@dataclass
class _Observation:
    identity: str = IDENTITY
    organism_tick: int = 23_723_846
    fabric_bytes: int = 400
    fabric_generation: int = 13
    fabric_sha256: str = "a" * 64
    joint_field_count: int = 2
    joint_neuron_count: int = 96
    mounted_generation: int = 2
    state_bytes: int = 500
    state_sha256: str = STATE_SHA
    cognitive_mosaic_count: int = 0
    cognitive_ordinal: int = 0
    cognitive_trace_count: int = 0
    formation_activation_count: int = 0
    mosaic_of_mosaics_count: int = 0
    partial_cue_reassembly_count: int = 0
    endogenous_partial_cue_reassembly_count: int = 0
    physical_transition_claimed: bool = False
    python_callback_count: int = 0
    complete_neuron_count: int = 96
    developmental_resting_neuron_count: int = 0
    metabolically_perturbed_body_receptor_count: int = 0
    # Energy state (minimal feeding metabolism, 2026-08-05): the readiness
    # observation now carries the decoded energy physics; a zero-capacity
    # fixture body reports no mounted energy system.
    recovery_fuel_quanta: int = 0
    recovery_spent_quanta: int = 0
    recovery_heat_quanta: int = 0
    recovery_fuel_capacity_quanta: int = 0
    dissipated_quanta: int = 0
    dissipation_capacity_quanta: int = 0
    separated_elementary_charges: int = 0
    energy_exhausted: bool = False
    available_energy_zeptojoules: tuple[int, int] = (0, 1)
    spent_energy_zeptojoules: tuple[int, int] = (0, 1)
    thermal_energy_zeptojoules: tuple[int, int] = (0, 1)
    available_energy_capacity_zeptojoules: tuple[int, int] = (0, 1)
    dissipated_energy_zeptojoules: tuple[int, int] = (0, 1)
    dissipation_capacity_energy_zeptojoules: tuple[int, int] = (0, 1)


class _Organism:
    def __init__(self) -> None:
        self.readiness_calls = 0

    def readiness(self) -> _Observation:
        self.readiness_calls += 1
        return _Observation()

    def observe_reached_neuron_count_by_layer(self):
        return ((0, 27), (1, 27), (6, 42))

    def observe_retained_formations(self):
        return ()


@dataclass
class _Restored:
    organism: _Organism = field(default_factory=_Organism)


@dataclass
class _Admission:
    max_envelope_bytes: int = 1_000
    max_fabric_bytes: int = 900
    max_logical_peak_bytes: int = 3_000
    memory_boundary_source: str = "test"
    derivation: str = "three finite regions"


class _ReassemblingOrganism(_Organism):
    def readiness(self) -> _Observation:
        self.readiness_calls += 1
        return _Observation(
            partial_cue_reassembly_count=3,
            endogenous_partial_cue_reassembly_count=3,
            cognitive_mosaic_count=1,
        )


def _mount(monkeypatch) -> _Restored:
    restored = _Restored()
    monkeypatch.setattr(serving, "_restored", restored)
    monkeypatch.setattr(serving, "_last_transition_evidence", None)
    monkeypatch.setattr(serving, "_admission", _Admission())
    monkeypatch.setattr(
        serving,
        "_build_identity",
        lambda: {
            "git_sha": "b" * 40,
            "image_digest": "sha256:" + "c" * 64,
            "task_definition": "dsf-ai-task:900",
        },
    )
    serving._refresh_public_observation_cache()
    return restored


def test_interoception_requires_exact_local_body_receptor_evidence(
    monkeypatch,
) -> None:
    restored = _Restored()
    restored.organism.observe_reached_neuron_count_by_layer = lambda: (
        (0, 27),
        (1, 27),
        (5, 1),
        (6, 43),
        (8, 1),
    )
    monkeypatch.setattr(serving, "_restored", restored)
    monkeypatch.setattr(
        serving,
        "_last_transition_evidence",
        {
            "complete_neuron_fractal_count": 0,
            "totals": {"metabolically_perturbed_body_receptor_count": 1},
        },
    )
    monkeypatch.setattr(
        serving,
        "_admission",
        _Admission(),
    )
    monkeypatch.setattr(
        serving,
        "_build_identity",
        lambda: {
            "git_sha": "b" * 40,
            "image_digest": "sha256:" + "c" * 64,
            "task_definition": "dsf-ai-task:900",
        },
    )

    serving._refresh_public_observation_cache()
    interoception = json.loads(serving.native_observation().body)["sensory"][
        "interoception"
    ]
    assert interoception["available"] is True
    assert interoception["status"] == "local_cellular_metabolic_afference_observed"
    assert interoception["local_body_receptor_transition_count"] == 1
    assert interoception["dedicated_visceral_organ_afferents_mounted"] is False


def test_public_observation_is_cached_and_conditional(monkeypatch) -> None:
    restored = _mount(monkeypatch)
    assert restored.organism.readiness_calls == 1

    first = serving.native_observation()
    assert first.status_code == 200
    etag = first.headers["etag"]
    assert etag.startswith('"') and etag.endswith('"')
    assert restored.organism.readiness_calls == 1

    unchanged = serving.native_observation(if_none_match=etag)
    assert unchanged.status_code == 304
    assert unchanged.body == b""
    assert unchanged.headers["etag"] == etag
    assert restored.organism.readiness_calls == 1

    again = serving.native_observation()
    assert again.body == first.body
    assert restored.organism.readiness_calls == 1


def test_public_observation_reports_exact_sparse_attention_without_a_score(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    reached = ("01" * 16, 5, 1, "02" * 16, 8, 2, 0, 2)
    foregone = ("01" * 16, 5, 1, "03" * 16, 8, 3, 0, 0)
    monkeypatch.setattr(
        serving,
        "_last_transition_evidence",
        {
            "cognitive_mosaic_count": 1,
            "complete_neuron_fractal_count": 0,
            "hop_count": 1,
            "intake": "world-move",
            "physical_frontier_routes": (),
            "preceding_distinct_physical_frontier_routes": (
                reached,
                foregone,
            ),
            "reached_and_foregone_physical_frontier_routes": (
                reached,
                foregone,
            ),
            "totals": {
                "complete_neuron_fractal_count": 0,
                "current_cohort_evaluation_count": 1,
                "dsf_delivery_count": 2,
                "partial_cue_reassembly_count": 0,
                "physically_transitioned_neuron_count": 1,
                "recurrent_complete_neuron_fractal_count": 0,
            },
        },
    )

    serving._refresh_public_observation_cache()
    value = json.loads(serving.native_observation().body)

    attention = value["attention"]
    assert attention["available"] is True
    assert attention["status"] == "changing_sparse_physical_frontier_observed"
    assert attention["transported_route_count"] == 1
    assert attention["foregone_route_count"] == 1
    assert attention["attention_score_authority"] is False
    stage = value["experience_stage_ledger"]["stages"]["attention"]
    assert stage["available"] is True
    assert stage["status"] == attention["status"]


def test_public_observation_reports_bounded_working_cause_and_exact_settlement(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    first = ("01" * 16, "02" * 16, 0, 7)
    second = ("02" * 16, "03" * 16, 0, 5)
    monkeypatch.setattr(
        serving,
        "_last_transition_evidence",
        {
            "cognitive_mosaic_count": 0,
            "complete_neuron_fractal_count": 0,
            "hop_count": 3,
            "intake": "continuous-environment:test",
            "physical_frontier_routes": (),
            "preceding_distinct_physical_frontier_routes": (),
            "reached_and_foregone_physical_frontier_routes": (),
            "working_causal_continuations": ((first, second),),
            "settled_working_frontier": (second,),
            "totals": {
                "complete_neuron_fractal_count": 0,
                "current_cohort_evaluation_count": 3,
                "dsf_delivery_count": 3,
                "partial_cue_reassembly_count": 0,
                "physically_transitioned_neuron_count": 3,
                "recurrent_complete_neuron_fractal_count": 0,
            },
        },
    )

    serving._refresh_public_observation_cache()
    value = json.loads(serving.native_observation().body)
    working = value["working_causal_state"]
    assert working["available"] is True
    assert working["status"] == "bounded_working_cause_continued_and_settled"
    assert working["continuation"] == [list(first), list(second)]
    assert working["settled_transfer"] == list(second)
    assert working["retained_history_authority"] is False
    assert working["semantic_working_memory_authority"] is False


def test_public_observation_matches_both_browser_consumers(monkeypatch) -> None:
    _mount(monkeypatch)
    value = json.loads(serving.native_observation().body)

    assert value["schema"] == "guala.native.public_observation.v1"
    assert value["generation"] == value["organism"]["tick"]
    assert value["generation_state"] == {
        "fabric_generation": 13,
        "mounted_generation": 2,
        "organism_tick": 23_723_846,
        "state_sha256": STATE_SHA,
    }
    for name in (
        "identity",
        "organism",
        "sensory",
        "neuron_activity",
        "fractals",
        "formations",
        "recall",
        "energy",
        "cognitive_capital",
        "attention",
        "body",
        "autonomy",
        "articulation",
        "expression",
        "curriculum",
        "full_dsf",
        "persistence",
        "resources",
    ):
        section = value[name]
        assert isinstance(section["available"], bool)
        assert section["status"]
        assert section["reason"]

    # Auditory intake and the curriculum's card surface are genuinely
    # mounted now; every other modality must still refuse honestly.
    for modality in ("auditory", "visual"):
        assert value["sensory"][modality]["available"] is True
    for modality in (
        "text",
        "touch",
        "temperature",
        "smell",
        "taste",
        "vestibular",
        "proprioception",
        "interoception",
    ):
        assert value["sensory"][modality]["available"] is False

    assert value["autonomy"]["action_observed"] is False
    assert value["neuron_activity"]["reached_count_by_developmental_layer"] == [
        [0, 27],
        [1, 27],
        [6, 42],
    ]
    # The fixture observation carries zero formations; the projection must
    # report exactly what the observation says, not a hardwired zero.
    assert value["fractals"]["count"] == 0
    assert value["formations"]["mosaic_count"] == 0
    assert value["full_dsf"]["fields"] == [
        "D_k",
        "M_k",
        "R_rev_k",
        "U_star_k",
        "C_k",
        "P_k",
        "B_k",
    ]
    assert value["full_dsf"]["projection"] == "none"
    assert value["observation_contract"] == {
        "cached_per_committed_generation": True,
        "cognition_authority": False,
        "declared_loss": (
            "only committed native readiness facts and explicit unavailability "
            "are projected; no neuronal field body is present"
        ),
        "read_advances_organism": False,
    }
    receipt = value.pop("snapshot_receipt_sha256")
    assert receipt == serving._receipt(value)


def test_recall_section_is_truth_coupled_to_the_native_observation(
    monkeypatch,
) -> None:
    # Zero reassembly in the decoded state: recall must refuse honestly.
    _mount(monkeypatch)
    quiet = json.loads(serving.native_observation().body)["recall"]
    assert quiet["available"] is False
    assert (
        quiet["status"]
        == "no_endogenous_reassembly_in_last_committed_transition"
    )
    assert quiet["partial_cue_reassembly_count"] == 0

    # Nonzero reassembly in the decoded state: the projection must say so,
    # rather than reporting a hardwired zero.
    restored = _Restored(organism=_ReassemblingOrganism())
    monkeypatch.setattr(serving, "_restored", restored)
    serving._refresh_public_observation_cache()
    value = json.loads(serving.native_observation().body)
    assert value["recall"]["available"] is True
    assert value["recall"]["status"] == "endogenous_physical_reassembly_observed"
    assert value["recall"]["partial_cue_reassembly_count"] == 3
    assert value["formations"]["mosaic_count"] == 1


def test_capabilities_are_truth_coupled_to_mounted_routes(monkeypatch) -> None:
    _mount(monkeypatch)
    value = json.loads(serving.native_observation().body)
    assert value["capabilities"]
    served_paths = {route.path for route in serving.app.routes}
    mounted = {
        name: record
        for name, record in value["capabilities"].items()
        if record["available"] is True
    }
    # The mounted set is exactly the visual/media ingresses and curriculum
    # routes available under this fixture's explicit environment. Audio and
    # nutrition remain unavailable here.
    assert set(mounted) == {
        "book",
        "camera",
        "curriculum",
        "gutenberg",
        "pdf",
        "picture",
        "text_visual",
    }
    for record in mounted.values():
        assert record["status"]
        assert record["endpoint"] in served_paths
        assert record["reason"]
    for name, record in value["capabilities"].items():
        if name in mounted:
            continue
        assert record["available"] is False
        assert record["endpoint"] is None
        assert record["status"]
        assert record["reason"]


def test_native_public_surface_contains_no_owner_or_legacy_observation_route(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    body = serving.native_observation().body.decode("ascii")
    assert "owner" not in body.lower()
    paths = {route.path for route in serving.app.routes}
    assert "/api/v1/guala/native-observation" in paths
    assert "/api/v1/gualaloom/observation" not in paths
