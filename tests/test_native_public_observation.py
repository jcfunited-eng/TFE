from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import threading

from fastapi import HTTPException
import pytest

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
    articulated_body_state_bytes: int = 195
    articulated_body_state_sha256: str = "b" * 64
    articulated_body_proprioception_initialized: bool = True
    articulated_body_lung_air_microlitres: int = 2_000_000

    @property
    def articulated_body_axes(self):
        return [
            (index, f"axis_{index}", "millidegree", 0, -1, 0, 1)
            for index in range(37)
        ]

    @property
    def articulated_body_vocal_tract_areas_square_millimetres(self):
        return [100] * 8


class _Organism:
    def __init__(self) -> None:
        self.readiness_calls = 0

    def readiness(self) -> _Observation:
        self.readiness_calls += 1
        return _Observation()

    def observe_reached_neuron_count_by_layer(self):
        return ((0, 27), (1, 27), (6, 42))

    def observe_reached_source_site_count(self, _sensor_id: str, _substream: str):
        return 0

    def observe_retained_formations(self):
        return ()

    def observe_retained_formation_recurrence_evidence(self):
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

    def observe_retained_formation_recurrence_evidence(self):
        return (("d" * 64, ("01" * 16,), "internally_simulated"),)


def _mount(monkeypatch) -> _Restored:
    restored = _Restored()
    monkeypatch.setattr(serving, "_restored", restored)
    monkeypatch.setattr(serving, "_last_transition_evidence", None)
    monkeypatch.setattr(serving, "_last_tested_prediction_evidence", None)
    monkeypatch.setattr(serving, "_last_tested_affective_balance_evidence", None)
    monkeypatch.setattr(
        serving, "_last_tested_localized_fluid_chemistry_evidence", None
    )
    monkeypatch.setattr(serving, "_last_causal_cross_context_use_evidence", None)
    monkeypatch.setattr(serving, "_last_intrinsic_curiosity_evidence", None)
    monkeypatch.setattr(serving, "_sensorimotor_play_candidate", None)
    monkeypatch.setattr(serving, "_last_sensorimotor_play_evidence", None)
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


def test_runtime_proof_is_the_same_committed_snapshot_and_never_borrows_cognition(
    monkeypatch,
) -> None:
    restored = _mount(monkeypatch)
    expected = json.loads(serving._runtime_proof_body)

    def forbidden_native_read():
        raise AssertionError("read-only runtime proof borrowed native cognition")

    monkeypatch.setattr(restored.organism, "readiness", forbidden_native_read)
    monkeypatch.setattr(
        restored.organism,
        "observe_retained_formations",
        forbidden_native_read,
    )

    responses: list[object] = []
    failures: list[BaseException] = []

    def read_while_transition_boundary_is_held() -> None:
        try:
            responses.append(serving.ready_guala())
        except BaseException as error:
            failures.append(error)

    reader = threading.Thread(
        target=read_while_transition_boundary_is_held,
        daemon=True,
    )
    with serving._transition_lock:
        reader.start()
        reader.join(timeout=0.5)
        assert not reader.is_alive()

    assert failures == []
    assert len(responses) == 1
    ready = responses[0]
    assert ready.status_code == 200
    assert json.loads(ready.body) == expected
    assert ready.headers["cache-control"] == "private, no-store"

    proof = serving.runtime_proof()
    assert proof.body == ready.body
    assert restored.organism.readiness_calls == 1


def test_public_projection_failure_does_not_hide_native_readiness(monkeypatch) -> None:
    restored = _mount(monkeypatch)

    def broken_public_projection(*_args, **_kwargs):
        raise RuntimeError("optional public projection failed")

    monkeypatch.setattr(
        serving,
        "_build_public_observation_from_snapshot",
        broken_public_projection,
    )

    serving._refresh_public_observation_cache()

    ready = serving.ready_guala()
    assert ready.status_code == 200
    assert json.loads(ready.body)["organism_tick"] == _Observation().organism_tick
    assert restored.organism.readiness_calls == 2
    assert serving._public_observation_body is None
    assert serving._public_observation_etag is None
    with pytest.raises(HTTPException) as unavailable:
        serving.native_observation()
    assert unavailable.value.status_code == 503


def test_refresh_reuses_startup_build_identity_without_runtime_metadata(
    monkeypatch,
) -> None:
    restored = _mount(monkeypatch)
    stable_identity = {
        "git_sha": "d" * 40,
        "image_digest": "sha256:" + "e" * 64,
        "task_definition": "dsf-ai-task:901",
    }
    monkeypatch.setattr(serving, "_runtime_build_identity", stable_identity)

    def forbidden_runtime_metadata_read():
        raise AssertionError("build identity was reread after startup")

    monkeypatch.setattr(serving, "_build_identity", forbidden_runtime_metadata_read)

    serving._refresh_public_observation_cache()

    ready = json.loads(serving.ready_guala().body)
    assert ready["git_sha"] == "d" * 40
    assert ready["image_digest"] == "sha256:" + "e" * 64
    assert ready["task_definition"] == "dsf-ai-task:901"
    assert restored.organism.readiness_calls == 2


def test_observer_keeps_unbounded_exact_energy_coordinates_native(
    monkeypatch,
) -> None:
    huge = 10**5000

    class HugeEnergyOrganism(_Organism):
        def readiness(self) -> _Observation:
            self.readiness_calls += 1
            return _Observation(
                available_energy_zeptojoules=(huge, 1),
                spent_energy_zeptojoules=(huge, 1),
                thermal_energy_zeptojoules=(huge, 1),
                available_energy_capacity_zeptojoules=(huge, 1),
                dissipated_energy_zeptojoules=(huge, 1),
                dissipation_capacity_energy_zeptojoules=(huge, 1),
                separated_elementary_charges=huge,
            )

    restored = _Restored(organism=HugeEnergyOrganism())
    monkeypatch.setattr(serving, "_restored", restored)
    monkeypatch.setattr(serving, "_admission", _Admission())
    monkeypatch.setattr(serving, "_runtime_build_identity", None)
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

    ready = json.loads(serving.ready_guala().body)
    assert ready["ready"] is True
    assert "available_energy_zeptojoules" not in ready["native_resident"]
    observed = json.loads(serving.native_observation().body)
    assert observed["energy"]["available"] is True
    assert observed["energy"]["exact_coordinates_resident"] is True
    assert observed["energy"]["exact_coordinates_transported"] is False
    assert "available_energy_zeptojoules" not in observed["energy"]


def test_causal_observer_keeps_unbounded_contact_coordinates_native(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    huge = 10**5000
    state_sha = "d" * 64
    monkeypatch.setattr(
        serving,
        "_last_causal_cross_context_use_evidence",
        {
            "action": {
                "body_effector_binding_count": 1,
                "causal_intent_receipt_sha256": "a" * 64,
                "root_motion": False,
            },
            "changed_contact_channel_state": {
                "change_organism_tick": 24,
                "contact_cognitive_ordinal": 24,
                "left_lineage": "01" * 16,
                "right_lineage": "02" * 16,
                "parallel_ordinal": 0,
                "predecessor_state": (huge, (huge, 1), (1, huge)),
                "successor_state": (huge + 1, (huge, 1), (2, huge)),
            },
            "formation_receipt_sha256": "b" * 64,
            "intake": "continuous-environment:bounded-observer",
            "organism_tick": 25,
            "sensed_consequence": {
                "body_proprioceptive_source_count": 1,
                "successor_organism_tick": 25,
                "successor_state_sha256": state_sha,
            },
            "state_sha256": state_sha,
        },
    )

    serving._refresh_public_observation_cache()

    observed = json.loads(serving.native_observation().body)
    contact = observed["body"]["prior_causal_cross_context_use"][
        "changed_contact_channel_state"
    ]
    assert contact["exact_state_changed"] is True
    assert contact["exact_state_coordinates_resident"] is True
    assert contact["exact_state_coordinates_transported"] is False
    assert contact["resident_state_sha256"] == state_sha
    assert "predecessor_state" not in contact
    assert "successor_state" not in contact


def test_public_observer_keeps_exact_local_energy_coordinates_native(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    huge = 10**5000
    lineage = "10" * 16
    association = (7, ("07" * 16, lineage, 0, huge))
    body = (8, ("08" * 16, lineage, 0, huge))
    gradient = (
        9,
        -huge,
        -(huge - 2),
        -(huge - 1),
        2,
        2,
        0,
        (huge, 1),
        (huge, 1),
        (huge, 1),
    )
    plasticity = (
        9,
        huge,
        huge,
        (huge, 1),
        (huge, 1),
        (huge - 1, 1),
        (huge, 1),
        (huge, 1),
        ((huge, 1), (0, 1), (0, 1)),
        ((huge - 1, 1), (1, 1), (0, 1)),
    )
    monkeypatch.setattr(
        serving,
        "_last_tested_affective_balance_evidence",
        {
            "affective_balance_trajectories": (
                (lineage, 10, 4, association, body, gradient, plasticity),
            ),
            "intake": "continuous-environment:bounded-observer",
            "organism_tick": 42,
            "state_sha256": "d" * 64,
        },
    )
    localized = (
        lineage,
        10,
        4,
        9,
        (250_000, (huge, 1), 1, 1, 1, 0, 0),
        (-huge, -(huge - 2), 0, huge, 2, huge - 2, 0, -2),
        (
            ((huge, 1), (0, 1), (0, 1)),
            ((huge - 1, 1), (1, 1), (0, 1)),
            (1, 1),
        ),
    )
    monkeypatch.setattr(
        serving,
        "_last_tested_localized_fluid_chemistry_evidence",
        {
            "intake": "continuous-environment:bounded-observer",
            "localized_fluid_chemistry": (localized,),
            "organism_tick": 42,
            "state_sha256": "d" * 64,
        },
    )

    serving._refresh_public_observation_cache()

    body = serving.native_observation().body
    observed = json.loads(body)
    assert b'"numerator"' not in body
    assert observed["affective_balance"]["available"] is True
    assert observed["affective_balance"]["trajectory"][
        "localized_gradient_settlement"
    ]["exact_coordinates_transported"] is False
    assert observed["localized_fluid_chemistry"]["exact_conservation"] is True
    assert observed["localized_fluid_chemistry"]["reservoir_energy"][
        "exact_coordinates_transported"
    ] is False


def test_public_observation_counts_every_fractal_emitted_by_the_experience(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    emitted = (
        {
            "neuron_lineage": "01" * 16,
            "organism_tick": 24,
            "predecessor_organism_tick": 23,
            "sparse_retained_delta": (("psi-winding", 0, 1),),
        },
        {
            "neuron_lineage": "02" * 16,
            "organism_tick": 25,
            "predecessor_organism_tick": 24,
            "sparse_retained_delta": (("receptor-quantum-residue", 0, 1),),
        },
    )
    monkeypatch.setattr(
        serving,
        "_last_transition_evidence",
        {
            # The final hop is quiet, but two earlier hops of this same
            # admitted experience emitted exact retained physical deltas.
            "complete_neuron_fractal_count": 0,
            "emitted_neuron_fractals": emitted,
            "hop_count": 3,
            "intake": "continuous-environment:test",
            "totals": {
                "complete_neuron_fractal_count": 2,
                "current_cohort_evaluation_count": 3,
                "dsf_delivery_count": 3,
                "partial_cue_reassembly_count": 0,
                "physically_transitioned_neuron_count": 3,
                "recurrent_complete_neuron_fractal_count": 0,
            },
        },
    )

    serving._refresh_public_observation_cache()
    fractals = json.loads(serving.native_observation().body)["fractals"]

    assert fractals["formed_in_last_experience"] == len(emitted)
    assert "formed_evidence_in_last_experience" not in fractals


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


def test_experience_stage_ledger_reports_native_action_and_its_consequence(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    receipt = "9" * 64
    monkeypatch.setattr(
        serving,
        "_last_transition_evidence",
        {
            "cognitive_mosaic_count": 0,
            "complete_neuron_fractal_count": 0,
            "hop_count": 1,
            "intake": "continuous-environment:test",
            "attention_motor_binding": {"matched_attention_route_count": 7},
            "motor_action": {
                "causal_intent_receipt_sha256": receipt,
                "disposition": "applied",
                "moved": True,
                "signed_yaw_millidegrees": -6,
                "sensory_consequence": {
                    "action_receipt_sha256": receipt,
                    "organism_tick": 24,
                },
            },
            "totals": {
                "complete_neuron_fractal_count": 0,
                "current_cohort_evaluation_count": 1,
                "dsf_delivery_count": 1,
                "partial_cue_reassembly_count": 0,
                "physically_transitioned_neuron_count": 1,
                "recurrent_complete_neuron_fractal_count": 0,
            },
        },
    )

    serving._refresh_public_observation_cache()
    stages = json.loads(serving.native_observation().body)[
        "experience_stage_ledger"
    ]["stages"]

    assert stages["intent"]["status"] == (
        "native_attention_motor_preparation_observed"
    )
    assert stages["action"]["status"] == "native_body_action_applied"
    assert stages["consequence"]["status"] == (
        "native_action_consequence_returned"
    )
    assert all(
        stages[name]["available"] is True
        for name in ("intent", "action", "consequence")
    )


def test_experience_stage_ledger_does_not_turn_current_absence_into_never(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    stages = json.loads(serving.native_observation().body)[
        "experience_stage_ledger"
    ]["stages"]

    for name in ("intent", "action", "consequence"):
        assert stages[name]["available"] is False
        assert stages[name]["status"] == "not_observed_in_this_experience"
        assert "never" not in stages[name]["summary"].lower()


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


def test_public_observation_reports_prediction_only_after_later_body_test(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    intrinsic_cause = "01" * 16
    first = ((intrinsic_cause, "02" * 16, 0, 7), ("02" * 16, "04" * 16, 0, 5))
    second = ((intrinsic_cause, "03" * 16, 0, 6), ("03" * 16, "05" * 16, 0, 4))
    consequence = ("06" * 16, "04" * 16, 0, 3)
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
            "working_causal_continuations": (),
            "settled_working_frontier": (),
            "physical_prediction_alternatives": (first, second),
            "body_consequence_transfers": (consequence,),
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
    prediction = json.loads(serving.native_observation().body)["prediction"]
    assert prediction["available"] is True
    assert prediction["agreeing_alternative_indices"] == [0]
    assert prediction["contradicted_alternative_indices"] == []
    assert prediction["planner_authority"] is False
    assert prediction["score_authority"] is False


def test_public_observation_preserves_reverse_body_relation_as_contradiction(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    intrinsic_cause = "01" * 16
    first = ((intrinsic_cause, "02" * 16, 0, 7), ("02" * 16, "04" * 16, 0, 5))
    second = ((intrinsic_cause, "03" * 16, 0, 6), ("03" * 16, "05" * 16, 0, 4))
    consequence = ("04" * 16, "06" * 16, 0, 3)
    monkeypatch.setattr(
        serving,
        "_last_transition_evidence",
        {
            "physical_prediction_alternatives": (first, second),
            "body_consequence_transfers": (consequence,),
        },
    )
    prediction = serving._physical_prediction_record()
    assert prediction["available"] is True
    assert prediction["status"] == "physical_alternatives_contradicted_by_later_body_consequence"
    assert prediction["agreeing_alternative_indices"] == ()
    assert prediction["contradicted_alternative_indices"] == (0,)


def test_public_observation_does_not_call_an_unrelated_body_relation_contradiction(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    intrinsic_cause = "01" * 16
    first = ((intrinsic_cause, "02" * 16, 0, 7), ("02" * 16, "04" * 16, 0, 5))
    second = ((intrinsic_cause, "03" * 16, 0, 6), ("03" * 16, "05" * 16, 0, 4))
    consequence = ("07" * 16, "06" * 16, 0, 3)
    monkeypatch.setattr(
        serving,
        "_last_transition_evidence",
        {
            "physical_prediction_alternatives": (first, second),
            "body_consequence_transfers": (consequence,),
        },
    )
    prediction = serving._physical_prediction_record()
    assert prediction["available"] is False
    assert prediction["status"] == "body_consequence_did_not_reach_predicted_relation"


def test_public_observation_retains_exactly_one_tested_prediction_witness(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    intrinsic_cause = "01" * 16
    first = ((intrinsic_cause, "02" * 16, 0, 7), ("02" * 16, "04" * 16, 0, 5))
    second = ((intrinsic_cause, "03" * 16, 0, 6), ("03" * 16, "05" * 16, 0, 4))
    tested = {
        "physical_prediction_alternatives": (first, second),
        "body_consequence_transfers": (("04" * 16, "06" * 16, 0, 3),),
        "intake": "world-move",
        "organism_tick": 41,
        "state_sha256": "d" * 64,
    }
    monkeypatch.setattr(serving, "_last_tested_prediction_evidence", tested)
    monkeypatch.setattr(
        serving,
        "_last_transition_evidence",
        {
            "cognitive_mosaic_count": 0,
            "complete_neuron_fractal_count": 0,
            "hop_count": 8,
            "physical_prediction_alternatives": (first, second),
            "body_consequence_transfers": (),
            "intake": "continuous-environment:later",
            "organism_tick": 49,
            "physical_frontier_routes": (),
            "preceding_distinct_physical_frontier_routes": (),
            "reached_and_foregone_physical_frontier_routes": (),
            "state_sha256": "e" * 64,
            "working_causal_continuations": (),
            "settled_working_frontier": (),
            "totals": {
                "complete_neuron_fractal_count": 0,
                "current_cohort_evaluation_count": 8,
                "dsf_delivery_count": 8,
                "partial_cue_reassembly_count": 0,
                "physically_transitioned_neuron_count": 8,
                "recurrent_complete_neuron_fractal_count": 0,
            },
        },
    )
    serving._refresh_public_observation_cache()
    prediction = json.loads(serving.native_observation().body)["prediction"]
    assert prediction["available"] is True
    assert prediction["status"] == "physical_alternatives_contradicted_by_later_body_consequence"
    assert prediction["evidence_scope"] == "latest_tested_physical_event"
    assert prediction["evidence_organism_tick"] == 41
    assert prediction["evidence_state_sha256"] == "d" * 64
    assert prediction["evidence_intake"] == "world-move"


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
        "play",
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


def test_completed_sensorimotor_play_reaches_public_observation_and_capital(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    huge = 10**5000
    evidence = {
        "activity": "sensorimotor_body_yaw",
        "changed_world_context": True,
        "evidence_receipt_sha256": "e" * 64,
        "first_episode": {
            "action_causal_intent_receipt_sha256": "1" * 64,
            "affective_body_participation": {
                "active_contact_predecessor_state": (huge, (huge, 1)),
                "active_contact_successor_state": (huge + 1, (huge, 1)),
                "trajectory_receipt_sha256": "3" * 64,
            },
            "metabolic_overload_exclusion": {
                "dissipation_capacity_energy_zeptojoules": (huge, 1),
                "witness_receipt_sha256": "5" * 64,
            },
            "localized_metabolic_strain": {
                "localized_nonzero_strain_count": 0,
                "localized_nonzero_strain": ((huge, huge),),
                "witness_receipt_sha256": "7" * 64,
            },
            "signed_yaw_millidegrees": -58,
            "world_revision": 40,
        },
        "formation_receipt_sha256": "f" * 64,
        "movement_ceased_before_return": True,
        "return_episode": {
            "action_causal_intent_receipt_sha256": "2" * 64,
            "affective_body_participation": {
                "active_contact_predecessor_state": (huge, (huge, 1)),
                "active_contact_successor_state": (huge + 1, (huge, 1)),
                "trajectory_receipt_sha256": "4" * 64,
            },
            "metabolic_overload_exclusion": {
                "dissipation_capacity_energy_zeptojoules": (huge, 1),
                "witness_receipt_sha256": "6" * 64,
            },
            "localized_metabolic_strain": {
                "localized_nonzero_strain_count": 0,
                "localized_nonzero_strain": ((huge, huge),),
                "witness_receipt_sha256": "8" * 64,
            },
            "signed_yaw_millidegrees": -40,
            "world_revision": 41,
        },
        "return_gap_organism_ticks": 11,
        "varied_displacement": True,
    }
    monkeypatch.setattr(serving, "_last_sensorimotor_play_evidence", evidence)
    serving._refresh_public_observation_cache()

    value = json.loads(serving.native_observation().body)
    play = value["play"]
    assert play["available"] is True
    assert play["status"] == "sensorimotor_play_observed"
    assert play["formation_receipt_sha256"] == "f" * 64
    assert play["first_episode"]["signed_yaw_millidegrees"] == -58
    assert play["return_episode"]["signed_yaw_millidegrees"] == -40
    assert "active_contact_predecessor_state" not in play["first_episode"][
        "affective_body_participation"
    ]
    assert (
        "dissipation_capacity_energy_zeptojoules"
        not in play["first_episode"]["metabolic_overload_exclusion"]
    )
    assert "localized_nonzero_strain" not in play["first_episode"][
        "localized_metabolic_strain"
    ]
    assert play["affective_engagement"]["available"] is True
    assert play["overload_exclusion"]["available"] is True
    assert play["distress_exclusion"]["available"] is True
    assert play["distress_exclusion"]["exclusion_scope"] == (
        "localized_metabolic_strain_only"
    )
    assert play["fun"]["available"] is True
    assert play["fun"]["status"] == "positive_engagement_trajectory_observed"
    assert play["social_joy"]["available"] is False
    assert play["laughter"]["available"] is False

    cells = {
        (credit["capability"], credit["dimension"])
        for credit in value["cognitive_capital"]["credits"]
    }
    assert ("Play and exploration", "autonomous_use") in cells
    assert ("Play and exploration", "transfer") in cells

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
    assert value["neuron_activity"]["reached_count_by_developmental_layer"] == []
    # The fixture observation carries zero formations; the projection must
    # report exactly what the observation says, not a hardwired zero.
    assert value["fractals"]["count"] is None
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
    assert value["recall"]["retained_formation_recurrence_evidence"] == []
    assert value["formations"]["mosaic_count"] == 1


def test_affective_balance_requires_ordered_local_recovery(monkeypatch) -> None:
    _mount(monkeypatch)
    lineage = "10" * 16
    association = (7, ("07" * 16, lineage, 0, 3))
    body = (8, ("08" * 16, lineage, 0, 2))
    gradient = (9, -5, -3, -4, 2, 2, 0, (11, 2), (13, 2), (1, 1))
    plasticity = (
        9,
        2,
        2,
        (1, 8),
        (7, 8),
        (0, 1),
        (4, 3),
        (4, 3),
        ((1, 1), (0, 1), (0, 1)),
        ((7, 8), (1, 8), (0, 1)),
    )
    monkeypatch.setattr(
        serving,
        "_last_tested_affective_balance_evidence",
        {
            "affective_balance_trajectories": (
                (lineage, 10, 4, association, body, gradient, plasticity),
            ),
            "intake": "unattended-world",
            "organism_tick": 42,
            "state_sha256": "d" * 64,
        },
    )
    serving._refresh_public_observation_cache()

    value = json.loads(serving.native_observation().body)["affective_balance"]

    assert value["available"] is True
    assert value["status"] == (
        "body_association_perturbation_followed_by_local_gradient"
    )
    assert value["trajectory"]["neuron_layer"] == 10
    assert value["trajectory"]["association_influence"]["source_layer"] == 7
    assert value["trajectory"]["body_influence"]["source_layer"] == 8
    assert value["trajectory"]["localized_gradient_settlement"][
        "cognitive_ordinal"
    ] == 9
    assert value["trajectory"]["localized_recovery_settlement"][
        "retained_support_changed"
    ] is False
    assert value["trajectory"]["localized_recovery_settlement"][
        "exact_coordinates_resident"
    ] is True
    assert value["trajectory"]["localized_recovery_settlement"][
        "exact_coordinates_transported"
    ] is False
    assert (
        "successor_plastic_rest_length_nanometres"
        not in value["trajectory"]["localized_recovery_settlement"]
    )
    assert value["named_emotion_authority"] is False
    assert value["python_decision_authority"] is False


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
