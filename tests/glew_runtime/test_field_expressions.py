from dataclasses import replace
from fractions import Fraction as F

import pytest

from dsf_ai_service.glew_runtime.expressions import (
    EvaluatedHermitianUpperEntry,
    ExpressionEvaluationStatus,
    FieldExpressionStep,
    IndeterminateProofRequest,
    ModeExpressionInput,
    PrecisionScheduleAuthority,
    create_closed_experience_expression,
    create_hermitian_leaf_reference,
    evaluate_closed_experience_expression,
    indeterminate_proof_request_receipt_payload,
    precision_schedule_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.expression_modes import (
    ExpressionRecognitionStatus,
    create_empty_expression_mode_bank,
    evaluate_expression_mode_boundary,
)
from dsf_ai_service.glew_runtime.expression_memory import (
    ExpressionHMemEvaluator,
    create_expression_h_mem_leaf_material,
)
from dsf_ai_service.glew_runtime.field import ExactComplex, PortFiber
from dsf_ai_service.glew_runtime.memory import (
    H_MEM_OPERATOR_ID,
    DirectedRelation,
    ExactMemoryMassState,
    HMemOperatorAuthority,
    MemoryValidityMask,
    _exact_state_payload,
    h_mem_authority_receipt_payload,
    validity_mask_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import ReceiptError, receipt_sha256
from tests.glew_runtime.test_field import (
    evidence,
    evolution_authority,
    exact_state,
    make_injection,
    registry,
)


def bounds(ball):
    return (
        F(ball.lower_mantissa) * F(2) ** ball.lower_exponent,
        F(ball.upper_mantissa) * F(2) ** ball.upper_exponent,
    )


def contains(ball, value: F) -> bool:
    lower, upper = bounds(ball)
    return lower <= value <= upper


def make_two_gate_expression(*, maximum_precision_bits: int = 4096):
    first_record = evidence("language", "typed", (F(1),) + (F(0),) * 18)
    second_record = evidence("language", "typed", (F(3),) + (F(0),) * 18)
    mounted, first_injection, first_payloads = make_injection(
        (PortFiber("language", "typed"),), (first_record,)
    )
    _, second_injection, second_payloads = make_injection(
        (PortFiber("language", "typed"),), (second_record,)
    )
    first_authority, first_authority_payload = evolution_authority(
        mounted,
        first_injection,
        source_time_start=F(5),
        source_time_end=F(6),
    )
    second_authority, second_authority_payload = evolution_authority(
        mounted,
        second_injection,
        source_time_start=F(6),
        source_time_end=F(7),
    )
    initial, initial_payload = exact_state(
        mounted,
        F(5),
        (ExactComplex(F(0)),) * mounted.dimension,
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="closed-experience-precision",
        maximum_precision_bits=maximum_precision_bits,
    )
    precision = PrecisionScheduleAuthority(
        authority_id="closed-experience-precision",
        maximum_precision_bits=maximum_precision_bits,
        authority_receipt_sha256=receipt_sha256(precision_payload),
    )
    payloads = tuple(
        dict.fromkeys(
            (
                *first_payloads,
                *second_payloads,
                first_authority_payload,
                second_authority_payload,
                initial_payload,
                precision_payload,
            )
        )
    )
    receipts = registry(*payloads)
    expression = create_closed_experience_expression(
        topology=mounted,
        initial_state=initial,
        steps=(
            FieldExpressionStep(first_injection, first_authority),
            FieldExpressionStep(second_injection, second_authority),
        ),
        precision_authority=precision,
        receipt_registry=receipts,
    )
    return expression, receipts, payloads


def test_closed_experience_centroid_contains_every_post_gate_state():
    expression, receipts, _ = make_two_gate_expression()
    result = evaluate_closed_experience_expression(
        expression,
        receipt_registry=receipts,
    )

    # post-gate states are 1 and 4, so the equal-weight centroid is 5/2.
    assert result.status is ExpressionEvaluationStatus.CERTIFIED
    assert contains(result.amplitudes[0].real, F(5, 2))
    assert contains(result.amplitudes[0].imag, F(0))
    assert len(expression.post_gate_state_node_ids) == 2
    assert expression.post_gate_state_node_ids[0] != expression.post_gate_state_node_ids[1]
    assert b"equal_weight_sum_of_every_post_gate_state.v1" in expression.receipt_payload
    assert b"certified_state" not in expression.receipt_payload
    assert b"midpoint" not in expression.receipt_payload


def test_topology_dimension_remains_exact_19_times_mounted_ports():
    records = (
        evidence("sight", "release", (F(0),) * 19),
        evidence("sound", "release", (F(0),) * 19),
    )
    mounted, injection, payloads = make_injection(
        (PortFiber("sight", "release"), PortFiber("sound", "release")),
        records,
    )
    authority, authority_payload = evolution_authority(
        mounted, injection, max_component=38
    )
    initial, initial_payload = exact_state(
        mounted, F(5), (ExactComplex(F(1)),) + (ExactComplex(F(0)),) * 37
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="two-port-precision", maximum_precision_bits=4096
    )
    precision = PrecisionScheduleAuthority(
        "two-port-precision", 4096, receipt_sha256(precision_payload)
    )
    receipts = registry(*payloads, authority_payload, initial_payload, precision_payload)
    expression = create_closed_experience_expression(
        topology=mounted,
        initial_state=initial,
        steps=(FieldExpressionStep(injection, authority),),
        precision_authority=precision,
        receipt_registry=receipts,
    )

    assert expression.dimension == 38
    assert len(
        evaluate_closed_experience_expression(
            expression, receipt_registry=receipts
        ).amplitudes
    ) == 38


def test_expression_receipt_tamper_fails_closed():
    expression, receipts, _ = make_two_gate_expression()
    forged = replace(expression, receipt_payload=b"forged closed experience")

    with pytest.raises(ReceiptError, match="canonical receipt"):
        evaluate_closed_experience_expression(forged, receipt_registry=receipts)


def make_request(expression, previous, request_id: str):
    payload = indeterminate_proof_request_receipt_payload(
        request_id=request_id,
        expression_receipt_sha256=expression.receipt_sha256,
        previous_evaluation_receipt_sha256=previous.receipt_sha256,
        previous_precision_bits=previous.working_precision_bits,
        proof_obligation="unique full-field dominance remains indeterminate",
    )
    return (
        IndeterminateProofRequest(
            request_id=request_id,
            expression_receipt_sha256=expression.receipt_sha256,
            previous_evaluation_receipt_sha256=previous.receipt_sha256,
            previous_precision_bits=previous.working_precision_bits,
            proof_obligation="unique full-field dominance remains indeterminate",
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
    )


def test_precision_doubles_only_for_explicit_mounted_indeterminate_request():
    expression, receipts, payloads = make_two_gate_expression()
    first = evaluate_closed_experience_expression(expression, receipt_registry=receipts)
    request, request_payload = make_request(expression, first, "proof-refinement-1")
    mounted = registry(*payloads, request_payload)

    refined = evaluate_closed_experience_expression(
        expression,
        receipt_registry=mounted,
        previous_evaluation=first,
        indeterminate_request=request,
    )

    assert refined.status is ExpressionEvaluationStatus.CERTIFIED
    assert refined.working_precision_bits == 2 * first.working_precision_bits
    assert refined.proof_request_receipt_sha256 == request.authority_receipt_sha256
    with pytest.raises(ReceiptError, match="requires an indeterminate"):
        evaluate_closed_experience_expression(
            expression,
            receipt_registry=receipts,
            previous_evaluation=first,
        )


def test_mounted_precision_exhaustion_returns_unknown_without_amplitude_authority():
    high_expression, _, _ = make_two_gate_expression()
    initial_precision = high_expression.initial_precision_bits
    expression, receipts, payloads = make_two_gate_expression(
        maximum_precision_bits=initial_precision
    )
    first = evaluate_closed_experience_expression(expression, receipt_registry=receipts)
    request, request_payload = make_request(expression, first, "proof-exhaustion-1")

    exhausted = evaluate_closed_experience_expression(
        expression,
        receipt_registry=registry(*payloads, request_payload),
        previous_evaluation=first,
        indeterminate_request=request,
    )

    assert first.status is ExpressionEvaluationStatus.CERTIFIED
    assert exhausted.status is ExpressionEvaluationStatus.UNKNOWN
    assert exhausted.amplitudes == ()
    assert "UNKNOWN" in exhausted.reason


class SharedSqrtTwoHermitianEvaluator:
    def __init__(self, digest: str, dimension: int):
        self.provider_expression_receipt_sha256 = digest
        self.dimension = dimension
        self.calls: list[int] = []

    def evaluate_upper(self, *, flint, working_precision_bits: int):
        self.calls.append(working_precision_bits)
        shared = flint.acb(flint.arb(2).sqrt(), 0)
        return (EvaluatedHermitianUpperEntry(0, 1, shared),)


def make_hermitian_expression():
    zero_record = evidence("sound", "release", (F(0),) * 19)
    mounted, injection, payloads = make_injection(
        (PortFiber("sound", "release"),), (zero_record,)
    )
    first_authority, first_authority_payload = evolution_authority(
        mounted,
        injection,
        source_time_start=F(5),
        source_time_end=F(6),
    )
    second_authority, second_authority_payload = evolution_authority(
        mounted,
        injection,
        source_time_start=F(6),
        source_time_end=F(7),
    )
    initial, initial_payload = exact_state(
        mounted,
        F(5),
        (ExactComplex(F(1)),) + (ExactComplex(F(0)),) * 18,
    )
    provider_payload = b"correlated H_mem expression using one shared sqrt(2) dependency"
    dependency_payload = b"exact shared H_mem dependency"
    leaf = create_hermitian_leaf_reference(
        leaf_id="shared-H-mem",
        dimension=mounted.dimension,
        provider_expression_receipt_sha256=receipt_sha256(provider_payload),
        dependency_receipt_sha256s=(receipt_sha256(dependency_payload),),
        exact_input_bit_lengths=(2,),
        upper_nonzero_positions=((0, 1),),
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="H-mem-expression-precision", maximum_precision_bits=4096
    )
    precision = PrecisionScheduleAuthority(
        "H-mem-expression-precision", 4096, receipt_sha256(precision_payload)
    )
    all_payloads = (
        *payloads,
        first_authority_payload,
        second_authority_payload,
        initial_payload,
        provider_payload,
        dependency_payload,
        leaf.receipt_payload,
        precision_payload,
    )
    receipts = registry(*all_payloads)
    expression = create_closed_experience_expression(
        topology=mounted,
        initial_state=initial,
        steps=(
            FieldExpressionStep(injection, first_authority, (leaf,)),
            FieldExpressionStep(injection, second_authority, (leaf,)),
        ),
        precision_authority=precision,
        receipt_registry=receipts,
    )
    return expression, receipts, leaf


def test_shared_hermitian_expression_is_evaluated_once_and_conjugate_is_structural():
    expression, receipts, leaf = make_hermitian_expression()
    evaluator = SharedSqrtTwoHermitianEvaluator(
        leaf.provider_expression_receipt_sha256, expression.dimension
    )

    result = evaluate_closed_experience_expression(
        expression,
        receipt_registry=receipts,
        hermitian_evaluators={leaf.provider_expression_receipt_sha256: evaluator},
    )

    assert result.status is ExpressionEvaluationStatus.CERTIFIED
    assert evaluator.calls == [result.working_precision_bits]
    assert b"upper_expression_plus_same_object_exact_conjugate" in expression.receipt_payload
    assert all(value.real.python_flint_version == "0.9.0" for value in result.amplitudes)


def test_missing_hermitian_runtime_expression_fails_instead_of_using_stored_balls():
    expression, receipts, _ = make_hermitian_expression()

    with pytest.raises(ReceiptError, match="no runtime evaluator"):
        evaluate_closed_experience_expression(expression, receipt_registry=receipts)


def test_mode_adapter_preserves_reevaluation_and_never_claims_exact_rational_state():
    expression, receipts, _ = make_two_gate_expression()
    adapter = ModeExpressionInput(expression)

    result = adapter.evaluate(receipt_registry=receipts)

    assert adapter.expression_receipt_sha256 == expression.receipt_sha256
    assert adapter.dimension == 19
    assert result.status is ExpressionEvaluationStatus.CERTIFIED
    assert not hasattr(adapter, "amplitudes")


def make_axis_expression(values: tuple[F, ...]):
    record = evidence("language", "typed", values)
    mounted, injection, payloads = make_injection(
        (PortFiber("language", "typed"),), (record,)
    )
    authority, authority_payload = evolution_authority(
        mounted,
        injection,
        source_time_start=F(5),
        source_time_end=F(6),
    )
    initial, initial_payload = exact_state(
        mounted, F(5), (ExactComplex(F(0)),) * 19
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="expression-mode-precision", maximum_precision_bits=4096
    )
    precision = PrecisionScheduleAuthority(
        "expression-mode-precision", 4096, receipt_sha256(precision_payload)
    )
    all_payloads = (
        *payloads,
        authority_payload,
        initial_payload,
        precision_payload,
    )
    receipts = registry(*all_payloads)
    expression = create_closed_experience_expression(
        topology=mounted,
        initial_state=initial,
        steps=(FieldExpressionStep(injection, authority),),
        precision_authority=precision,
        receipt_registry=receipts,
    )
    return expression, all_payloads


def test_expression_modes_bootstrap_two_independent_fields_then_recognize():
    first, first_payloads = make_axis_expression((F(1),) + (F(0),) * 18)
    second, second_payloads = make_axis_expression(
        (F(0), F(1)) + (F(0),) * 17
    )
    receipts = registry(*first_payloads, *second_payloads)
    bank = create_empty_expression_mode_bank(
        topology=first.topology,
        precision_authority=first.precision_authority,
        receipt_registry=receipts,
    )

    first_growth = evaluate_expression_mode_boundary(
        topology=first.topology,
        bank=bank,
        input_expression=first,
        receipt_registry=receipts,
    )
    second_growth = evaluate_expression_mode_boundary(
        topology=first.topology,
        bank=first_growth.post_growth_bank,
        input_expression=second,
        receipt_registry=receipts,
    )
    recognized = evaluate_expression_mode_boundary(
        topology=first.topology,
        bank=second_growth.post_growth_bank,
        input_expression=first,
        receipt_registry=receipts,
    )

    assert first_growth.status is ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
    assert second_growth.status is ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
    assert first_growth.post_growth_bank.rank == 1
    assert second_growth.post_growth_bank.rank == 2
    assert recognized.status is ExpressionRecognitionStatus.RECOGNIZED
    assert recognized.winner_mode_index == 0
    assert recognized.mutation is False
    assert b'"stored_numeric_representative":null' in second_growth.post_growth_bank.modes[0].receipt_payload


def test_expression_mode_growth_requires_certified_positive_orthogonal_residual():
    first, payloads = make_axis_expression((F(1),) + (F(0),) * 18)
    receipts = registry(*payloads)
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
    ).post_growth_bank

    dependent = evaluate_expression_mode_boundary(
        topology=first.topology,
        bank=one,
        input_expression=first,
        receipt_registry=receipts,
    )

    assert dependent.status is ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
    assert dependent.mutation is False
    assert dependent.post_growth_bank.rank == 1


def test_expression_modes_use_complete_vector_for_novel_and_ambiguous_silence():
    first, first_payloads = make_axis_expression((F(1),) + (F(0),) * 18)
    second, second_payloads = make_axis_expression(
        (F(0), F(1)) + (F(0),) * 17
    )
    third, third_payloads = make_axis_expression(
        (F(0), F(0), F(1)) + (F(0),) * 16
    )
    equal, equal_payloads = make_axis_expression(
        (F(1), F(1)) + (F(0),) * 17
    )
    receipts = registry(
        *first_payloads,
        *second_payloads,
        *third_payloads,
        *equal_payloads,
    )
    bank = create_empty_expression_mode_bank(
        topology=first.topology,
        precision_authority=first.precision_authority,
        receipt_registry=receipts,
    )
    for source in (first, second):
        bank = evaluate_expression_mode_boundary(
            topology=first.topology,
            bank=bank,
            input_expression=source,
            receipt_registry=receipts,
        ).post_growth_bank

    novel = evaluate_expression_mode_boundary(
        topology=first.topology,
        bank=bank,
        input_expression=third,
        receipt_registry=receipts,
    )
    ambiguous = evaluate_expression_mode_boundary(
        topology=first.topology,
        bank=bank,
        input_expression=equal,
        receipt_registry=receipts,
    )

    assert novel.status is ExpressionRecognitionStatus.NOVEL_SILENCE
    assert novel.mutation is True
    assert novel.post_growth_bank.rank == 3
    assert novel.post_growth_bank.modes[0].receipt_sha256 == bank.modes[0].receipt_sha256
    assert novel.post_growth_bank.modes[1].receipt_sha256 == bank.modes[1].receipt_sha256
    assert novel.post_growth_bank.receipt_sha256 != bank.receipt_sha256
    assert ambiguous.status is ExpressionRecognitionStatus.AMBIGUOUS_SILENCE
    assert ambiguous.mutation is False
    assert len(ambiguous.mode_probabilities) == 2
    assert ambiguous.certified_residual_probability is not None


def test_expression_mode_receipts_detect_source_expression_tamper():
    first, payloads = make_axis_expression((F(1),) + (F(0),) * 18)
    receipts = registry(*payloads)
    empty = create_empty_expression_mode_bank(
        topology=first.topology,
        precision_authority=first.precision_authority,
        receipt_registry=receipts,
    )
    bank = evaluate_expression_mode_boundary(
        topology=first.topology,
        bank=empty,
        input_expression=first,
        receipt_registry=receipts,
    ).post_growth_bank
    forged_source = replace(first, receipt_payload=b"forged source expression")
    forged_mode = replace(bank.modes[0], source_expression=forged_source)
    forged_bank = replace(bank, modes=(forged_mode,))

    with pytest.raises(ReceiptError, match="canonical receipt"):
        forged_bank.verify(topology=first.topology, receipt_registry=receipts)


def test_directed_h_mem_reevaluates_stable_expression_mode_endpoints_in_field():
    first, first_payloads = make_axis_expression((F(1),) + (F(0),) * 18)
    second, second_payloads = make_axis_expression(
        (F(0), F(1)) + (F(0),) * 17
    )
    base_receipts = registry(*first_payloads, *second_payloads)
    bank = create_empty_expression_mode_bank(
        topology=first.topology,
        precision_authority=first.precision_authority,
        receipt_registry=base_receipts,
    )
    for source in (first, second):
        bank = evaluate_expression_mode_boundary(
            topology=first.topology,
            bank=bank,
            input_expression=source,
            receipt_registry=base_receipts,
        ).post_growth_bank

    relation = DirectedRelation(
        0,
        1,
        bank.modes[0].receipt_sha256,
        bank.modes[1].receipt_sha256,
    )
    memory_payload = _exact_state_payload(
        source_time=F(6),
        structural_time_unit="structural_second",
        topology_authority_receipt_sha256=first.topology_authority_receipt_sha256,
        relation_order=(relation,),
        quiescent_mass=F(0),
        active_masses=(F(1),),
    )
    memory_state = ExactMemoryMassState(
        source_time=F(6),
        structural_time_unit="structural_second",
        topology_authority_receipt_sha256=first.topology_authority_receipt_sha256,
        relation_order=(relation,),
        quiescent_mass=F(0),
        active_masses=(F(1),),
        receipt_sha256=receipt_sha256(memory_payload),
        receipt_payload=memory_payload,
    )
    mask_payload = validity_mask_receipt_payload(
        mask_id="language-two-coordinate-mask",
        topology_authority_receipt_sha256=first.topology_authority_receipt_sha256,
        dimension=19,
        active_coordinates=(0, 1),
    )
    mask = MemoryValidityMask(
        mask_id="language-two-coordinate-mask",
        topology_authority_receipt_sha256=first.topology_authority_receipt_sha256,
        dimension=19,
        active_coordinates=(0, 1),
        authority_receipt_sha256=receipt_sha256(mask_payload),
    )
    h_authority_payload = h_mem_authority_receipt_payload(
        operator_id=H_MEM_OPERATOR_ID,
        memory_state_receipt_sha256=memory_state.receipt_sha256,
        mode_bank_receipt_sha256=bank.receipt_sha256,
        validity_mask_receipt_sha256=mask.authority_receipt_sha256,
    )
    h_authority = HMemOperatorAuthority(
        operator_id=H_MEM_OPERATOR_ID,
        memory_state_receipt_sha256=memory_state.receipt_sha256,
        mode_bank_receipt_sha256=bank.receipt_sha256,
        validity_mask_receipt_sha256=mask.authority_receipt_sha256,
        authority_receipt_sha256=receipt_sha256(h_authority_payload),
    )
    material = create_expression_h_mem_leaf_material(
        bank=bank,
        state=memory_state,
        validity_mask=mask,
        authority=h_authority,
    )
    all_payloads = (
        *first_payloads,
        *second_payloads,
        bank.receipt_payload,
        memory_payload,
        mask_payload,
        h_authority_payload,
        material.provider_expression_receipt_payload,
        material.reference.receipt_payload,
    )
    receipts = registry(*all_payloads)
    evaluator = ExpressionHMemEvaluator(
        topology=first.topology,
        bank=bank,
        state=memory_state,
        validity_mask=mask,
        authority=h_authority,
        receipt_registry=receipts,
        provider_expression_receipt_sha256=(
            material.reference.provider_expression_receipt_sha256
        ),
        dimension=19,
    )
    h_expression = create_closed_experience_expression(
        topology=first.topology,
        initial_state=first.initial_state,
        steps=(
            FieldExpressionStep(
                first.steps[0].injection,
                first.steps[0].authority,
                (material.reference,),
            ),
        ),
        precision_authority=first.precision_authority,
        receipt_registry=receipts,
    )

    result = evaluate_closed_experience_expression(
        h_expression,
        receipt_registry=receipts,
        hermitian_evaluators={
            material.reference.provider_expression_receipt_sha256: evaluator
        },
    )

    assert result.status is ExpressionEvaluationStatus.CERTIFIED
    assert material.reference.upper_nonzero_positions == ((0, 0), (0, 1), (1, 1))
    assert relation.source_mode_receipt_sha256 == bank.modes[0].receipt_sha256
    assert relation.target_mode_receipt_sha256 == bank.modes[1].receipt_sha256
    assert b"individual_mode_receipt_plus_checked_index" in material.provider_expression_receipt_payload
