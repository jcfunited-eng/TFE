"""Conformance tests for exact-projective GLEW mode recognition."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.certified_backend import CertifiedBall
from dsf_ai_service.glew_runtime.field import (
    FIBER_DIMENSION,
    CertifiedComplexBall,
    CertifiedFieldState,
    ExactComplex,
    ExactFieldState,
    MountedFieldTopology,
    PortFiber,
    _state_payload,
    exact_field_state_receipt_payload,
    field_topology_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.modes import (
    ENTROPY_OPERATOR_ID,
    MODE_OPERATOR_ID,
    NORMALIZED_MODE_EXPRESSION,
    CertifiedModeBank,
    ModeGrowthAuthority,
    RecognitionStatus,
    create_empty_mode_bank,
    evaluate_mode_boundary,
    mode_growth_authority_receipt_payload,
    reevaluate_mode_expression,
)


PRECISION = 256


def _topology(port_count: int = 1):
    fibers = tuple(
        PortFiber(f"lane-{index}", f"port-{index}")
        for index in range(port_count)
    )
    payload = field_topology_receipt_payload("mode-test-topology", fibers)
    topology = MountedFieldTopology(
        topology_id="mode-test-topology",
        ordered_port_fibers=fibers,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    return topology, payload


def _exact_state(
    topology: MountedFieldTopology,
    values: list[int | Fraction | tuple[int | Fraction, int | Fraction]],
    source_time: int,
) -> tuple[ExactFieldState, bytes]:
    padded = [*values, *([0] * (topology.dimension - len(values)))]
    amplitudes = tuple(
        ExactComplex(Fraction(value[0]), Fraction(value[1]))
        if isinstance(value, tuple)
        else ExactComplex(Fraction(value), Fraction(0))
        for value in padded
    )
    payload = exact_field_state_receipt_payload(
        topology.authority_receipt_sha256,
        Fraction(source_time),
        amplitudes,
    )
    return (
        ExactFieldState(
            topology_authority_receipt_sha256=(
                topology.authority_receipt_sha256
            ),
            source_time=Fraction(source_time),
            amplitudes=amplitudes,
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
    )


def _event(
    topology: MountedFieldTopology,
    topology_payload: bytes,
    values: list[int | Fraction | tuple[int | Fraction, int | Fraction]],
    source_time: int,
    *,
    eligible: bool = True,
):
    state, state_payload = _exact_state(topology, values, source_time)
    payloads: list[bytes] = [topology_payload, state_payload]
    authority = None
    if eligible:
        closed_payload = f"closed-experience-{source_time}".encode()
        authority_payload = mode_growth_authority_receipt_payload(
            authority_id=f"growth-{source_time}",
            topology_authority_receipt_sha256=(
                topology.authority_receipt_sha256
            ),
            source_state_authority_receipt_sha256=(
                state.authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=receipt_sha256(closed_payload),
        )
        authority = ModeGrowthAuthority(
            authority_id=f"growth-{source_time}",
            topology_authority_receipt_sha256=(
                topology.authority_receipt_sha256
            ),
            source_state_authority_receipt_sha256=(
                state.authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=receipt_sha256(closed_payload),
            authority_receipt_sha256=receipt_sha256(authority_payload),
        )
        payloads.extend((closed_payload, authority_payload))
    registry = ReceiptRegistry.from_payloads(
        profile_payload=b"mode-test-profile",
        receipt_payloads=tuple(payloads),
    )
    return state, registry, authority


def _evaluate(
    topology,
    topology_payload,
    bank,
    values,
    source_time,
    *,
    eligible=True,
):
    state, registry, authority = _event(
        topology,
        topology_payload,
        values,
        source_time,
        eligible=eligible,
    )
    return evaluate_mode_boundary(
        topology=topology,
        state=state,
        bank=bank,
        receipt_registry=registry,
        growth_authority=authority,
    )


def _bootstrap(topology, topology_payload):
    bank = create_empty_mode_bank(
        topology,
        working_precision_bits=PRECISION,
    )
    first = _evaluate(topology, topology_payload, bank, [1], 1)
    second = _evaluate(
        topology,
        topology_payload,
        first.post_growth_bank,
        [0, 1],
        2,
    )
    return first, second


def test_topology_sets_dimension_and_maximum_rank_to_nineteen_per_port():
    topology, _ = _topology(port_count=3)
    bank = create_empty_mode_bank(
        topology,
        working_precision_bits=PRECISION,
    )

    assert topology.dimension == 3 * FIBER_DIMENSION == 57
    assert bank.dimension == bank.max_rank == 57
    assert bank.rank == 0

    with pytest.raises(ReceiptError, match="rank exceeds"):
        CertifiedModeBank(
            topology_authority_receipt_sha256=(
                topology.authority_receipt_sha256
            ),
            dimension=1,
            working_precision_bits=PRECISION,
            modes=(None, None),  # type: ignore[arg-type]
            receipt_sha256="0" * 64,
            receipt_payload=b"not-reached",
        )


def test_first_two_independent_experiences_bootstrap_silently():
    topology, topology_payload = _topology()
    first, second = _bootstrap(topology, topology_payload)

    assert first.status is RecognitionStatus.BOOTSTRAP_SILENCE
    assert first.silent and first.recognized_mode_index is None
    assert first.pre_growth_bank.rank == 0
    assert first.post_growth_bank.rank == 1
    assert first.mutation_applied

    assert second.status is RecognitionStatus.BOOTSTRAP_SILENCE
    assert second.silent and second.recognized_mode_index is None
    assert second.pre_growth_bank.rank == 1
    assert second.post_growth_bank.rank == 2
    assert second.mutation_applied
    second.post_growth_bank.verify(topology)

    mode = second.post_growth_bank.modes[1]
    assert MODE_OPERATOR_ID.encode() in mode.receipt_payload
    assert NORMALIZED_MODE_EXPRESSION.encode() in mode.receipt_payload
    assert mode.projective_components[1] == ExactComplex(Fraction(1))


def test_exact_mode_expression_can_be_reevaluated_beyond_stored_precision():
    topology, topology_payload = _topology()
    bank = create_empty_mode_bank(
        topology,
        working_precision_bits=PRECISION,
    )
    first = _evaluate(topology, topology_payload, bank, [1, 1], 1)
    mode = first.post_growth_bank.modes[0]

    reevaluated = reevaluate_mode_expression(
        mode,
        working_precision_bits=512,
    )

    stored_lower, stored_upper = (
        Fraction(mode.evaluated_normalized_components[0].real.lower_mantissa)
        * Fraction(2)
        ** mode.evaluated_normalized_components[0].real.lower_exponent,
        Fraction(mode.evaluated_normalized_components[0].real.upper_mantissa)
        * Fraction(2)
        ** mode.evaluated_normalized_components[0].real.upper_exponent,
    )
    new_lower, new_upper = (
        Fraction(reevaluated[0].real.lower_mantissa)
        * Fraction(2) ** reevaluated[0].real.lower_exponent,
        Fraction(reevaluated[0].real.upper_mantissa)
        * Fraction(2) ** reevaluated[0].real.upper_exponent,
    )
    assert reevaluated[0].real.working_precision_bits == 512
    assert new_lower >= stored_lower
    assert new_upper <= stored_upper
    assert new_upper - new_lower < stored_upper - stored_lower


def test_dependent_second_experience_is_silent_and_does_not_mutate():
    topology, topology_payload = _topology()
    bank = create_empty_mode_bank(
        topology,
        working_precision_bits=PRECISION,
    )
    first = _evaluate(topology, topology_payload, bank, [1], 1)
    repeated = _evaluate(
        topology,
        topology_payload,
        first.post_growth_bank,
        [3],
        2,
    )

    assert repeated.status is RecognitionStatus.AMBIGUOUS_SILENCE
    assert repeated.post_growth_bank is repeated.pre_growth_bank
    assert not repeated.mutation_applied
    assert repeated.residual.exact_energy == 0


def test_exact_repeat_recognizes_existing_mode_without_growth():
    topology, topology_payload = _topology()
    _, second = _bootstrap(topology, topology_payload)
    bank = second.post_growth_bank

    repeat = _evaluate(topology, topology_payload, bank, [7], 3)

    assert repeat.status is RecognitionStatus.RECOGNIZED
    assert repeat.recognized_mode_index == 0
    assert repeat.residual.exact_energy == 0
    assert repeat.post_growth_bank is bank
    assert not repeat.mutation_applied


def test_residual_dominant_external_experience_grows_silently_after_decision():
    topology, topology_payload = _topology()
    _, second = _bootstrap(topology, topology_payload)
    bank = second.post_growth_bank

    # Existing mode e1 carries energy 1; the new e3 direction carries energy 9.
    novel = _evaluate(
        topology,
        topology_payload,
        bank,
        [0, 1, 0, 3],
        3,
    )

    assert novel.status is RecognitionStatus.NOVEL_SILENCE
    assert novel.silent and novel.recognized_mode_index is None
    assert novel.pre_growth_bank.rank == 2
    assert novel.post_growth_bank.rank == 3
    assert novel.mutation_applied
    assert novel.residual.exact_energy == 9
    assert novel.post_growth_bank.modes[2].projective_components[3] == ExactComplex(
        Fraction(1)
    )


def test_novel_mode_cannot_self_certify_in_the_event_that_creates_it():
    topology, topology_payload = _topology()
    _, second = _bootstrap(topology, topology_payload)
    bank = second.post_growth_bank

    novel = _evaluate(topology, topology_payload, bank, [0, 0, 1], 3)

    assert novel.status is RecognitionStatus.NOVEL_SILENCE
    assert novel.recognized_mode_index is None
    assert novel.pre_growth_bank.rank == 2
    assert novel.post_growth_bank.rank == 3
    assert novel.silent

    next_event = _evaluate(
        topology,
        topology_payload,
        novel.post_growth_bank,
        [0, 0, 5],
        4,
    )
    assert next_event.status is RecognitionStatus.RECOGNIZED
    assert next_event.recognized_mode_index == 2


def test_tied_stored_modes_are_ambiguous_and_growth_authority_cannot_override():
    topology, topology_payload = _topology()
    _, second = _bootstrap(topology, topology_payload)
    bank = second.post_growth_bank

    tied = _evaluate(topology, topology_payload, bank, [1, 1], 3)

    assert tied.status is RecognitionStatus.AMBIGUOUS_SILENCE
    assert tied.post_growth_bank is bank
    assert not tied.mutation_applied
    assert tuple(
        value.exact_probability
        for value in tied.entropy_receipt.mode_probabilities
    ) == (Fraction(1, 2), Fraction(1, 2))


def test_tiny_positive_innovation_grows_without_a_threshold_after_old_mode_wins():
    topology, topology_payload = _topology()
    _, second = _bootstrap(topology, topology_payload)
    bank = second.post_growth_bank

    result = _evaluate(
        topology,
        topology_payload,
        bank,
        [1_000_000, 0, 1],
        3,
    )

    assert result.status is RecognitionStatus.RECOGNIZED
    assert result.recognized_mode_index == 0
    assert result.residual.exact_energy == 1
    assert result.post_growth_bank.rank == 3
    assert result.mutation_applied


def test_positive_residual_does_not_mutate_without_upstream_growth_authority():
    topology, topology_payload = _topology()
    _, second = _bootstrap(topology, topology_payload)
    bank = second.post_growth_bank

    result = _evaluate(
        topology,
        topology_payload,
        bank,
        [10, 0, 1],
        3,
        eligible=False,
    )

    assert result.status is RecognitionStatus.RECOGNIZED
    assert result.recognized_mode_index == 0
    assert result.post_growth_bank is bank
    assert not result.mutation_applied
    assert "no upstream closed-experience" in result.reason


def test_probability_identity_preserves_every_mode_and_orthogonal_energy():
    topology, topology_payload = _topology()
    _, second = _bootstrap(topology, topology_payload)
    bank = second.post_growth_bank

    result = _evaluate(
        topology,
        topology_payload,
        bank,
        [2, 3, 6],
        3,
    )
    entropy = result.entropy_receipt
    probabilities = tuple(
        value.exact_probability for value in entropy.mode_probabilities
    ) + (entropy.exact_perpendicular_probability,)

    assert probabilities == (
        Fraction(4, 49),
        Fraction(9, 49),
        Fraction(36, 49),
    )
    assert sum(probabilities, Fraction(0)) == 1
    assert result.exact_total_field_energy == 49
    assert (
        sum(
            (
                value.exact_activation_energy
                for value in entropy.mode_probabilities
            ),
            result.residual.exact_energy,
        )
        == result.exact_total_field_energy
    )
    entropy.verify()
    assert ENTROPY_OPERATOR_ID.encode() in entropy.receipt_payload
    assert b"receipt_only_not_decision_authority" in entropy.receipt_payload


def test_full_rank_bank_never_grows_past_field_dimension_n():
    topology, topology_payload = _topology()
    _, second = _bootstrap(topology, topology_payload)
    bank = second.post_growth_bank
    source_time = 3

    for coordinate in range(2, topology.dimension):
        values = [10, 0] + [0] * (coordinate - 2) + [1]
        result = _evaluate(
            topology,
            topology_payload,
            bank,
            values,
            source_time,
        )
        assert result.status is RecognitionStatus.RECOGNIZED
        assert result.recognized_mode_index == 0
        assert result.post_growth_bank.rank == bank.rank + 1
        bank = result.post_growth_bank
        source_time += 1

    assert bank.rank == topology.dimension
    full = _evaluate(
        topology,
        topology_payload,
        bank,
        [10],
        source_time,
    )
    assert full.status is RecognitionStatus.RECOGNIZED
    assert full.post_growth_bank is bank
    assert not full.mutation_applied
    bank.verify(topology)


def test_tampered_mode_expression_is_rejected_before_recognition():
    topology, topology_payload = _topology()
    _, second = _bootstrap(topology, topology_payload)
    bank = second.post_growth_bank
    mode = bank.modes[1]
    tampered_mode = replace(
        mode,
        projective_components=(
            ExactComplex(Fraction(7)),
            *mode.projective_components[1:],
        ),
    )
    tampered_bank = replace(bank, modes=(bank.modes[0], tampered_mode))
    state, registry, authority = _event(
        topology, topology_payload, [1], 3
    )

    with pytest.raises(ReceiptError, match="not exactly orthogonal|fields differ"):
        evaluate_mode_boundary(
            topology=topology,
            state=state,
            bank=tampered_bank,
            receipt_registry=registry,
            growth_authority=authority,
        )


def test_fixed_certified_balls_are_rejected_as_non_executable_mode_authority():
    topology, topology_payload = _topology()
    bank = create_empty_mode_bank(
        topology,
        working_precision_bits=PRECISION,
    )
    amplitudes = tuple(
        CertifiedComplexBall(
            real=CertifiedBall(1 if index == 0 else 0, 0, 2 if index == 0 else 0, 0, PRECISION),
            imag=CertifiedBall(0, 0, 0, 0, PRECISION),
        )
        for index in range(topology.dimension)
    )
    payload = _state_payload(
        topology.authority_receipt_sha256,
        Fraction(1),
        amplitudes,
    )
    state = CertifiedFieldState(
        topology_authority_receipt_sha256=(
            topology.authority_receipt_sha256
        ),
        source_time=Fraction(1),
        amplitudes=amplitudes,
        receipt_sha256=receipt_sha256(payload),
    )
    registry = ReceiptRegistry.from_payloads(
        profile_payload=b"mode-test-profile",
        receipt_payloads=(topology_payload,),
    )

    with pytest.raises(ReceiptError, match="cannot be replayed as expressions"):
        evaluate_mode_boundary(  # type: ignore[arg-type]
            topology=topology,
            state=state,
            bank=bank,
            receipt_registry=registry,
            growth_authority=None,
        )


def test_growth_authority_for_a_different_state_is_rejected():
    topology, topology_payload = _topology()
    bank = create_empty_mode_bank(
        topology,
        working_precision_bits=PRECISION,
    )
    state, registry, _ = _event(topology, topology_payload, [1], 1)
    other, _, _ = _event(topology, topology_payload, [0, 1], 2)
    closed_payload = b"wrong-state-closed-experience"
    authority_payload = mode_growth_authority_receipt_payload(
        authority_id="wrong-state-growth",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        source_state_authority_receipt_sha256=other.authority_receipt_sha256,
        closed_experience_receipt_sha256=receipt_sha256(closed_payload),
    )
    authority = ModeGrowthAuthority(
        authority_id="wrong-state-growth",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        source_state_authority_receipt_sha256=other.authority_receipt_sha256,
        closed_experience_receipt_sha256=receipt_sha256(closed_payload),
        authority_receipt_sha256=receipt_sha256(authority_payload),
    )

    with pytest.raises(ReceiptError, match="different source state"):
        evaluate_mode_boundary(
            topology=topology,
            state=state,
            bank=bank,
            receipt_registry=registry,
            growth_authority=authority,
        )
