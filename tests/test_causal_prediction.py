from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.glew_runtime.model import receipt_sha256
from dsf_ai_service.substrate.causal_prediction import (
    CausalPredictionAuthority,
    PredictionWitness,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from tests.native_joint_occurrence_support import joint_occurrences_for


def _settlement(
    assembly_id: str,
    *,
    frequency: int,
    routing_chis: tuple[int, ...] = (),
):
    count = 96
    signal = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="prediction-test-camera",
        substream_id="fixation-0",
        topology_index=0,
        coordinates=(NativeAxisCoordinate("fixation", "center"),),
        physical_quantity="light-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(Fraction(index, 512) for index in range(count)),
        normalized_signal=tuple(
            math.sin(2 * math.pi * frequency * index / 512)
            for index in range(count)
        ),
        phase_turns=tuple(Fraction(index // 12) for index in range(count)),
    )
    built = build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=Fraction(0),
        source_time_end=Fraction(count, 512),
        observed_substreams={PhysicalSense.SIGHT: (signal,)}, occurrences=joint_occurrences_for({PhysicalSense.SIGHT: (signal,)}),
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SIGHT
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=routing_chis,
        source_tags=(f"source:{assembly_id}",),
    )


def _teach(
    authority: CausalPredictionAuthority,
    before_frequency: int,
    after_frequency: int,
    label: str,
) -> None:
    authority.start(
        _settlement(f"{label}-before", frequency=before_frequency)
    )
    authority.advance(
        _settlement(f"{label}-after", frequency=after_frequency)
    )
    authority.stop()


def test_exact_full_field_transition_predicts_before_and_verifies_next() -> None:
    authority = CausalPredictionAuthority(authority_key="prediction-exact-key")
    _teach(authority, 8, 13, "learn")

    context = _settlement("live-context", frequency=8, routing_chis=(91,))
    prediction = authority.start(context)
    assert prediction.status == "predicted"
    assert len(prediction.candidates) == 1
    expected = _settlement("expected-shape", frequency=13, routing_chis=(3,))
    assert (
        prediction.candidates[0].target_structural_fingerprint
        == expected.structural_fingerprint
    )

    step = authority.advance(expected)
    assert step.resolution.prediction_status == "predicted"
    assert step.resolution.verification == "predicted_match"
    assert (
        step.resolution.attempt_receipt_sha256
        == prediction.authority_receipt_sha256
    )
    assert (
        step.transition.from_structural_fingerprint
        == context.structural_fingerprint
    )
    assert step.transition.to_structural_fingerprint == expected.structural_fingerprint
    assert authority.status()["relations"] == 1


def test_routing_chi_is_not_prediction_identity_but_one_field_change_is() -> None:
    left = _settlement("identity-left", frequency=10, routing_chis=(1, 7))
    same = _settlement("identity-same", frequency=10, routing_chis=(88,))
    changed = _settlement("identity-changed", frequency=40, routing_chis=(1, 7))
    assert left.structural_fingerprint == same.structural_fingerprint
    assert left.routing_chis != same.routing_chis
    assert left.structural_fingerprint != changed.structural_fingerprint

    authority = CausalPredictionAuthority(authority_key="prediction-identity-key")
    authority.start(left)
    authority.advance(_settlement("identity-target", frequency=21))
    authority.stop()
    assert authority.start(same).status == "predicted"
    authority.stop()
    assert authority.start(changed).status == "unknown"


def test_unknown_ambiguous_and_novel_outcomes_remain_exact() -> None:
    authority = CausalPredictionAuthority(authority_key="prediction-branches-key")
    first_unknown = authority.start(_settlement("unknown-a", frequency=6))
    assert first_unknown.status == "unknown"
    unknown_step = authority.advance(_settlement("unknown-b", frequency=7))
    assert unknown_step.resolution.verification == "unknown_observed"
    authority.stop()

    _teach(authority, 30, 31, "branch-one")
    _teach(authority, 30, 32, "branch-two")
    ambiguous = authority.start(_settlement("branch-live", frequency=30))
    assert ambiguous.status == "ambiguous"
    assert len(ambiguous.candidates) == 2
    candidate_step = authority.advance(
        _settlement("branch-candidate", frequency=31)
    )
    assert (
        candidate_step.resolution.verification
        == "ambiguous_candidate_observed"
    )
    authority.stop()

    ambiguous = authority.start(_settlement("branch-live-novel", frequency=30))
    novel_step = authority.advance(_settlement("branch-novel", frequency=33))
    assert novel_step.resolution.verification == "ambiguous_novel_observed"
    assert authority.status()["ambiguous_contexts"] == 1


def test_one_exact_prediction_reports_mismatch_without_score_or_nearest_match() -> None:
    authority = CausalPredictionAuthority(authority_key="prediction-mismatch-key")
    _teach(authority, 34, 35, "mismatch-learn")
    prediction = authority.start(_settlement("mismatch-context", frequency=34))
    assert prediction.status == "predicted"
    step = authority.advance(_settlement("mismatch-actual", frequency=90))
    assert step.resolution.verification == "predicted_mismatch"
    assert step.resolution.actual_structural_fingerprint != (
        prediction.candidates[0].target_structural_fingerprint
    )


def test_repeated_cycles_compact_without_lifetime_attempt_or_event_index() -> None:
    authority = CausalPredictionAuthority(
        authority_key="prediction-compact-key",
        relation_capacity=1,
        evidence_capacity=8,
    )
    sizes = []
    for index in range(20):
        authority.start(
            _settlement(f"compact-before-{index}", frequency=40)
        )
        authority.advance(
            _settlement(f"compact-after-{index}", frequency=41)
        )
        authority.stop()
        status = authority.status()
        assert status["relations"] == 1
        assert status["evidence"] <= 4
        assert status["active_episode"] is False
        sizes.append(len(authority.encoded_snapshot()))
    assert max(sizes[1:]) - min(sizes[1:]) < 128
    payload = json.loads(
        base64.b64decode(
            json.loads(authority.encoded_snapshot())["payload_base64"]
        )
    )
    assert "attempts" not in payload
    assert "events" not in payload
    assert payload["pending"] is None


def test_unique_relation_capacity_replaces_oldest_and_runs_past_capacity() -> None:
    authority = CausalPredictionAuthority(
        authority_key="prediction-capacity-key",
        relation_capacity=3,
        evidence_capacity=20,
    )
    evictions = []
    for index in range(12):
        authority.start(
            _settlement(f"capacity-before-{index}", frequency=50 + index)
        )
        step = authority.advance(
            _settlement(f"capacity-after-{index}", frequency=100 + index)
        )
        authority.stop()
        if step.evicted_relation_id is not None:
            evictions.append(step.evicted_relation_id)
        assert authority.status()["relations"] <= 3
        assert authority.status()["evidence"] <= 20
    assert len(evictions) == 9
    assert len(authority.relation_records()) == 3


def test_snapshot_hmac_restore_and_tamper_rejection_are_atomic() -> None:
    authority = CausalPredictionAuthority(authority_key="prediction-state-key")
    _teach(authority, 14, 15, "state")
    authority.start(_settlement("state-active", frequency=14))
    snapshot = authority.encoded_snapshot()

    restored = CausalPredictionAuthority(authority_key="prediction-state-key")
    restored.restore_encoded(snapshot)
    assert restored.encoded_snapshot() == snapshot
    assert restored.current_prediction().status == "predicted"

    wrong_key = CausalPredictionAuthority(authority_key="wrong-state-key")
    with pytest.raises(ValueError, match="state HMAC changed"):
        wrong_key.restore_encoded(snapshot)

    envelope = json.loads(snapshot)
    envelope["authority_hmac_sha256"] = hashlib.sha256(b"tampered").hexdigest()
    tampered = json.dumps(
        envelope,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    before = restored.encoded_snapshot()
    with pytest.raises(ValueError, match="state HMAC changed"):
        restored.restore_encoded(tampered)
    assert restored.encoded_snapshot() == before

    invalid = replace(
        _settlement("state-invalid", frequency=15),
        structural_fingerprint="0" * 64,
    )
    with pytest.raises(Exception):
        restored.advance(invalid)
    assert restored.encoded_snapshot() == before


def test_encoded_byte_boundary_rolls_back_the_entire_failed_mutation() -> None:
    authority = CausalPredictionAuthority(
        authority_key="prediction-rollback-key",
        relation_capacity=1,
        evidence_capacity=8,
        encoded_state_capacity=1024,
    )
    before = authority.encoded_snapshot()
    with pytest.raises(RuntimeError, match="encoded state capacity is full"):
        authority.start(_settlement("rollback-context", frequency=19))
    assert authority.encoded_snapshot() == before
    assert authority.status() == {
        "active_episode": False,
        "ambiguous_contexts": 0,
        "evidence": 0,
        "latest_verification": None,
        "pending_status": None,
        "relations": 0,
    }

def test_concurrent_duplicate_advance_has_one_commit_and_consistent_state() -> None:
    authority = CausalPredictionAuthority(authority_key="prediction-thread-key")
    _teach(authority, 17, 18, "thread-learn")
    authority.start(_settlement("thread-context", frequency=17))
    actual = _settlement("thread-actual", frequency=18)

    def advance_once():
        try:
            return authority.advance(actual).resolution.verification
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _index: advance_once(), range(2)))

    assert outcomes.count("predicted_match") == 1
    assert outcomes.count("causal prediction cannot advance the same settlement") == 1
    assert authority.status()["relations"] <= 2
    snapshot = authority.encoded_snapshot()
    restored = CausalPredictionAuthority(authority_key="prediction-thread-key")
    restored.restore_encoded(snapshot)
    assert restored.encoded_snapshot() == snapshot


def test_full_settlement_payload_and_explicit_six_sense_fields_are_retained() -> None:
    authority = CausalPredictionAuthority(authority_key="prediction-field-key")
    _teach(authority, 22, 23, "field")
    records = authority.relation_records()
    assert len(records) == 1
    evidence = records[0]["latest_evidence"]
    snapshot = json.loads(
        base64.b64decode(
            json.loads(authority.encoded_snapshot())["payload_base64"]
        )
    )
    witnesses = {
        item["settlement_receipt_sha256"]: item
        for item in snapshot["evidence"]
    }
    for receipt in (
        evidence["from_settlement_receipt_sha256"],
        evidence["to_settlement_receipt_sha256"],
    ):
        payload = json.loads(
            base64.b64decode(witnesses[receipt]["settlement_payload_base64"])
        )
        assert [item["sense"] for item in payload["interpretations"]] == [
            item.value for item in SENSE_ORDER
        ]
        observed = next(
            item for item in payload["interpretations"] if item["state"] == "observed"
        )
        fields = observed["substreams"][0]["field_tuples"][0]["fields"]
        assert [name for name, _value in fields] == [
            "D_k",
            "M_k",
            "R_rev_k",
            "U_star_k",
            "C_k",
            "P_k",
            "B_k",
        ]


def test_witness_recomputes_explicit_dsf_fields_instead_of_trusting_fingerprint() -> None:
    settlement = _settlement("field-tamper", frequency=25)
    payload = json.loads(
        settlement.receipt_registry.resolve(
            settlement.authority_receipt_sha256
        ).decode("utf-8")
    )
    observed = next(
        item for item in payload["interpretations"] if item["state"] == "observed"
    )
    field = observed["substreams"][0]["field_tuples"][0]["fields"][0]
    field[1] = "1/1" if field[1] != "1/1" else "2/1"
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    witness = PredictionWitness(
        event_id=settlement.event_id,
        settlement_receipt_sha256=receipt_sha256(encoded),
        structural_fingerprint=settlement.structural_fingerprint,
        settlement_payload_base64=base64.b64encode(encoded).decode("ascii"),
    )
    with pytest.raises(ValueError, match="explicit DSF field changed"):
        witness.verify(max_bytes=2 * 1024 * 1024)
