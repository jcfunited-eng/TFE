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
    def __init__(self, payloads: dict[tuple[str, str], bytes]):
        self._payloads = MappingProxyType(dict(payloads))

    def resolve(self, digest: str, field_name: str) -> bytes | None:
        return self._payloads.get((field_name, digest))


class _RegistryBuilder:
    def __init__(self):
        self._payloads: dict[tuple[str, str], bytes] = {}

    def mount(self, field_name: str, payload: bytes) -> str:
        digest = receipt_sha256(payload)
        key = (field_name, digest)
        previous = self._payloads.get(key)
        if previous is not None and previous != payload:
            raise AssertionError("test registry digest collision")
        self._payloads[key] = payload
        return digest

    def freeze(self) -> _FrozenRegistry:
        return _FrozenRegistry(self._payloads)


def _row(
    builder: _RegistryBuilder,
    lane: L6Lane,
    native_port_id: str,
    field_name: L4Field,
    *,
    row_id: str,
    value: Fraction = Fraction(1),
):
    coefficients = [Fraction(0) for _ in FIELD_ORDER]
    coefficients[FIELD_ORDER.index(field_name)] = value
    exact = tuple(coefficients)
    provider_id = f"{lane.value}-signed-provider"
    operator_id = "direct-fixed42-covector-v1"
    payload = canonical_row_receipt_payload(
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        operator_id=operator_id,
        row_id=row_id,
        coefficients=exact,
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
            coefficients=exact,
        )
    )


def _independent_stack(
    builder: _RegistryBuilder,
    lanes: tuple[L6Lane, ...],
    rank: int,
) -> Fixed42ConstraintStack:
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
        raise AssertionError("requested synthetic rank exceeds lane capacity")
    return Fixed42ConstraintStack(tuple(rows))


def _predicates(
    builder: _RegistryBuilder,
    lanes: tuple[L6Lane, ...],
    stack: Fixed42ConstraintStack,
    *,
    u_star: Fraction = Fraction(0),
    disruption_clear: bool = True,
) -> L6PredicateInputs:
    lane_states = []
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
        digest = builder.mount(COMPLETENESS_RECEIPT_FIELD, payload)
        lane_states.append(
            ActiveLaneState(
                lane=lane,
                u_star=u_star,
                constraint_set_complete=True,
                constraint_set_receipt_sha256=digest,
            )
        )
    return L6PredicateInputs(tuple(lane_states), disruption_clear)


def _authorized_case(
    rank: int,
    *,
    lanes: tuple[L6Lane, ...] = LANE_ORDER[:4],
    u_star: Fraction = Fraction(0),
    disruption_clear: bool = True,
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


def test_fixed_surface_is_six_ordered_lanes_by_seven_ordered_fields():
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


def test_direct_embedding_places_native_fraction_in_only_its_lane_block():
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


def test_multiple_native_ports_remain_separate_rows_without_averaging():
    builder = _RegistryBuilder()
    edge = _row(
        builder, L6Lane.SIGHT, "edge-port", L4Field.D_K, row_id="edge"
    )
    motion = _row(
        builder, L6Lane.SIGHT, "motion-port", L4Field.M_K, row_id="motion"
    )
    stack = Fixed42ConstraintStack((edge, motion))

    receipt = exact_rank_receipt(stack)

    assert stack.rows == (edge, motion)
    assert receipt.row_count == 2
    assert receipt.rank == 2
    assert receipt.pivot_columns == (7, 8)


def test_equal_rows_from_distinct_ports_are_preserved_not_double_ranked():
    builder = _RegistryBuilder()
    left = _row(
        builder,
        L6Lane.SOUND,
        "left-mic",
        L4Field.C_K,
        row_id="left",
        value=Fraction(1, 3),
    )
    right = _row(
        builder,
        L6Lane.SOUND,
        "right-mic",
        L4Field.C_K,
        row_id="right",
        value=Fraction(2, 6),
    )

    receipt = exact_rank_receipt(Fixed42ConstraintStack((left, right)))

    assert receipt.row_count == 2
    assert receipt.rank == 1


def test_empty_genesis_stack_is_zero_by_42_and_unresolved_without_authority():
    stack = Fixed42ConstraintStack(())
    receipt = exact_rank_receipt(stack)
    result = evaluate_l6(stack)

    assert receipt.matrix_shape == (0, 42)
    assert receipt.rank == 0
    assert receipt.n_effective == 42
    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert result.structural_lock is None


def test_rank_27_is_first_integer_capture_rank_for_fixed_42():
    stack, predicates, registry = _authorized_case(27)

    result = evaluate_l6(stack, predicates, registry)

    assert result.rank_receipt.rank == 27
    assert result.rank_receipt.n_effective == 15
    assert result.omega == Fraction(27, 42)
    assert result.status is L6EvaluationStatus.LOCK
    assert result.structural_lock is True
    assert result.arb_proof is not None
    assert result.arb_proof.below_threshold is True


def test_rank_26_remains_outside_fixed_42_capture_basin():
    stack, predicates, registry = _authorized_case(26)

    result = evaluate_l6(stack, predicates, registry)

    assert result.rank_receipt.rank == 26
    assert result.rank_receipt.n_effective == 16
    assert result.status is L6EvaluationStatus.NO_LOCK
    assert result.structural_lock is False
    assert result.arb_proof is not None
    assert result.arb_proof.below_threshold is False


def test_complete_active_lane_may_emit_zero_nonzero_rows():
    lanes = LANE_ORDER[:4]
    builder = _RegistryBuilder()
    stack = _independent_stack(builder, lanes[:3], 21)
    predicates = _predicates(builder, lanes, stack)

    result = evaluate_l6(stack, predicates, builder.freeze())

    assert result.status is L6EvaluationStatus.NO_LOCK
    assert result.rank_receipt.rank == 21
    assert result.arb_proof is not None


@pytest.mark.parametrize(
    ("lanes", "rank", "u_star", "disruption_clear", "reason"),
    [
        (LANE_ORDER[:3], 21, Fraction(0), True, "fewer than four valid"),
        (LANE_ORDER[:4], 27, Fraction(1, 1000), True, "nonzero U_star"),
        (LANE_ORDER[:4], 27, Fraction(0), False, "disruption latch"),
    ],
)
def test_known_false_predicate_short_circuits_without_arb(
    monkeypatch, lanes, rank, u_star, disruption_clear, reason
):
    stack, predicates, registry = _authorized_case(
        rank,
        lanes=lanes,
        u_star=u_star,
        disruption_clear=disruption_clear,
    )
    monkeypatch.setattr(
        l6,
        "_import_flint",
        lambda: (_ for _ in ()).throw(AssertionError("Arb must not be called")),
    )

    result = evaluate_l6(stack, predicates, registry)

    assert result.status is L6EvaluationStatus.NO_LOCK
    assert result.structural_lock is False
    assert result.arb_proof is None
    assert reason in result.reason


def test_missing_registry_is_unknown_even_when_rows_rank_for_lock():
    stack, predicates, _registry = _authorized_case(27)

    result = evaluate_l6(stack, predicates)

    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert result.structural_lock is None
    assert "registry is missing" in result.reason


def test_row_field_tamper_cannot_reuse_mounted_receipt():
    stack, predicates, registry = _authorized_case(27)
    original = stack.rows[0]
    tampered = list(original.native_coefficients)
    tampered[0] = Fraction(2)
    tampered_row = embed_native_covector(
        NativeConstraintCovector(original.provenance, tuple(tampered))
    )
    tampered_stack = Fixed42ConstraintStack((tampered_row,) + stack.rows[1:])

    result = evaluate_l6(tampered_stack, predicates, registry)

    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert result.structural_lock is None
    assert "fields do not match" in result.reason


def test_subset_stack_cannot_reuse_full_completeness_receipt():
    stack, predicates, registry = _authorized_case(27)
    subset = Fixed42ConstraintStack(stack.rows[:-1])

    result = evaluate_l6(subset, predicates, registry)

    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert result.structural_lock is None
    assert "does not bind the exact active row set" in result.reason


def test_correct_but_unmounted_row_digest_has_no_authority():
    builder = _RegistryBuilder()
    row = _row(
        builder, L6Lane.LANGUAGE, "typed-port", L4Field.D_K, row_id="r0"
    )
    stack = Fixed42ConstraintStack((row,))

    completeness_only = _RegistryBuilder()
    predicates = _predicates(completeness_only, (L6Lane.LANGUAGE,), stack)
    registry = completeness_only.freeze()

    result = evaluate_l6(stack, predicates, registry)

    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert result.structural_lock is None
    assert ROW_RECEIPT_FIELD in result.reason
    assert "is not mounted" in result.reason


def test_forged_receipt_digest_cannot_authorize_typed_row():
    stack, predicates, registry = _authorized_case(27)
    original = stack.rows[0]
    forged_provenance = ConstraintRowProvenance(
        lane=original.provenance.lane,
        provider_id=original.provenance.provider_id,
        native_port_id=original.provenance.native_port_id,
        operator_id=original.provenance.operator_id,
        receipt_sha256="0" * 64,
        row_id=original.provenance.row_id,
    )
    forged = embed_native_covector(
        NativeConstraintCovector(forged_provenance, original.native_coefficients)
    )
    forged_stack = Fixed42ConstraintStack((forged,) + stack.rows[1:])

    result = evaluate_l6(forged_stack, predicates, registry)

    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert result.structural_lock is None
    assert "do not match provenance receipt" in result.reason


def test_missing_completeness_receipt_is_unknown():
    stack, predicates, registry = _authorized_case(27)
    states = list(predicates.active_lanes or ())
    final = states[-1]
    states[-1] = ActiveLaneState(
        lane=final.lane,
        u_star=final.u_star,
        constraint_set_complete=None,
        constraint_set_receipt_sha256=None,
    )

    result = evaluate_l6(
        stack,
        L6PredicateInputs(tuple(states), disruption_clear=True),
        registry,
    )

    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert result.structural_lock is None
    assert "completeness receipt is missing" in result.reason


@pytest.mark.parametrize(
    ("python_flint_version", "flint_version", "threads", "reason"),
    [
        ("0.8.0", "3.6.0", 1, "python-flint version mismatch"),
        ("0.9.0", "3.5.0", 1, "FLINT version mismatch"),
        ("0.9.0", "3.6.0", 2, "thread mismatch"),
    ],
)
def test_eligible_lock_fails_unknown_on_arb_mismatch(
    monkeypatch, python_flint_version, flint_version, threads, reason
):
    stack, predicates, registry = _authorized_case(27)
    mismatched = SimpleNamespace(
        __version__=python_flint_version,
        __FLINT_VERSION__=flint_version,
        ctx=SimpleNamespace(threads=threads),
    )
    monkeypatch.setattr(l6, "_import_flint", lambda: mismatched)

    result = evaluate_l6(stack, predicates, registry)

    assert result.status is L6EvaluationStatus.UNKNOWN_NO_LOCK
    assert result.structural_lock is None
    assert result.arb_proof is None
    assert reason in result.reason
