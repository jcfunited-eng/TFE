"""Focused tests for the direct expression-backed GLEW commit boundary."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.certified_backend import (
    FLINT_VERSION,
    PYTHON_FLINT_VERSION,
)
from dsf_ai_service.glew_runtime.commit import (
    ApplicabilityState,
    AuthorityDisposition,
    BinaryAuthorityKind,
    BinaryCommitAuthority,
    ClosedExperienceSeal,
    CommitStatus,
    EventSupportAuthority,
    EventSupportState,
    GovernedFact,
    L5Applicability,
    L6ScopeAuthority,
    PendingGlobalUFStatus,
    binary_authority_receipt_payload,
    closed_experience_seal_receipt_payload,
    evaluate_commit_boundary,
    evaluate_pending_global_uf_conjunction,
    event_support_authority_receipt_payload,
    l5_applicability_receipt_payload,
    l6_evaluation_receipt_payload,
    l6_scope_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.expression_modes import (
    create_empty_expression_mode_bank,
    evaluate_expression_mode_boundary,
)
from dsf_ai_service.glew_runtime.l6 import (
    ARB_PRECISION_BITS,
    ArbCaptureProof,
    ExactRankReceipt,
    L6Evaluation,
    L6EvaluationStatus,
    N_START,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from tests.glew_runtime.test_field import evidence, registry
from tests.glew_runtime.test_field_expressions import make_axis_expression


def _unique(payloads):
    return tuple(dict.fromkeys(payloads))


def _expression_recognition():
    first, first_payloads = make_axis_expression(
        (Fraction(1),) + (Fraction(0),) * 18
    )
    second, second_payloads = make_axis_expression(
        (Fraction(0), Fraction(1)) + (Fraction(0),) * 17
    )
    base_payloads = _unique(
        (
            *first_payloads,
            *second_payloads,
            first.receipt_payload,
            second.receipt_payload,
        )
    )
    receipts = registry(*base_payloads)
    empty = create_empty_expression_mode_bank(
        topology=first.topology,
        precision_authority=first.precision_authority,
        receipt_registry=receipts,
    )
    one = evaluate_expression_mode_boundary(
        topology=first.topology,
        bank=empty,
        input_expression=first,
        receipt_registry=receipts,
    )
    two = evaluate_expression_mode_boundary(
        topology=first.topology,
        bank=one.post_growth_bank,
        input_expression=second,
        receipt_registry=receipts,
    )
    recognized = evaluate_expression_mode_boundary(
        topology=first.topology,
        bank=two.post_growth_bank,
        input_expression=first,
        receipt_registry=receipts,
    )
    generated = [
        one.receipt_payload,
        two.receipt_payload,
        recognized.receipt_payload,
        empty.receipt_payload,
        one.post_growth_bank.receipt_payload,
        two.post_growth_bank.receipt_payload,
        recognized.post_growth_bank.receipt_payload,
    ]
    for bank in (
        recognized.pre_growth_bank,
        recognized.post_growth_bank,
    ):
        for mode in bank.modes:
            generated.extend(
                (
                    mode.receipt_payload,
                    mode.growth_proof_receipt_payload,
                    mode.source_expression.receipt_payload,
                )
            )
    return first, recognized, _unique((*base_payloads, *generated))


def _l6_lock() -> L6Evaluation:
    rank = 27
    n_effective = N_START - rank
    return L6Evaluation(
        status=L6EvaluationStatus.LOCK,
        structural_lock=True,
        rank_receipt=ExactRankReceipt(
            n_start=N_START,
            row_count=rank,
            rank=rank,
            n_effective=n_effective,
            pivot_columns=tuple(range(rank)),
        ),
        omega=Fraction(rank, N_START),
        arb_proof=ArbCaptureProof(
            python_flint_version=PYTHON_FLINT_VERSION,
            flint_version=FLINT_VERSION,
            threads=1,
            precision_bits=ARB_PRECISION_BITS,
            expression="n_effective < 42/exp(1)",
            threshold_ball="[15.450...,15.451...]",
            n_effective=n_effective,
            below_threshold=True,
        ),
        reason="test fixed42 lock authority",
    )


def _binary(kind, disposition, topology_receipt, experience_receipt):
    source = f"source:{kind.value}:{disposition.value}".encode()
    payload = binary_authority_receipt_payload(
        authority_id=f"{kind.value}-authority",
        kind=kind,
        disposition=disposition,
        topology_authority_receipt_sha256=topology_receipt,
        closed_experience_receipt_sha256=experience_receipt,
        source_operator_receipt_sha256=receipt_sha256(source),
    )
    return (
        BinaryCommitAuthority(
            authority_id=f"{kind.value}-authority",
            kind=kind,
            disposition=disposition,
            topology_authority_receipt_sha256=topology_receipt,
            closed_experience_receipt_sha256=experience_receipt,
            source_operator_receipt_sha256=receipt_sha256(source),
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        (source, payload),
    )


def _bundle(global_disposition=AuthorityDisposition.PASS):
    expression, recognition, expression_payloads = _expression_recognition()
    topology = expression.topology
    record, raw_payload, evidence_payload = evidence(
        "language",
        "typed",
        (Fraction(1),) + (Fraction(0),) * 18,
    )
    evidence_values = (record,)
    seal_payload = closed_experience_seal_receipt_payload(
        experience_id="expression-thought",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        input_expression_receipt_sha256=expression.receipt_sha256,
        recognition_receipt_sha256=recognition.receipt_sha256,
        ordered_evidence_receipt_sha256s=(record.evidence_receipt_sha256,),
        source_time_start=Fraction(5),
        source_time_end=Fraction(6),
        structural_time_unit="structural_second",
    )
    seal = ClosedExperienceSeal(
        experience_id="expression-thought",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        input_expression_receipt_sha256=expression.receipt_sha256,
        recognition_receipt_sha256=recognition.receipt_sha256,
        ordered_evidence_receipt_sha256s=(record.evidence_receipt_sha256,),
        source_time_start=Fraction(5),
        source_time_end=Fraction(6),
        structural_time_unit="structural_second",
        authority_receipt_sha256=receipt_sha256(seal_payload),
    )
    safe, safe_payloads = _binary(
        BinaryAuthorityKind.SAFE_MODE_CLEAR,
        AuthorityDisposition.PASS,
        topology.authority_receipt_sha256,
        seal.authority_receipt_sha256,
    )
    global_uf, global_payloads = _binary(
        BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
        global_disposition,
        topology.authority_receipt_sha256,
        seal.authority_receipt_sha256,
    )
    event_source = b"expression-R-event-source"
    event_payload = event_support_authority_receipt_payload(
        authority_id="expression-R-event",
        state=EventSupportState.POSITIVE,
        exact_r_event=Fraction(1),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=seal.authority_receipt_sha256,
        source_operator_receipt_sha256=receipt_sha256(event_source),
    )
    event_support = EventSupportAuthority(
        authority_id="expression-R-event",
        state=EventSupportState.POSITIVE,
        exact_r_event=Fraction(1),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=seal.authority_receipt_sha256,
        source_operator_receipt_sha256=receipt_sha256(event_source),
        authority_receipt_sha256=receipt_sha256(event_payload),
    )
    l6 = _l6_lock()
    l6_payload = l6_evaluation_receipt_payload(l6)
    l6_scope_payload = l6_scope_authority_receipt_payload(
        authority_id="expression-fixed42-scope",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=seal.authority_receipt_sha256,
        l6_evaluation_receipt_sha256=receipt_sha256(l6_payload),
    )
    l6_scope = L6ScopeAuthority(
        authority_id="expression-fixed42-scope",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=seal.authority_receipt_sha256,
        l6_evaluation_receipt_sha256=receipt_sha256(l6_payload),
        authority_receipt_sha256=receipt_sha256(l6_scope_payload),
    )
    applicability = []
    applicability_payloads = []
    for fact in (GovernedFact.S_UF, GovernedFact.R_UF):
        source = f"expression-L5:{fact.value}".encode()
        payload = l5_applicability_receipt_payload(
            authority_id=f"expression-L5-{fact.value}",
            lane_id="language",
            port_id="typed",
            fact=fact,
            state=ApplicabilityState.REQUIRED,
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            closed_experience_receipt_sha256=seal.authority_receipt_sha256,
            source_governance_receipt_sha256=receipt_sha256(source),
        )
        applicability.append(
            L5Applicability(
                authority_id=f"expression-L5-{fact.value}",
                lane_id="language",
                port_id="typed",
                fact=fact,
                state=ApplicabilityState.REQUIRED,
                topology_authority_receipt_sha256=(
                    topology.authority_receipt_sha256
                ),
                closed_experience_receipt_sha256=seal.authority_receipt_sha256,
                source_governance_receipt_sha256=receipt_sha256(source),
                authority_receipt_sha256=receipt_sha256(payload),
            )
        )
        applicability_payloads.extend((source, payload))
    receipts = registry(
        *expression_payloads,
        raw_payload,
        evidence_payload,
        seal_payload,
        *safe_payloads,
        *global_payloads,
        event_source,
        event_payload,
        l6_payload,
        l6_scope_payload,
        *applicability_payloads,
    )
    return {
        "topology": topology,
        "recognition": recognition,
        "l6_evaluation": l6,
        "l6_scope": l6_scope,
        "closed_experience": seal,
        "safe_mode": safe,
        "event_support": event_support,
        "evidence": evidence_values,
        "l5_applicability": tuple(applicability),
        "global_uf_validation": global_uf,
        "receipt_registry": receipts,
    }



def _extend_registry(
    base: ReceiptRegistry,
    *payloads: bytes,
) -> ReceiptRegistry:
    records = list(base.records)
    mounted = {value.digest: value.payload for value in records}
    for payload in payloads:
        digest = receipt_sha256(payload)
        if digest in mounted:
            assert mounted[digest] == payload
            continue
        records.append(ReceiptRecord(digest, payload))
        mounted[digest] = payload
    return ReceiptRegistry(base.profile_binding_sha256, tuple(records))


def _pending_inputs(bundle):
    return {
        key: value
        for key, value in bundle.items()
        if key != "global_uf_validation"
    }


def _assert_common_receipts_match(pending, final) -> None:
    assert pending.topology_authority_receipt_sha256 == (
        final.topology_authority_receipt_sha256
    )
    assert pending.closed_experience_receipt_sha256 == (
        final.closed_experience_receipt_sha256
    )
    assert pending.expression_recognition_receipt_sha256 == (
        final.expression_recognition_receipt_sha256
    )
    assert pending.pre_growth_expression_bank_receipt_sha256 == (
        final.pre_growth_expression_bank_receipt_sha256
    )
    assert pending.l6_evaluation_receipt_sha256 == (
        final.l6_evaluation_receipt_sha256
    )
    assert pending.safe_mode_receipt_sha256 == final.safe_mode_receipt_sha256
    assert pending.event_support_receipt_sha256 == (
        final.event_support_receipt_sha256
    )
    assert pending.evidence_receipt_sha256s == final.evidence_receipt_sha256s
    assert pending.applicability_receipt_sha256s == (
        final.applicability_receipt_sha256s
    )


def test_pending_global_uf_ready_and_final_pass_share_exact_conjunction():
    bundle = _bundle()

    pending = evaluate_pending_global_uf_conjunction(
        **_pending_inputs(bundle)
    )
    final = evaluate_commit_boundary(**bundle)

    assert pending.status is PendingGlobalUFStatus.READY_EXCEPT_GLOBAL_UF
    assert pending.selected_mode_index == final.selected_mode_index == 0
    assert pending.selected_mode_receipt_sha256 == (
        final.selected_mode_receipt_sha256
    )
    assert pending.findings == final.findings == ()
    assert b'"global_uf_state":"pending_not_evaluated"' in (
        pending.receipt_payload
    )
    _assert_common_receipts_match(pending, final)
    pending.verify()


def test_pending_global_uf_does_not_hide_a_common_unknown():
    bundle = _bundle()
    safe, payloads = _binary(
        BinaryAuthorityKind.SAFE_MODE_CLEAR,
        AuthorityDisposition.UNKNOWN,
        bundle["topology"].authority_receipt_sha256,
        bundle["closed_experience"].authority_receipt_sha256,
    )
    bundle["safe_mode"] = safe
    bundle["receipt_registry"] = _extend_registry(
        bundle["receipt_registry"],
        *payloads,
    )

    pending = evaluate_pending_global_uf_conjunction(
        **_pending_inputs(bundle)
    )
    final = evaluate_commit_boundary(**bundle)

    assert pending.status is PendingGlobalUFStatus.UNKNOWN
    assert pending.selected_mode_index is None
    assert pending.findings == ("safe_mode_unknown",)
    assert final.status is CommitStatus.UNKNOWN_NO_COMMIT
    assert final.findings == pending.findings
    _assert_common_receipts_match(pending, final)


def test_pending_global_uf_does_not_hide_a_common_negative():
    bundle = _bundle()
    safe, payloads = _binary(
        BinaryAuthorityKind.SAFE_MODE_CLEAR,
        AuthorityDisposition.FAIL,
        bundle["topology"].authority_receipt_sha256,
        bundle["closed_experience"].authority_receipt_sha256,
    )
    bundle["safe_mode"] = safe
    bundle["receipt_registry"] = _extend_registry(
        bundle["receipt_registry"],
        *payloads,
    )

    pending = evaluate_pending_global_uf_conjunction(
        **_pending_inputs(bundle)
    )
    final = evaluate_commit_boundary(**bundle)

    assert pending.status is PendingGlobalUFStatus.NO_COMMIT
    assert pending.selected_mode_receipt_sha256 is None
    assert pending.findings == ("safe_mode_active",)
    assert final.status is CommitStatus.NO_COMMIT
    assert final.findings == pending.findings


def test_global_uf_failure_changes_only_the_final_conjunction():
    bundle = _bundle(global_disposition=AuthorityDisposition.FAIL)

    pending = evaluate_pending_global_uf_conjunction(
        **_pending_inputs(bundle)
    )
    final = evaluate_commit_boundary(**bundle)

    assert pending.status is PendingGlobalUFStatus.READY_EXCEPT_GLOBAL_UF
    assert pending.findings == ()
    assert final.status is CommitStatus.NO_COMMIT
    assert final.findings == ("global_uf_validation_failed",)
    _assert_common_receipts_match(pending, final)


def test_pending_receipt_status_tamper_fails_closed():
    pending = evaluate_pending_global_uf_conjunction(
        **_pending_inputs(_bundle())
    )

    with pytest.raises(ReceiptError):
        replace(
            pending,
            status=PendingGlobalUFStatus.NO_COMMIT,
        ).verify()

def test_direct_expression_result_commits_one_stable_pre_growth_mode():
    bundle = _bundle()
    decision = evaluate_commit_boundary(**bundle)

    assert decision.status is CommitStatus.COMMIT
    assert decision.selected_mode_index == 0
    assert decision.selected_mode_receipt_sha256 == (
        bundle["recognition"].pre_growth_bank.modes[0].receipt_sha256
    )
    assert decision.expression_recognition_receipt_sha256 == (
        bundle["recognition"].receipt_sha256
    )
    assert decision.pre_growth_expression_bank_receipt_sha256 == (
        bundle["recognition"].pre_growth_bank.receipt_sha256
    )
    assert not hasattr(decision, "pre_growth_bank_receipt_sha256")


def test_legacy_recognition_object_is_rejected_not_adapted():
    bundle = _bundle()
    bundle["recognition"] = object()

    with pytest.raises(ReceiptError, match="ExpressionModeBoundaryResult"):
        evaluate_commit_boundary(**bundle)


def test_unknown_independent_authority_propagates_unknown_no_commit():
    decision = evaluate_commit_boundary(
        **_bundle(global_disposition=AuthorityDisposition.UNKNOWN)
    )

    assert decision.status is CommitStatus.UNKNOWN_NO_COMMIT
    assert "global_uf_validation_unknown" in decision.findings


def test_expression_seal_cannot_name_a_different_recognition_receipt():
    bundle = _bundle()
    forged = replace(
        bundle["closed_experience"],
        recognition_receipt_sha256="a" * 64,
    )
    bundle["closed_experience"] = forged

    with pytest.raises(ReceiptError, match="different recognition"):
        evaluate_commit_boundary(**bundle)
