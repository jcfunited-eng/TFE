"""Directed H_mem adapter for expression-backed full-field mode endpoints.

The adapter reevaluates every endpoint from its stable source-expression mode
receipt in the caller's Arb context.  It constructs only the upper triangle of
the correlated directed H_mem expression; field evolution creates the lower
triangle by exact conjugate assignment from those same live objects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from .certified_backend import CertifiedBall, arb_fraction, canonical_ball
from .expression_modes import (
    ExpressionModeBank,
    reevaluate_expression_mode_endpoints_in_arb,
)
from .expressions import (
    EvaluatedHermitianUpperEntry,
    HermitianExpressionEvaluator,
    HermitianExpressionLeafReference,
    create_hermitian_leaf_reference,
)
from .field import MountedFieldTopology
from .memory import (
    CertifiedMemoryMassState,
    ExactMemoryMassState,
    HMemOperatorAuthority,
    MemoryValidityMask,
    SIMPLEX_CONSTRAINT_ID,
)
from .model import ReceiptError, ReceiptRegistry, receipt_sha256


MemoryMassState = ExactMemoryMassState | CertifiedMemoryMassState


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _relation_payload(relation) -> dict[str, object]:
    return {
        "source_mode_index": relation.source_mode_index,
        "source_mode_receipt_sha256": relation.source_mode_receipt_sha256,
        "target_mode_index": relation.target_mode_index,
        "target_mode_receipt_sha256": relation.target_mode_receipt_sha256,
    }


def expression_h_mem_receipt_payload(
    *,
    bank: ExpressionModeBank,
    state: MemoryMassState,
    validity_mask: MemoryValidityMask,
    authority: HMemOperatorAuthority,
) -> bytes:
    return _canonical_bytes(
        {
            "authority_receipt_sha256": authority.authority_receipt_sha256,
            "direction_rule": "ordered_mode_pair_uses_positive_i_skew_term",
            "endpoint_identity": [
                {
                    "mode_index": mode.mode_index,
                    "mode_receipt_sha256": mode.receipt_sha256,
                    "source_expression_receipt_sha256": (
                        mode.source_expression.receipt_sha256
                    ),
                }
                for mode in bank.modes
            ],
            "endpoint_operator": (
                "reevaluate_source_expressions_then_shared_arb_gram_schmidt"
                "_then_current_validity_mask_and_normalization"
            ),
            "factor": "1/(2*sqrt(2))",
            "hermitian_construction": (
                "upper_triangle_expression_then_same_object_exact_conjugate"
            ),
            "mass_correlation": {
                "constraint": SIMPLEX_CONSTRAINT_ID,
                "independent_interval_component_selection": "forbidden",
                "state_receipt_sha256": state.receipt_sha256,
            },
            "memory_state_receipt_sha256": state.receipt_sha256,
            "mode_bank_receipt_sha256": bank.receipt_sha256,
            "relations": [_relation_payload(value) for value in state.relation_order],
            "schema": "glew.expression_memory.correlated_H_mem.v1",
            "stable_relation_endpoint": "individual_mode_receipt_plus_checked_index",
            "validity_mask_receipt_sha256": validity_mask.authority_receipt_sha256,
        }
    )


def _mass_input_bit_lengths(state: MemoryMassState) -> tuple[int, ...]:
    result: list[int] = []
    for value in state.active_masses:
        if isinstance(value, Fraction):
            result.append(
                max(1, abs(value.numerator).bit_length())
                + value.denominator.bit_length()
            )
        else:
            result.extend(
                (
                    max(1, abs(value.lower_mantissa).bit_length())
                    + max(1, abs(value.lower_exponent).bit_length()),
                    max(1, abs(value.upper_mantissa).bit_length())
                    + max(1, abs(value.upper_exponent).bit_length()),
                )
            )
    return tuple(result or (1,))


def expression_h_mem_upper_positions(
    validity_mask: MemoryValidityMask,
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (row, column)
        for row in validity_mask.active_coordinates
        for column in validity_mask.active_coordinates
        if row <= column
    )


@dataclass(frozen=True, slots=True)
class ExpressionHMemLeafMaterial:
    provider_expression_receipt_payload: bytes
    reference: HermitianExpressionLeafReference


def create_expression_h_mem_leaf_material(
    *,
    bank: ExpressionModeBank,
    state: MemoryMassState,
    validity_mask: MemoryValidityMask,
    authority: HMemOperatorAuthority,
) -> ExpressionHMemLeafMaterial:
    payload = expression_h_mem_receipt_payload(
        bank=bank,
        state=state,
        validity_mask=validity_mask,
        authority=authority,
    )
    digest = receipt_sha256(payload)
    expression_bits = tuple(
        bit_length
        for mode in bank.modes
        for bit_length in mode.source_expression.exact_input_bit_lengths
    )
    dependencies = tuple(
        sorted(
            {
                authority.authority_receipt_sha256,
                bank.receipt_sha256,
                state.receipt_sha256,
                validity_mask.authority_receipt_sha256,
            }
        )
    )
    reference = create_hermitian_leaf_reference(
        leaf_id="expression-backed-directed-H-mem",
        dimension=bank.dimension,
        provider_expression_receipt_sha256=digest,
        dependency_receipt_sha256s=dependencies,
        exact_input_bit_lengths=(*expression_bits, *_mass_input_bit_lengths(state)),
        upper_nonzero_positions=expression_h_mem_upper_positions(validity_mask),
    )
    return ExpressionHMemLeafMaterial(
        provider_expression_receipt_payload=payload,
        reference=reference,
    )


def _dyadic_pair(value: Fraction) -> tuple[int, int]:
    denominator = value.denominator
    if denominator & (denominator - 1):
        raise ReceiptError("certified memory endpoint is not dyadic")
    return (value.numerator, -(denominator.bit_length() - 1))


def _arb_from_ball(flint, value: CertifiedBall):
    lower = Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent
    upper = Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent
    center = (lower + upper) / 2
    radius = (upper - lower) / 2
    return flint.arb(_dyadic_pair(center), _dyadic_pair(radius))


def _mass_value(flint, value: Fraction | CertifiedBall):
    return arb_fraction(flint, value) if isinstance(value, Fraction) else _arb_from_ball(flint, value)


def _mass_is_certified_zero(value: Fraction | CertifiedBall) -> bool:
    if isinstance(value, Fraction):
        return value == 0
    lower = Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent
    upper = Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent
    return lower == 0 and upper == 0


@dataclass(frozen=True, slots=True)
class ExpressionHMemEvaluator(HermitianExpressionEvaluator):
    topology: MountedFieldTopology
    bank: ExpressionModeBank
    state: MemoryMassState
    validity_mask: MemoryValidityMask
    authority: HMemOperatorAuthority
    receipt_registry: ReceiptRegistry
    provider_expression_receipt_sha256: str
    dimension: int
    nested_hermitian_evaluators: Mapping[str, HermitianExpressionEvaluator] | None = None

    def verify(self) -> None:
        self.topology.verify(self.receipt_registry)
        self.bank.verify(
            topology=self.topology, receipt_registry=self.receipt_registry
        )
        self.state.verify()
        self.validity_mask.verify(self.receipt_registry)
        self.authority.verify(self.receipt_registry)
        expected_payload = expression_h_mem_receipt_payload(
            bank=self.bank,
            state=self.state,
            validity_mask=self.validity_mask,
            authority=self.authority,
        )
        if self.provider_expression_receipt_sha256 != receipt_sha256(expected_payload):
            raise ReceiptError("expression H_mem evaluator has a different formula receipt")
        mounted = self.receipt_registry.resolve(
            self.provider_expression_receipt_sha256,
            "expression H_mem provider receipt",
        )
        if mounted != expected_payload:
            raise ReceiptError("expression H_mem formula differs from mounted bytes")
        if self.dimension != self.bank.dimension or self.dimension != self.validity_mask.dimension:
            raise ReceiptError("expression H_mem dimensions differ")
        if self.state.topology_authority_receipt_sha256 != self.topology.authority_receipt_sha256:
            raise ReceiptError("expression H_mem state belongs to another topology")
        if (
            self.authority.memory_state_receipt_sha256 != self.state.receipt_sha256
            or self.authority.mode_bank_receipt_sha256 != self.bank.receipt_sha256
            or self.authority.validity_mask_receipt_sha256
            != self.validity_mask.authority_receipt_sha256
        ):
            raise ReceiptError("expression H_mem authority names different dependencies")
        for relation in self.state.relation_order:
            if (
                relation.source_mode_index >= self.bank.rank
                or relation.target_mode_index >= self.bank.rank
            ):
                raise ReceiptError("expression H_mem relation names an unavailable mode")
            source = self.bank.modes[relation.source_mode_index]
            target = self.bank.modes[relation.target_mode_index]
            if (
                relation.source_mode_receipt_sha256 != source.receipt_sha256
                or relation.target_mode_receipt_sha256 != target.receipt_sha256
            ):
                raise ReceiptError("expression H_mem relation endpoint identity changed")
        for mode in self.bank.modes:
            if any(
                leaf.provider_expression_receipt_sha256
                == self.provider_expression_receipt_sha256
                for step in mode.source_expression.steps
                for leaf in step.hermitian_leaves
            ):
                raise ReceiptError("expression H_mem dependency graph contains a cycle")

    def evaluate_upper(
        self, *, flint: object, working_precision_bits: int
    ) -> tuple[EvaluatedHermitianUpperEntry, ...]:
        self.verify()
        endpoints = reevaluate_expression_mode_endpoints_in_arb(
            topology=self.topology,
            bank=self.bank,
            receipt_registry=self.receipt_registry,
            flint=flint,
            precision_bits=working_precision_bits,
            hermitian_evaluators=self.nested_hermitian_evaluators,
            active_coordinates=self.validity_mask.active_coordinates,
        )
        endpoint_by_index = {value.mode_index: value for value in endpoints}
        active_relations = tuple(
            (relation, mass)
            for relation, mass in zip(
                self.state.relation_order, self.state.active_masses, strict=True
            )
            if not _mass_is_certified_zero(mass)
        )
        for relation, _ in active_relations:
            if relation.source_mode_index == relation.target_mode_index:
                continue
            left = endpoint_by_index[relation.source_mode_index].normalized_amplitudes
            right = endpoint_by_index[relation.target_mode_index].normalized_amplitudes
            inner = sum(
                (u.conjugate() * v for u, v in zip(left, right, strict=True)),
                flint.acb(0),
            )
            gram = flint.arb(1) - (
                inner.real * inner.real + inner.imag * inner.imag
            )
            gram_ball = canonical_ball(gram, working_precision_bits)
            gram_lower = Fraction(gram_ball.lower_mantissa) * Fraction(2) ** gram_ball.lower_exponent
            if gram_lower <= 0:
                raise ReceiptError("validity mask does not certify distinct H_mem endpoints")

        mass_values = tuple(
            (relation, _mass_value(flint, mass))
            for relation, mass in active_relations
        )
        denominator = 2 * flint.arb(2).sqrt()
        imaginary_unit = flint.acb(0, 1)
        result: list[EvaluatedHermitianUpperEntry] = []
        for row, column in expression_h_mem_upper_positions(self.validity_mask):
            expression = flint.acb(0)
            for relation, mass in mass_values:
                source = endpoint_by_index[
                    relation.source_mode_index
                ].normalized_amplitudes
                target = endpoint_by_index[
                    relation.target_mode_index
                ].normalized_amplitudes
                if relation.source_mode_index == relation.target_mode_index:
                    relation_value = source[row] * source[column].conjugate()
                else:
                    a = source[row] * target[column].conjugate()
                    a_dagger = target[row] * source[column].conjugate()
                    relation_value = (
                        (a + a_dagger) + imaginary_unit * (a - a_dagger)
                    ) / denominator
                expression += mass * relation_value
            if row == column:
                expression = flint.acb(expression.real, 0)
            if not expression.is_finite():
                raise ReceiptError("expression-backed H_mem is nonfinite")
            result.append(EvaluatedHermitianUpperEntry(row, column, expression))
        return tuple(result)


__all__ = (
    "ExpressionHMemEvaluator",
    "ExpressionHMemLeafMaterial",
    "create_expression_h_mem_leaf_material",
    "expression_h_mem_receipt_payload",
    "expression_h_mem_upper_positions",
)
