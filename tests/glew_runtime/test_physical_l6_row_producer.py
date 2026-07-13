"""Focused proofs for the candidate physical fixed-42 row producer."""

from dataclasses import replace
from fractions import Fraction
from types import MappingProxyType

import pytest

from dsf_ai_service.glew_runtime.l6 import (
    CANDIDATE_BRANCH_CELL_RECEIPT_FIELD,
    CANDIDATE_LEFT_NULLSPACE_OPERATOR_ID,
    CANDIDATE_LOCAL_TANGENT_RECEIPT_FIELD,
    FIELD_ORDER,
    CandidateConstraintProductionStatus,
    CandidateProviderTangentClaim,
    ConstraintRowProvenance,
    L6Lane,
    NativeConstraintCovector,
    candidate_exact_left_nullspace_basis,
    canonical_candidate_branch_cell_receipt_payload,
    canonical_candidate_local_tangent_receipt_payload,
    exact_rank_receipt,
    produce_candidate_fixed42_constraints,
    receipt_sha256,
)


class _FrozenRegistry:
    def __init__(self, payloads):
        self._payloads = MappingProxyType(dict(payloads))

    def resolve(self, digest, field_name):
        return self._payloads.get((field_name, digest))


class _RegistryBuilder:
    def __init__(self):
        self._payloads = {}

    def mount(self, field_name, payload):
        digest = receipt_sha256(payload)
        self._payloads[(field_name, digest)] = payload
        return digest

    def freeze(self):
        return _FrozenRegistry(self._payloads)


def _identity_tangent():
    return tuple(
        tuple(
            Fraction(int(row_index == column_index))
            for column_index in range(7)
        )
        for row_index in range(7)
    )


def _rank_six_tangent():
    return tuple(
        tuple(
            Fraction(int(row_index == column_index))
            for column_index in range(6)
        )
        for row_index in range(7)
    )


def _rank_two_tangent():
    columns = (
        (
            Fraction(1),
            Fraction(2),
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(0),
        ),
        (
            Fraction(0),
            Fraction(0),
            Fraction(1),
            Fraction(1),
            Fraction(0),
            Fraction(0),
            Fraction(0),
        ),
    )
    return tuple(
        tuple(column[row_index] for column in columns)
        for row_index in range(7)
    )


def _mount_claim(
    builder,
    *,
    lane=L6Lane.SOUND,
    provider_id="physical-acoustic-provider",
    native_port_id="left-microphone",
    branch_id="l4-branch-positive-displacement",
    cell_id="gate-120-128",
    tangent=None,
):
    exact_tangent = _rank_six_tangent() if tangent is None else tangent
    coordinate_ids = tuple(
        f"native-perturbation-{index}"
        for index in range(len(exact_tangent[0]))
    )
    branch_payload = canonical_candidate_branch_cell_receipt_payload(
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        branch_id=branch_id,
        cell_id=cell_id,
    )
    branch_digest = builder.mount(
        CANDIDATE_BRANCH_CELL_RECEIPT_FIELD,
        branch_payload,
    )
    tangent_payload = canonical_candidate_local_tangent_receipt_payload(
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        branch_id=branch_id,
        cell_id=cell_id,
        perturbation_coordinate_ids=coordinate_ids,
        tangent=exact_tangent,
        branch_cell_receipt_sha256=branch_digest,
    )
    tangent_digest = builder.mount(
        CANDIDATE_LOCAL_TANGENT_RECEIPT_FIELD,
        tangent_payload,
    )
    return CandidateProviderTangentClaim(
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        branch_id=branch_id,
        cell_id=cell_id,
        perturbation_coordinate_ids=coordinate_ids,
        tangent=exact_tangent,
        branch_cell_receipt_sha256=branch_digest,
        tangent_receipt_sha256=tangent_digest,
    )


def _column_scale(tangent, scales):
    return tuple(
        tuple(value * scales[column] for column, value in enumerate(row))
        for row in tangent
    )


def test_exact_basis_is_canonical_and_invariant_to_physical_coordinate_scale():
    tangent = _rank_two_tangent()
    scaled = _column_scale(
        tangent,
        (Fraction(-3, 5), Fraction(7, 11)),
    )
    expected = (
        (
            Fraction(2),
            Fraction(-1),
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(0),
        ),
        (
            Fraction(0),
            Fraction(0),
            Fraction(1),
            Fraction(-1),
            Fraction(0),
            Fraction(0),
            Fraction(0),
        ),
        (
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(1),
            Fraction(0),
            Fraction(0),
        ),
        (
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(1),
            Fraction(0),
        ),
        (
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(0),
            Fraction(1),
        ),
    )
    assert candidate_exact_left_nullspace_basis(tangent) == expected
    assert candidate_exact_left_nullspace_basis(scaled) == expected


def test_full_rank_physical_tangent_legitimately_produces_no_constraints():
    builder = _RegistryBuilder()
    claim = _mount_claim(builder, tangent=_identity_tangent())
    result = produce_candidate_fixed42_constraints(
        (claim,),
        builder.freeze(),
    )
    assert result.status is CandidateConstraintProductionStatus.KNOWN
    assert result.stack is not None
    assert result.stack.rows == ()
    assert len(result.provider_sets) == 1
    assert result.provider_sets[0].rows == ()
    assert result.provider_sets[0].row_receipt_payloads == ()


def test_lower_rank_tangent_rows_exactly_annihilate_every_native_perturbation():
    builder = _RegistryBuilder()
    tangent = _rank_two_tangent()
    claim = _mount_claim(builder, tangent=tangent)
    result = produce_candidate_fixed42_constraints(
        (claim,),
        builder.freeze(),
    )
    assert result.status is CandidateConstraintProductionStatus.KNOWN
    assert result.stack is not None
    assert len(result.stack.rows) == 5
    for row in result.stack.rows:
        assert row.provenance.operator_id == CANDIDATE_LEFT_NULLSPACE_OPERATOR_ID
        assert any(row.native_coefficients)
        for perturbation_index in range(2):
            assert sum(
                (
                    row.native_coefficients[field_index]
                    * tangent[field_index][perturbation_index]
                    for field_index in range(7)
                ),
                Fraction(0),
            ) == 0


def test_zero_covector_is_rejected_at_the_existing_fixed42_boundary():
    provenance = ConstraintRowProvenance(
        lane=L6Lane.SOUND,
        provider_id="physical-acoustic-provider",
        native_port_id="left-microphone",
        operator_id=CANDIDATE_LEFT_NULLSPACE_OPERATOR_ID,
        receipt_sha256="0" * 64,
        row_id="forbidden-zero",
    )
    with pytest.raises(ValueError, match="zero covector"):
        NativeConstraintCovector(
            provenance=provenance,
            coefficients=tuple(Fraction(0) for _ in FIELD_ORDER),
        )


def test_multiple_native_ports_remain_separate_provenance_sets():
    builder = _RegistryBuilder()
    left = _mount_claim(
        builder,
        native_port_id="left-microphone",
    )
    right = _mount_claim(
        builder,
        native_port_id="right-microphone",
        cell_id="gate-121-129",
    )
    result = produce_candidate_fixed42_constraints(
        (right, left),
        builder.freeze(),
    )
    assert result.status is CandidateConstraintProductionStatus.KNOWN
    assert result.stack is not None
    assert tuple(
        provider_set.native_port_id for provider_set in result.provider_sets
    ) == ("left-microphone", "right-microphone")
    assert tuple(
        row.provenance.native_port_id for row in result.stack.rows
    ) == ("left-microphone", "right-microphone")
    rank = exact_rank_receipt(result.stack)
    assert rank.row_count == 2
    assert rank.rank == 1


def test_branch_or_cell_tamper_is_unknown_and_releases_no_partial_rows():
    builder = _RegistryBuilder()
    claim = _mount_claim(builder)
    tampered = replace(claim, cell_id="different-l4-cell")
    result = produce_candidate_fixed42_constraints(
        (tampered,),
        builder.freeze(),
    )
    assert result.status is CandidateConstraintProductionStatus.UNKNOWN
    assert result.stack is None
    assert result.provider_sets == ()
    assert "branch/cell" in result.reason


@pytest.mark.parametrize(
    "broken_claim",
    (
        lambda claim: replace(claim, tangent=None),
        lambda claim: replace(
            claim,
            tangent=(
                (0.5,) + claim.tangent[0][1:],
                *claim.tangent[1:],
            ),
        ),
        lambda claim: replace(claim, branch_cell_receipt_sha256=None),
    ),
)
def test_missing_or_nonrational_provider_facts_are_typed_unknown(broken_claim):
    builder = _RegistryBuilder()
    claim = _mount_claim(builder)
    result = produce_candidate_fixed42_constraints(
        (broken_claim(claim),),
        builder.freeze(),
    )
    assert result.status is CandidateConstraintProductionStatus.UNKNOWN
    assert result.stack is None
    assert result.provider_sets == ()


def test_candidate_rows_do_not_guarantee_or_manufacture_capture_rank():
    builder = _RegistryBuilder()
    claim = _mount_claim(builder, tangent=_rank_six_tangent())
    result = produce_candidate_fixed42_constraints(
        (claim,),
        builder.freeze(),
    )
    assert result.status is CandidateConstraintProductionStatus.KNOWN
    assert result.stack is not None
    receipt = exact_rank_receipt(result.stack)
    assert receipt.row_count == 1
    assert receipt.rank == 1
    assert receipt.n_effective == 41
