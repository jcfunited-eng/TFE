"""Exact fixed-42 L6 tests, including joint-field U_star semantics."""

from fractions import Fraction
from types import MappingProxyType, SimpleNamespace

import pytest

import dsf_ai_service.glew_runtime.l6 as l6
from dsf_ai_service.glew_runtime.l6 import (
    COMPLETENESS_RECEIPT_FIELD,
    FIELD_ORDER,
    LANE_ORDER,
    N_START,
    ROW_RECEIPT_FIELD,
    ActiveLaneState,
    ConstraintRowProvenance,
    Fixed42ConstraintStack,
    L4Field,
    L6EvaluationStatus,
    L6Lane,
    L6PredicateInputs,
    NativeConstraintCovector,
    canonical_completeness_receipt_payload,
    canonical_row_receipt_payload,
    embed_native_covector,
    evaluate_l6,
    exact_rank_receipt,
    fixed42_column,
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
        key = (field_name, digest)
        previous = self._payloads.get(key)
        if previous is not None and previous != payload:
            raise AssertionError("test registry digest collision")
        self._payloads[key] = payload
        return digest

    def freeze(self):
        return _FrozenRegistry(self._payloads)


def _row(
    builder,
    lane,
    native_port_id,
    field_name,
    *,
    row_id,
    value=Fraction(1),
):
    coefficients = [Fraction(0) for _ in FIELD_ORDER]
    coefficients[FIELD_ORDER.index(field_name)] = value
    coefficients = tuple(coefficients)
    provider_id = f"{lane.value}-signed-provider"
    operator_id = "direct-fixed42-covector-v1"
    payload = canonical_row_receipt_payload(
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        operator_id=operator_id,
        row_id=row_id,
        coefficients=coefficients,
    )
    digest = builder.mount(ROW_RECEIPT_FIELD, payload)
    return embed_native_covector(
        NativeConstraintCovector(
            provenance=ConstraintRowProvenance(
                lane=lane,
                provider_id=provider_id,
                native_port_id=native_port_id,
                operator_id=operator_id,
                receipt_sha256=digest,
                row_id=row_id,
            ),
            coefficients=coefficients,
        )
    )


def _independent_stack(builder, lanes, rank):
    rows = []
    for lane in lanes:
        for field_name in FIELD_ORDER:
            if len(rows) == rank:
                return Fixed42ConstraintStack(tuple(rows))
            rows.append(
                _row(
                    builder,
                    lane,
                    f"port-{field_name.value}",
                    field_name,
                    row_id=f"basis-{lane.value}-{field_name.value}",
                )
            )
    if len(rows) != rank:
        raise AssertionError("synthetic rank exceeds lane capacity")
    return Fixed42ConstraintStack(tuple(rows))


def _predicates(
    builder,
    lanes,
    stack,
    *,
    u_star=Fraction(0),
    disruption_clear=True,
):
    states = []
    for lane in lanes:
        row_digests = tuple(
            row.provenance.receipt_sha256
            for row in stack.rows
            if row.provenance.lane is lane
        )
        payload = canonical_completeness_receipt_payload(
            lane=lane,
            row_receipt_sha256s=row_digests,
        )
        states.append(
            ActiveLaneState(
                lane=lane,
                u_star=u_star,
                constraint_set_complete=True,
                constraint_set_receipt_sha256=builder.mount(
                    COMPLETENESS_RECEIPT_FIELD,
                    payload,
                ),
            )
        )
    return L6PredicateInputs(tuple(states), disruption_clear)


def _authorized_case(
    rank,
    *,
    lanes=LANE_ORDER[:4],
    u_star=Fraction(0),
    disruption_clear=True,
):
    builder = _RegistryBuilder()
    stack = _independent_stack(builder, lanes, rank)
    predicates = _predicates(
        builder,
        lanes,
        stack,
        u_star=u_star,
        disruption_clear=disruption_clear,
    )
    return stack, predicates, builder.freeze()


def test_fixed_surface_is_six_lanes_by_seven_fields():
    assert LANE_ORDER == (
        L6Lane.LANGUAGE,
        L6Lane.SIGHT,
        L6Lane.SOUND,
        L6Lane.TOUCH,
        L6Lane.SMELL,
        L6Lane.TASTE,
    )
    assert FIELD_ORDER == (
        L4Field.D_K,
        L4Field.M_K,
        L4Field.R_REV_K,
        L4Field.U_STAR_K,
        L4Field.C_K,
        L4Field.P_K,
        L4Field.B_K,
    )
    assert N_START == 42
    assert fixed42_column(L6Lane.LANGUAGE, L4Field.D_K) == 0
    assert fixed42_column(L6Lane.SIGHT, L4Field.D_K) == 7
    assert fixed42_column(L6Lane.TASTE, L4Field.B_K) == 41


def test_direct_embedding_stays_inside_its_lane_block():
    builder = _RegistryBuilder()
    row = _row(
        builder,
        L6Lane.SOUND,
        "spectral-port",
        L4Field.C_K,
        row_id="r0",
        value=Fraction(-7, 13),
    )
    assert row.coefficients[fixed42_column(L6Lane.SOUND, L4Field.C_K)] == Fraction(
        -7, 13
    )
    assert sum(value != 0 for value in row.coefficients) == 1


def test_multiple_ports_remain_separate_rows_without_double_counting_rank():
    builder = _RegistryBuilder()
    first = _row(
        builder,
        L6Lane.SOUND,
        "left-mic",
        L4Field.C_K,
        row_id="left",
        value=Fraction(1, 3),
    )
    second = _row(
        builder,
        L6Lane.SOUND,
        "right-mic",
        L4Field.C_K,
        row_id="right",
        value=Fraction(2, 6),
    )
    receipt = exact_rank_receipt(Fixed42ConstraintStack((first, second)))
    assert receipt.row_count == 2
    assert receipt.rank == 1


def test_empty_genesis_is_unresolved_not_zero_lock():
    stack = Fixed42ConstraintStack(())
    receipt = exact_rank_receipt(stack)
    result = evaluate_l6(stack)
    assert receipt.matrix_shape == (0, 42)
    assert receipt.rank == 0
    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert result.structural_lock is None


def test_rank_27_is_first_integer_capture_rank_for_fixed_42():
    stack, predicates, receipts = _authorized_case(27)
    result = evaluate_l6(stack, predicates, receipts)
    assert result.rank_receipt.n_effective == 15
    assert result.omega == Fraction(27, 42)
    assert result.status is L6EvaluationStatus.LOCK
    assert result.arb_proof is not None and result.arb_proof.below_threshold


def test_rank_26_remains_outside_capture_basin():
    stack, predicates, receipts = _authorized_case(26)
    result = evaluate_l6(stack, predicates, receipts)
    assert result.rank_receipt.n_effective == 16
    assert result.status is L6EvaluationStatus.NO_LOCK
    assert result.arb_proof is not None and not result.arb_proof.below_threshold


def test_complete_active_lane_may_emit_zero_nonzero_rows():
    lanes = LANE_ORDER[:4]
    builder = _RegistryBuilder()
    stack = _independent_stack(builder, lanes[:3], 21)
    predicates = _predicates(builder, lanes, stack)
    result = evaluate_l6(stack, predicates, builder.freeze())
    assert result.status is L6EvaluationStatus.NO_LOCK
    assert result.rank_receipt.rank == 21


@pytest.mark.parametrize(
    ("lanes", "rank", "disruption_clear", "reason"),
    [
        (LANE_ORDER[:3], 21, True, "fewer than four valid"),
        (LANE_ORDER[:4], 27, False, "disruption latch"),
    ],
)
def test_actual_false_predicates_short_circuit_without_arb(
    monkeypatch,
    lanes,
    rank,
    disruption_clear,
    reason,
):
    stack, predicates, receipts = _authorized_case(
        rank,
        lanes=lanes,
        disruption_clear=disruption_clear,
    )
    monkeypatch.setattr(
        l6,
        "_import_flint",
        lambda: (_ for _ in ()).throw(AssertionError("Arb must not be called")),
    )
    result = evaluate_l6(stack, predicates, receipts)
    assert result.status is L6EvaluationStatus.NO_LOCK
    assert result.arb_proof is None
    assert reason in result.reason


@pytest.mark.parametrize("u_star", [Fraction(1, 1000), Fraction(1), None])
def test_u_star_is_retained_but_never_a_standalone_veto(u_star):
    stack, predicates, receipts = _authorized_case(27, u_star=u_star)
    result = evaluate_l6(stack, predicates, receipts)
    assert result.status is L6EvaluationStatus.LOCK
    assert result.structural_lock is True


def test_missing_registry_is_unknown_even_when_rank_enters_lock():
    stack, predicates, _ = _authorized_case(27)
    result = evaluate_l6(stack, predicates)
    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert "registry is missing" in result.reason


def test_row_field_tamper_cannot_reuse_mounted_receipt():
    stack, predicates, receipts = _authorized_case(27)
    original = stack.rows[0]
    values = list(original.native_coefficients)
    values[0] = Fraction(2)
    forged = embed_native_covector(
        NativeConstraintCovector(original.provenance, tuple(values))
    )
    result = evaluate_l6(
        Fixed42ConstraintStack((forged,) + stack.rows[1:]),
        predicates,
        receipts,
    )
    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert "fields do not match" in result.reason


def test_subset_stack_cannot_reuse_full_completeness_receipt():
    stack, predicates, receipts = _authorized_case(27)
    result = evaluate_l6(
        Fixed42ConstraintStack(stack.rows[:-1]),
        predicates,
        receipts,
    )
    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert "does not bind the exact active row set" in result.reason


def test_unmounted_or_forged_row_has_no_authority():
    builder = _RegistryBuilder()
    row = _row(
        builder,
        L6Lane.LANGUAGE,
        "typed-port",
        L4Field.D_K,
        row_id="r0",
    )
    stack = Fixed42ConstraintStack((row,))
    completeness = _RegistryBuilder()
    predicates = _predicates(completeness, (L6Lane.LANGUAGE,), stack)
    result = evaluate_l6(stack, predicates, completeness.freeze())
    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert ROW_RECEIPT_FIELD in result.reason
    assert "is not mounted" in result.reason

    provenance = ConstraintRowProvenance(
        lane=row.provenance.lane,
        provider_id=row.provenance.provider_id,
        native_port_id=row.provenance.native_port_id,
        operator_id=row.provenance.operator_id,
        receipt_sha256="0" * 64,
        row_id=row.provenance.row_id,
    )
    forged = embed_native_covector(
        NativeConstraintCovector(provenance, row.native_coefficients)
    )
    result = evaluate_l6(
        Fixed42ConstraintStack((forged,)),
        predicates,
        completeness.freeze(),
    )
    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert "do not match provenance receipt" in result.reason


def test_missing_completeness_receipt_is_unknown():
    stack, predicates, receipts = _authorized_case(27)
    states = list(predicates.active_lanes or ())
    final = states[-1]
    states[-1] = ActiveLaneState(final.lane, final.u_star, None, None)
    result = evaluate_l6(
        stack,
        L6PredicateInputs(tuple(states), True),
        receipts,
    )
    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert "completeness receipt is missing" in result.reason


@pytest.mark.parametrize(
    ("python_version", "flint_version", "threads", "reason"),
    [
        ("0.8.0", "3.6.0", 1, "python-flint version mismatch"),
        ("0.9.0", "3.5.0", 1, "FLINT version mismatch"),
        ("0.9.0", "3.6.0", 2, "thread mismatch"),
    ],
)
def test_eligible_lock_fails_unknown_on_arb_mismatch(
    monkeypatch,
    python_version,
    flint_version,
    threads,
    reason,
):
    stack, predicates, receipts = _authorized_case(27)
    monkeypatch.setattr(
        l6,
        "_import_flint",
        lambda: SimpleNamespace(
            __version__=python_version,
            __FLINT_VERSION__=flint_version,
            ctx=SimpleNamespace(threads=threads),
        ),
    )
    result = evaluate_l6(stack, predicates, receipts)
    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert result.arb_proof is None
    assert reason in result.reason
