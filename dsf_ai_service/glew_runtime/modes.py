"""Exact-projective GLEW mode memory with certified recognition receipts.

This module operates on one upstream-attested closed-experience field state. It
does not form that experience by summing post-gate states; that upstream
operator is deliberately outside this boundary.

Every admitted source component is exact rational-complex authority.  A mode
retains the exact canonical projective residual and the executable normalized
expression

    u / sqrt(<u, u>).

Pinned Arb evaluates that expression at the bank's receipt-bound precision.
Neither a midpoint nor a fixed interval replay is ever mode authority.  The
current ``CertifiedFieldState`` produced by field evolution is therefore not
accepted for growth: its balls are valid outward results, but the executable
expression needed for precision escalation is not present in that type.

Recognition decomposes the complete input over every pre-growth mode and the
exact orthogonal residual.  The resulting probabilities sum to one exactly
before Arb enclosure.  Stored recognition requires one certified lower bound
to exceed every other stored upper bound and the residual upper bound.  A
certified residual winner is a novel experience and remains silent.  Overlap or
ties are ambiguity: silence and no mutation.  Eligible residual growth occurs
only after this decision, so a new mode can never certify itself.

Entropy is a receipt over the complete probability vector only.  It is never a
recognition, growth, commit, or output gate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Sequence

from .certified_backend import (
    FLINT_VERSION,
    PYTHON_FLINT_VERSION,
    PYTHON_FLINT_WHEEL_SHA256,
    CertifiedBall,
    arb_fraction,
    canonical_ball,
    load_pinned_flint,
)
from .field import (
    FIBER_DIMENSION,
    CertifiedComplexBall,
    ExactComplex,
    ExactFieldState,
    MountedFieldTopology,
    exact_field_state_receipt_payload,
)
from .model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_identifier,
    sha256_digest,
)


MODE_OPERATOR_ID = "exact_projective_full_bank_gram_schmidt.v1"
NORMALIZED_MODE_EXPRESSION = "u/sqrt(<u,u>)"
RECOGNITION_OPERATOR_ID = "certified_unique_full_vector_dominance.v1"
ENTROPY_OPERATOR_ID = "full_probability_vector_shannon_receipt.v1"


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _exact_payload(value: ExactComplex) -> dict[str, str]:
    return {
        "imag": _fraction_text(value.imag),
        "real": _fraction_text(value.real),
    }


def _ball_payload(value: CertifiedBall) -> dict[str, object]:
    return {
        "flint_version": value.flint_version,
        "lower_exponent": value.lower_exponent,
        "lower_mantissa": value.lower_mantissa,
        "python_flint_version": value.python_flint_version,
        "upper_exponent": value.upper_exponent,
        "upper_mantissa": value.upper_mantissa,
        "wheel_sha256": value.wheel_sha256,
        "working_precision_bits": value.working_precision_bits,
    }


def _complex_ball_payload(value: CertifiedComplexBall) -> dict[str, object]:
    return {"imag": _ball_payload(value.imag), "real": _ball_payload(value.real)}


def _ball_bounds(value: CertifiedBall) -> tuple[Fraction, Fraction]:
    return (
        Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent,
        Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent,
    )


def _c_add(left: ExactComplex, right: ExactComplex) -> ExactComplex:
    return ExactComplex(left.real + right.real, left.imag + right.imag)


def _c_sub(left: ExactComplex, right: ExactComplex) -> ExactComplex:
    return ExactComplex(left.real - right.real, left.imag - right.imag)


def _c_mul(left: ExactComplex, right: ExactComplex) -> ExactComplex:
    return ExactComplex(
        left.real * right.real - left.imag * right.imag,
        left.real * right.imag + left.imag * right.real,
    )


def _c_div(left: ExactComplex, right: ExactComplex) -> ExactComplex:
    denominator = right.real * right.real + right.imag * right.imag
    if denominator == 0:
        raise ReceiptError("exact complex division by zero")
    numerator = _c_mul(left, right.conjugate())
    return ExactComplex(numerator.real / denominator, numerator.imag / denominator)


def _c_scale(value: ExactComplex, scalar: Fraction) -> ExactComplex:
    return ExactComplex(value.real * scalar, value.imag * scalar)


def _inner(
    left: Sequence[ExactComplex], right: Sequence[ExactComplex]
) -> ExactComplex:
    if len(left) != len(right):
        raise ReceiptError("inner-product dimensions differ")
    total = ExactComplex(Fraction(0), Fraction(0))
    for left_value, right_value in zip(left, right, strict=True):
        total = _c_add(total, _c_mul(left_value.conjugate(), right_value))
    return total


def _energy(values: Sequence[ExactComplex]) -> Fraction:
    value = _inner(values, values)
    if value.imag != 0 or value.real < 0:
        raise ReceiptError("exact field norm is not nonnegative real")
    return value.real


def _orthogonal_residual(
    source: Sequence[ExactComplex],
    projective_modes: Sequence[Sequence[ExactComplex]],
) -> tuple[ExactComplex, ...]:
    residual = tuple(source)
    for mode in projective_modes:
        norm = _energy(mode)
        if norm <= 0:
            raise ReceiptError("stored projective mode has zero norm")
        coefficient = _c_scale(_inner(mode, residual), Fraction(1, 1) / norm)
        residual = tuple(
            _c_sub(value, _c_mul(component, coefficient))
            for value, component in zip(residual, mode, strict=True)
        )
    return residual


def _canonical_projective(
    values: Sequence[ExactComplex],
) -> tuple[ExactComplex, ...]:
    pivot = next(
        (value for value in values if not value.is_zero),
        None,
    )
    if pivot is None:
        raise ReceiptError("zero residual has no projective direction")
    result = tuple(_c_div(value, pivot) for value in values)
    first_nonzero = next(value for value in result if not value.is_zero)
    if first_nonzero != ExactComplex(Fraction(1), Fraction(0)):
        raise ReceiptError("projective canonicalization did not establish unit pivot")
    return result


def _acb_exact(flint, value: ExactComplex):
    return flint.acb(
        arb_fraction(flint, value.real),
        arb_fraction(flint, value.imag),
    )


def _certified_normalized_mode(
    flint,
    projective_components: Sequence[ExactComplex],
    projective_norm_squared: Fraction,
    precision_bits: int,
) -> tuple[CertifiedComplexBall, ...]:
    norm = arb_fraction(flint, projective_norm_squared).sqrt()
    if not norm.is_finite() or norm.contains(0):
        raise ReceiptError("normalized mode expression is not certified finite")
    return tuple(
        CertifiedComplexBall(
            real=canonical_ball(
                (_acb_exact(flint, value) / norm).real,
                precision_bits,
            ),
            imag=canonical_ball(
                (_acb_exact(flint, value) / norm).imag,
                precision_bits,
            ),
        )
        for value in projective_components
    )


def reevaluate_mode_expression(
    mode: "CertifiedMode",
    *,
    working_precision_bits: int,
) -> tuple[CertifiedComplexBall, ...]:
    """Reevaluate a stored exact expression without replaying its old balls."""

    if not isinstance(mode, CertifiedMode):
        raise ReceiptError("mode expression evaluation requires a certified mode")
    mode.verify_receipt()
    if (
        isinstance(working_precision_bits, bool)
        or not isinstance(working_precision_bits, int)
        or working_precision_bits <= 0
    ):
        raise ReceiptError("mode expression precision must be a positive integer")
    flint = load_pinned_flint()
    with flint.ctx.workprec(working_precision_bits):
        return _certified_normalized_mode(
            flint,
            mode.projective_components,
            mode.projective_norm_squared,
            working_precision_bits,
        )


@dataclass(frozen=True, slots=True)
class ModeGrowthAuthority:
    """Upstream receipt that one exact state is eligible closed experience.

    This type binds an upstream decision; it deliberately does not invent how
    multiple post-gate states become a closed experience.
    """

    authority_id: str
    topology_authority_receipt_sha256: str
    source_state_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.authority_id, "growth authority id")
        sha256_digest(
            self.topology_authority_receipt_sha256,
            "growth topology receipt",
        )
        sha256_digest(
            self.source_state_authority_receipt_sha256,
            "growth source-state receipt",
        )
        sha256_digest(
            self.closed_experience_receipt_sha256,
            "closed-experience receipt",
        )
        sha256_digest(self.authority_receipt_sha256, "growth authority receipt")

    def verify(
        self,
        *,
        topology: MountedFieldTopology,
        state: ExactFieldState,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if (
            self.topology_authority_receipt_sha256
            != topology.authority_receipt_sha256
        ):
            raise ReceiptError("growth authority belongs to a different topology")
        if self.source_state_authority_receipt_sha256 != state.authority_receipt_sha256:
            raise ReceiptError("growth authority belongs to a different source state")
        receipt_registry.resolve(
            self.closed_experience_receipt_sha256,
            "closed-experience receipt",
        )
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256,
            "mode-growth authority receipt",
        )
        expected = mode_growth_authority_receipt_payload(
            authority_id=self.authority_id,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            source_state_authority_receipt_sha256=(
                self.source_state_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
        )
        if mounted != expected:
            raise ReceiptError("mode-growth authority differs from mounted bytes")


def mode_growth_authority_receipt_payload(
    *,
    authority_id: str,
    topology_authority_receipt_sha256: str,
    source_state_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
) -> bytes:
    require_identifier(authority_id, "growth authority id")
    for value, name in (
        (topology_authority_receipt_sha256, "growth topology receipt"),
        (source_state_authority_receipt_sha256, "growth source-state receipt"),
        (closed_experience_receipt_sha256, "closed-experience receipt"),
    ):
        sha256_digest(value, name)
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "scope": "upstream_attested_single_closed_experience_field_state",
            "schema": "glew.mode_growth_authority.v1",
            "source_state_authority_receipt_sha256": (
                source_state_authority_receipt_sha256
            ),
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class CertifiedMode:
    """Exact projective direction plus executable normalized evaluation."""

    mode_index: int
    topology_authority_receipt_sha256: str
    source_state: ExactFieldState
    source_state_authority_payload: bytes
    pre_growth_bank_receipt_sha256: str
    dependency_mode_receipt_sha256s: tuple[str, ...]
    projective_components: tuple[ExactComplex, ...]
    projective_norm_squared: Fraction
    residual_energy_before_canonicalization: Fraction
    evaluated_normalized_components: tuple[CertifiedComplexBall, ...]
    working_precision_bits: int
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        if (
            isinstance(self.mode_index, bool)
            or not isinstance(self.mode_index, int)
            or self.mode_index < 0
        ):
            raise ReceiptError("mode index must be a nonnegative integer")
        sha256_digest(
            self.topology_authority_receipt_sha256, "mode topology receipt"
        )
        sha256_digest(
            self.pre_growth_bank_receipt_sha256, "mode pre-growth bank receipt"
        )
        for digest in self.dependency_mode_receipt_sha256s:
            sha256_digest(digest, "mode dependency receipt")
        if not isinstance(self.source_state, ExactFieldState):
            raise ReceiptError("mode source must be an exact field state")
        if (
            not isinstance(self.source_state_authority_payload, bytes)
            or not self.source_state_authority_payload
        ):
            raise ReceiptError("mode source authority payload must be exact bytes")
        if not all(
            isinstance(value, ExactComplex) for value in self.projective_components
        ):
            raise ReceiptError("mode projective components must be exact complex values")
        if not isinstance(self.projective_norm_squared, Fraction):
            raise ReceiptError("mode projective norm must be exact Fraction")
        if not isinstance(self.residual_energy_before_canonicalization, Fraction):
            raise ReceiptError("mode residual energy must be exact Fraction")
        if self.projective_norm_squared <= 0:
            raise ReceiptError("mode projective norm must be positive")
        if self.residual_energy_before_canonicalization <= 0:
            raise ReceiptError("mode residual energy must be positive")
        if (
            isinstance(self.working_precision_bits, bool)
            or not isinstance(self.working_precision_bits, int)
            or self.working_precision_bits <= 0
        ):
            raise ReceiptError("mode precision must be a positive integer")
        sha256_digest(self.receipt_sha256, "mode receipt")
        if receipt_sha256(self.receipt_payload) != self.receipt_sha256:
            raise ReceiptError("mode receipt payload does not match its digest")

    def verify_receipt(self) -> None:
        expected_source = exact_field_state_receipt_payload(
            self.source_state.topology_authority_receipt_sha256,
            self.source_state.source_time,
            self.source_state.amplitudes,
        )
        if expected_source != self.source_state_authority_payload:
            raise ReceiptError("mode source differs from preserved authority bytes")
        if receipt_sha256(expected_source) != self.source_state.authority_receipt_sha256:
            raise ReceiptError("mode source authority digest is inconsistent")
        expected = _mode_receipt_payload(
            mode_index=self.mode_index,
            topology_authority_receipt_sha256=self.topology_authority_receipt_sha256,
            source_state=self.source_state,
            source_state_authority_payload=self.source_state_authority_payload,
            pre_growth_bank_receipt_sha256=self.pre_growth_bank_receipt_sha256,
            dependency_mode_receipt_sha256s=self.dependency_mode_receipt_sha256s,
            projective_components=self.projective_components,
            projective_norm_squared=self.projective_norm_squared,
            residual_energy_before_canonicalization=(
                self.residual_energy_before_canonicalization
            ),
            evaluated_normalized_components=(
                self.evaluated_normalized_components
            ),
            working_precision_bits=self.working_precision_bits,
        )
        if expected != self.receipt_payload:
            raise ReceiptError("mode fields differ from their expression receipt")


def _mode_receipt_payload(
    *,
    mode_index: int,
    topology_authority_receipt_sha256: str,
    source_state: ExactFieldState,
    source_state_authority_payload: bytes,
    pre_growth_bank_receipt_sha256: str,
    dependency_mode_receipt_sha256s: Sequence[str],
    projective_components: Sequence[ExactComplex],
    projective_norm_squared: Fraction,
    residual_energy_before_canonicalization: Fraction,
    evaluated_normalized_components: Sequence[CertifiedComplexBall],
    working_precision_bits: int,
) -> bytes:
    return _canonical_bytes(
        {
            "dependency_mode_receipt_sha256s": list(
                dependency_mode_receipt_sha256s
            ),
            "evaluated_normalized_components": [
                _complex_ball_payload(value)
                for value in evaluated_normalized_components
            ],
            "mode_index": mode_index,
            "normalized_expression": NORMALIZED_MODE_EXPRESSION,
            "operator": MODE_OPERATOR_ID,
            "pre_growth_bank_receipt_sha256": pre_growth_bank_receipt_sha256,
            "projective_components": [
                _exact_payload(value) for value in projective_components
            ],
            "projective_norm_squared": _fraction_text(projective_norm_squared),
            "residual_energy_before_canonicalization": _fraction_text(
                residual_energy_before_canonicalization
            ),
            "schema": "glew.mode.exact_projective_expression.v1",
            "source_state_authority_payload_sha256": receipt_sha256(
                source_state_authority_payload
            ),
            "source_state_authority_receipt_sha256": (
                source_state.authority_receipt_sha256
            ),
            "source_time": _fraction_text(source_state.source_time),
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
            "working_precision_bits": working_precision_bits,
        }
    )


@dataclass(frozen=True, slots=True)
class CertifiedModeBank:
    topology_authority_receipt_sha256: str
    dimension: int
    working_precision_bits: int
    modes: tuple[CertifiedMode, ...]
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        sha256_digest(
            self.topology_authority_receipt_sha256, "bank topology receipt"
        )
        if (
            isinstance(self.dimension, bool)
            or not isinstance(self.dimension, int)
            or self.dimension <= 0
        ):
            raise ReceiptError("mode-bank dimension must be a positive integer")
        if (
            isinstance(self.working_precision_bits, bool)
            or not isinstance(self.working_precision_bits, int)
            or self.working_precision_bits <= 0
        ):
            raise ReceiptError("mode-bank precision must be a positive integer")
        if len(self.modes) > self.dimension:
            raise ReceiptError("mode-bank rank exceeds field dimension N")
        if not all(isinstance(mode, CertifiedMode) for mode in self.modes):
            raise ReceiptError("mode bank contains a non-certified mode")
        sha256_digest(self.receipt_sha256, "mode-bank receipt")
        if receipt_sha256(self.receipt_payload) != self.receipt_sha256:
            raise ReceiptError("mode-bank receipt payload does not match its digest")

    @property
    def rank(self) -> int:
        return len(self.modes)

    @property
    def max_rank(self) -> int:
        return self.dimension

    def verify(self, topology: MountedFieldTopology, *, recompute: bool = True) -> None:
        if not isinstance(topology, MountedFieldTopology):
            raise ReceiptError("mode-bank verification requires a mounted topology")
        if topology.dimension != FIBER_DIMENSION * len(
            topology.ordered_port_fibers
        ):
            raise ReceiptError("topology dimension is not nineteen per mounted port")
        if topology.dimension != self.dimension:
            raise ReceiptError("mode-bank dimension differs from mounted topology")
        if (
            topology.authority_receipt_sha256
            != self.topology_authority_receipt_sha256
        ):
            raise ReceiptError("mode bank belongs to a different topology")
        expected_payload = _mode_bank_receipt_payload(
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            dimension=self.dimension,
            working_precision_bits=self.working_precision_bits,
            modes=self.modes,
        )
        if expected_payload != self.receipt_payload:
            raise ReceiptError("mode-bank fields differ from their receipt")

        prefix = create_empty_mode_bank(
            topology,
            working_precision_bits=self.working_precision_bits,
        )
        for index, mode in enumerate(self.modes):
            if mode.mode_index != index:
                raise ReceiptError("mode bank is not in canonical creation order")
            if len(mode.projective_components) != self.dimension:
                raise ReceiptError("stored mode dimension differs from bank")
            if mode.working_precision_bits != self.working_precision_bits:
                raise ReceiptError("stored mode precision differs from bank")
            if mode.dependency_mode_receipt_sha256s != tuple(
                prior.receipt_sha256 for prior in prefix.modes
            ):
                raise ReceiptError("mode expression omits a pre-growth dependency")
            if mode.pre_growth_bank_receipt_sha256 != prefix.receipt_sha256:
                raise ReceiptError("mode expression names a different pre-growth bank")
            for prior in prefix.modes:
                if _inner(
                    prior.projective_components,
                    mode.projective_components,
                ) != ExactComplex(Fraction(0), Fraction(0)):
                    raise ReceiptError("stored modes are not exactly orthogonal")
            mode.verify_receipt()
            if recompute and _grow_mode(topology, prefix, mode.source_state) != mode:
                raise ReceiptError(
                    "stored mode differs from executable source expression"
                )
            prefix = _append_mode(prefix, mode)


def _mode_bank_receipt_payload(
    *,
    topology_authority_receipt_sha256: str,
    dimension: int,
    working_precision_bits: int,
    modes: Sequence[CertifiedMode],
) -> bytes:
    return _canonical_bytes(
        {
            "dimension": dimension,
            "max_rank": dimension,
            "mode_receipt_sha256s": [mode.receipt_sha256 for mode in modes],
            "rank": len(modes),
            "schema": "glew.mode_bank.exact_projective.v1",
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
            "working_precision_bits": working_precision_bits,
        }
    )


def _make_bank(
    *,
    topology_authority_receipt_sha256: str,
    dimension: int,
    working_precision_bits: int,
    modes: Sequence[CertifiedMode],
) -> CertifiedModeBank:
    immutable_modes = tuple(modes)
    payload = _mode_bank_receipt_payload(
        topology_authority_receipt_sha256=topology_authority_receipt_sha256,
        dimension=dimension,
        working_precision_bits=working_precision_bits,
        modes=immutable_modes,
    )
    return CertifiedModeBank(
        topology_authority_receipt_sha256=topology_authority_receipt_sha256,
        dimension=dimension,
        working_precision_bits=working_precision_bits,
        modes=immutable_modes,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


def create_empty_mode_bank(
    topology: MountedFieldTopology,
    *,
    working_precision_bits: int,
) -> CertifiedModeBank:
    if not isinstance(topology, MountedFieldTopology):
        raise ReceiptError("mode bank requires a mounted topology")
    if not topology.available:
        raise ReceiptError("mode bank requires at least one mounted port")
    if topology.dimension != FIBER_DIMENSION * len(topology.ordered_port_fibers):
        raise ReceiptError("topology dimension is not nineteen per mounted port")
    if (
        isinstance(working_precision_bits, bool)
        or not isinstance(working_precision_bits, int)
        or working_precision_bits <= 0
    ):
        raise ReceiptError("mode bank requires an explicit positive Arb precision")
    return _make_bank(
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        dimension=topology.dimension,
        working_precision_bits=working_precision_bits,
        modes=(),
    )


def _append_mode(bank: CertifiedModeBank, mode: CertifiedMode) -> CertifiedModeBank:
    if bank.rank >= bank.max_rank:
        raise ReceiptError("mode-bank rank cannot exceed field dimension N")
    if mode.mode_index != bank.rank:
        raise ReceiptError("new mode index differs from pre-growth bank rank")
    return _make_bank(
        topology_authority_receipt_sha256=(
            bank.topology_authority_receipt_sha256
        ),
        dimension=bank.dimension,
        working_precision_bits=bank.working_precision_bits,
        modes=(*bank.modes, mode),
    )


def _grow_mode(
    topology: MountedFieldTopology,
    bank: CertifiedModeBank,
    state: ExactFieldState,
) -> CertifiedMode:
    if bank.rank >= bank.max_rank:
        raise ReceiptError("full-rank mode bank cannot grow")
    if state.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
        raise ReceiptError("mode source belongs to a different topology")
    if len(state.amplitudes) != topology.dimension:
        raise ReceiptError("mode source dimension differs from topology")
    residual = _orthogonal_residual(
        state.amplitudes,
        tuple(mode.projective_components for mode in bank.modes),
    )
    residual_energy = _energy(residual)
    if residual_energy <= 0:
        raise ReceiptError("new mode requires positive exact orthogonal energy")
    projective = _canonical_projective(residual)
    projective_norm = _energy(projective)
    flint = load_pinned_flint()
    with flint.ctx.workprec(bank.working_precision_bits):
        evaluated = _certified_normalized_mode(
            flint,
            projective,
            projective_norm,
            bank.working_precision_bits,
        )
    source_payload = exact_field_state_receipt_payload(
        state.topology_authority_receipt_sha256,
        state.source_time,
        state.amplitudes,
    )
    if receipt_sha256(source_payload) != state.authority_receipt_sha256:
        raise ReceiptError("mode source does not match its exact authority digest")
    payload = _mode_receipt_payload(
        mode_index=bank.rank,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        source_state=state,
        source_state_authority_payload=source_payload,
        pre_growth_bank_receipt_sha256=bank.receipt_sha256,
        dependency_mode_receipt_sha256s=tuple(
            mode.receipt_sha256 for mode in bank.modes
        ),
        projective_components=projective,
        projective_norm_squared=projective_norm,
        residual_energy_before_canonicalization=residual_energy,
        evaluated_normalized_components=evaluated,
        working_precision_bits=bank.working_precision_bits,
    )
    return CertifiedMode(
        mode_index=bank.rank,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        source_state=state,
        source_state_authority_payload=source_payload,
        pre_growth_bank_receipt_sha256=bank.receipt_sha256,
        dependency_mode_receipt_sha256s=tuple(
            mode.receipt_sha256 for mode in bank.modes
        ),
        projective_components=projective,
        projective_norm_squared=projective_norm,
        residual_energy_before_canonicalization=residual_energy,
        evaluated_normalized_components=evaluated,
        working_precision_bits=bank.working_precision_bits,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


@dataclass(frozen=True, slots=True)
class CertifiedResidual:
    exact_amplitudes: tuple[ExactComplex, ...]
    certified_amplitudes: tuple[CertifiedComplexBall, ...]
    exact_energy: Fraction
    certified_energy: CertifiedBall
    receipt_sha256: str
    receipt_payload: bytes


@dataclass(frozen=True, slots=True)
class ModeProbability:
    mode_index: int
    mode_receipt_sha256: str
    exact_activation_energy: Fraction
    certified_activation_energy: CertifiedBall
    exact_probability: Fraction
    certified_probability: CertifiedBall


@dataclass(frozen=True, slots=True)
class EntropyVectorReceipt:
    mode_probabilities: tuple[ModeProbability, ...]
    exact_perpendicular_probability: Fraction
    certified_perpendicular_probability: CertifiedBall
    certified_entropy: CertifiedBall
    receipt_sha256: str
    receipt_payload: bytes

    def verify(self) -> None:
        probabilities = tuple(
            value.exact_probability for value in self.mode_probabilities
        ) + (self.exact_perpendicular_probability,)
        if sum(probabilities, Fraction(0)) != 1:
            raise ReceiptError("entropy probability vector does not sum exactly to one")
        expected = _entropy_receipt_payload(
            self.mode_probabilities,
            self.exact_perpendicular_probability,
            self.certified_perpendicular_probability,
            self.certified_entropy,
        )
        if expected != self.receipt_payload or receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("entropy fields differ from full-vector receipt")


class RecognitionStatus(str, Enum):
    BOOTSTRAP_SILENCE = "bootstrap_silence"
    RECOGNIZED = "recognized"
    NOVEL_SILENCE = "novel_silence"
    AMBIGUOUS_SILENCE = "ambiguous_silence"


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    status: RecognitionStatus
    recognized_mode_index: int | None
    pre_growth_bank: CertifiedModeBank
    post_growth_bank: CertifiedModeBank
    residual: CertifiedResidual
    exact_total_field_energy: Fraction
    certified_total_field_energy: CertifiedBall
    entropy_receipt: EntropyVectorReceipt
    mutation_applied: bool
    reason: str
    receipt_sha256: str
    receipt_payload: bytes

    @property
    def silent(self) -> bool:
        return self.status is not RecognitionStatus.RECOGNIZED


def _residual_receipt(
    *,
    flint,
    residual: Sequence[ExactComplex],
    energy: Fraction,
    precision_bits: int,
    state: ExactFieldState,
    bank: CertifiedModeBank,
) -> CertifiedResidual:
    certified = tuple(
        CertifiedComplexBall(
            real=canonical_ball(arb_fraction(flint, value.real), precision_bits),
            imag=canonical_ball(arb_fraction(flint, value.imag), precision_bits),
        )
        for value in residual
    )
    energy_ball = canonical_ball(arb_fraction(flint, energy), precision_bits)
    payload = _canonical_bytes(
        {
            "certified_amplitudes": [
                _complex_ball_payload(value) for value in certified
            ],
            "certified_energy": _ball_payload(energy_ball),
            "exact_amplitudes": [_exact_payload(value) for value in residual],
            "exact_energy": _fraction_text(energy),
            "operator": MODE_OPERATOR_ID,
            "pre_growth_bank_receipt_sha256": bank.receipt_sha256,
            "schema": "glew.mode.exact_orthogonal_residual.v1",
            "source_state_authority_receipt_sha256": (
                state.authority_receipt_sha256
            ),
        }
    )
    return CertifiedResidual(
        exact_amplitudes=tuple(residual),
        certified_amplitudes=certified,
        exact_energy=energy,
        certified_energy=energy_ball,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


def _entropy_receipt_payload(
    mode_probabilities: Sequence[ModeProbability],
    exact_perpendicular_probability: Fraction,
    certified_perpendicular_probability: CertifiedBall,
    certified_entropy: CertifiedBall,
) -> bytes:
    return _canonical_bytes(
        {
            "certified_entropy": _ball_payload(certified_entropy),
            "mode_probabilities": [
                {
                    "certified_activation_energy": _ball_payload(
                        value.certified_activation_energy
                    ),
                    "certified_probability": _ball_payload(
                        value.certified_probability
                    ),
                    "exact_activation_energy": _fraction_text(
                        value.exact_activation_energy
                    ),
                    "exact_probability": _fraction_text(value.exact_probability),
                    "mode_index": value.mode_index,
                    "mode_receipt_sha256": value.mode_receipt_sha256,
                }
                for value in mode_probabilities
            ],
            "operator": ENTROPY_OPERATOR_ID,
            "perpendicular_probability": {
                "certified": _ball_payload(certified_perpendicular_probability),
                "exact": _fraction_text(exact_perpendicular_probability),
            },
            "schema": "glew.mode.full_probability_entropy.v1",
            "use": "receipt_only_not_decision_authority",
        }
    )


def _make_entropy_receipt(
    *,
    flint,
    mode_probabilities: Sequence[ModeProbability],
    perpendicular_probability: Fraction,
    precision_bits: int,
) -> EntropyVectorReceipt:
    exact_vector = tuple(
        value.exact_probability for value in mode_probabilities
    ) + (perpendicular_probability,)
    if any(value < 0 or value > 1 for value in exact_vector):
        raise ReceiptError("exact projection produced a non-probability")
    if sum(exact_vector, Fraction(0)) != 1:
        raise ReceiptError("full probability vector does not sum exactly to one")
    entropy = flint.arb(0)
    for probability in exact_vector:
        if probability == 0:
            continue
        arb_probability = arb_fraction(flint, probability)
        entropy -= arb_probability * arb_probability.log()
    entropy_ball = canonical_ball(entropy, precision_bits)
    perpendicular_ball = canonical_ball(
        arb_fraction(flint, perpendicular_probability), precision_bits
    )
    payload = _entropy_receipt_payload(
        mode_probabilities,
        perpendicular_probability,
        perpendicular_ball,
        entropy_ball,
    )
    return EntropyVectorReceipt(
        mode_probabilities=tuple(mode_probabilities),
        exact_perpendicular_probability=perpendicular_probability,
        certified_perpendicular_probability=perpendicular_ball,
        certified_entropy=entropy_ball,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


def _result_payload(
    *,
    status: RecognitionStatus,
    winner: int | None,
    before: CertifiedModeBank,
    after: CertifiedModeBank,
    residual: CertifiedResidual,
    total_energy: Fraction,
    total_energy_ball: CertifiedBall,
    entropy: EntropyVectorReceipt,
    mutation: bool,
    reason: str,
) -> bytes:
    return _canonical_bytes(
        {
            "certified_total_field_energy": _ball_payload(total_energy_ball),
            "entropy_receipt_sha256": entropy.receipt_sha256,
            "exact_total_field_energy": _fraction_text(total_energy),
            "mutation_applied": mutation,
            "operator": RECOGNITION_OPERATOR_ID,
            "post_growth_bank_receipt_sha256": after.receipt_sha256,
            "pre_growth_bank_receipt_sha256": before.receipt_sha256,
            "reason": reason,
            "recognized_mode_index": winner,
            "residual_receipt_sha256": residual.receipt_sha256,
            "schema": "glew.mode.recognition_result.v1",
            "status": status.value,
        }
    )


def _make_result(
    *,
    status: RecognitionStatus,
    winner: int | None,
    before: CertifiedModeBank,
    after: CertifiedModeBank,
    residual: CertifiedResidual,
    total_energy: Fraction,
    total_energy_ball: CertifiedBall,
    entropy: EntropyVectorReceipt,
    mutation: bool,
    reason: str,
) -> RecognitionResult:
    payload = _result_payload(
        status=status,
        winner=winner,
        before=before,
        after=after,
        residual=residual,
        total_energy=total_energy,
        total_energy_ball=total_energy_ball,
        entropy=entropy,
        mutation=mutation,
        reason=reason,
    )
    return RecognitionResult(
        status=status,
        recognized_mode_index=winner,
        pre_growth_bank=before,
        post_growth_bank=after,
        residual=residual,
        exact_total_field_energy=total_energy,
        certified_total_field_energy=total_energy_ball,
        entropy_receipt=entropy,
        mutation_applied=mutation,
        reason=reason,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


def evaluate_mode_boundary(
    *,
    topology: MountedFieldTopology,
    state: ExactFieldState,
    bank: CertifiedModeBank,
    receipt_registry: ReceiptRegistry,
    growth_authority: ModeGrowthAuthority | None,
) -> RecognitionResult:
    """Evaluate all pre-growth modes, residual, decision, then eligible growth."""

    if not isinstance(topology, MountedFieldTopology):
        raise ReceiptError("recognition requires a mounted topology")
    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("recognition requires an immutable receipt registry")
    topology.verify(receipt_registry)
    if not topology.available:
        raise ReceiptError("recognition requires at least one mounted port")
    if not isinstance(state, ExactFieldState):
        raise ReceiptError(
            "mode authority requires exact executable field components; "
            "fixed CertifiedFieldState balls cannot be replayed as expressions"
        )
    state.verify(receipt_registry)
    if state.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
        raise ReceiptError("recognition state belongs to a different topology")
    if len(state.amplitudes) != topology.dimension:
        raise ReceiptError("recognition state dimension differs from topology")
    bank.verify(topology, recompute=True)
    if growth_authority is not None:
        if not isinstance(growth_authority, ModeGrowthAuthority):
            raise ReceiptError("growth authority has the wrong type")
        growth_authority.verify(
            topology=topology,
            state=state,
            receipt_registry=receipt_registry,
        )

    total_energy = _energy(state.amplitudes)
    if total_energy <= 0:
        raise ReceiptError("mode boundary requires positive exact field energy")
    residual_values = _orthogonal_residual(
        state.amplitudes,
        tuple(mode.projective_components for mode in bank.modes),
    )
    residual_energy = _energy(residual_values)
    activation_energies = tuple(
        _energy(((_inner(mode.projective_components, state.amplitudes)),))
        / mode.projective_norm_squared
        for mode in bank.modes
    )
    if sum(activation_energies, residual_energy) != total_energy:
        raise ReceiptError(
            "exact projection lost correlation: modal plus residual energy "
            "does not equal full field energy"
        )
    exact_probabilities = tuple(
        value / total_energy for value in activation_energies
    )
    perpendicular_probability = residual_energy / total_energy

    flint = load_pinned_flint()
    with flint.ctx.workprec(bank.working_precision_bits):
        mode_probabilities = tuple(
            ModeProbability(
                mode_index=index,
                mode_receipt_sha256=mode.receipt_sha256,
                exact_activation_energy=activation,
                certified_activation_energy=canonical_ball(
                    arb_fraction(flint, activation), bank.working_precision_bits
                ),
                exact_probability=probability,
                certified_probability=canonical_ball(
                    arb_fraction(flint, probability), bank.working_precision_bits
                ),
            )
            for index, (mode, activation, probability) in enumerate(
                zip(
                    bank.modes,
                    activation_energies,
                    exact_probabilities,
                    strict=True,
                )
            )
        )
        residual = _residual_receipt(
            flint=flint,
            residual=residual_values,
            energy=residual_energy,
            precision_bits=bank.working_precision_bits,
            state=state,
            bank=bank,
        )
        total_energy_ball = canonical_ball(
            arb_fraction(flint, total_energy), bank.working_precision_bits
        )
        entropy = _make_entropy_receipt(
            flint=flint,
            mode_probabilities=mode_probabilities,
            perpendicular_probability=perpendicular_probability,
            precision_bits=bank.working_precision_bits,
        )

    probability_bounds = tuple(
        _ball_bounds(value.certified_probability) for value in mode_probabilities
    )
    residual_bounds = _ball_bounds(entropy.certified_perpendicular_probability)
    stored_winners = tuple(
        index
        for index, (candidate_lower, _) in enumerate(probability_bounds)
        if candidate_lower > residual_bounds[1]
        and all(
            candidate_lower > other_upper
            for other_index, (_, other_upper) in enumerate(probability_bounds)
            if other_index != index
        )
    )
    residual_wins = residual_bounds[0] > max(
        (upper for _, upper in probability_bounds),
        default=Fraction(-1),
    )

    if bank.rank < 2 and residual_energy == 0:
        return _make_result(
            status=RecognitionStatus.AMBIGUOUS_SILENCE,
            winner=None,
            before=bank,
            after=bank,
            residual=residual,
            total_energy=total_energy,
            total_energy_ball=total_energy_ball,
            entropy=entropy,
            mutation=False,
            reason="bootstrap field is exactly dependent on the existing bank",
        )
    if bank.rank < 2:
        status = RecognitionStatus.BOOTSTRAP_SILENCE
        winner = None
        reason = "independent bootstrap experience remains silent"
        decision_allows_growth = residual_energy > 0
    elif len(stored_winners) == 1:
        status = RecognitionStatus.RECOGNIZED
        winner = stored_winners[0]
        reason = "one stored mode has certified unique full-vector dominance"
        decision_allows_growth = residual_energy > 0
    elif residual_wins:
        status = RecognitionStatus.NOVEL_SILENCE
        winner = None
        reason = "orthogonal field has certified unique full-vector dominance"
        decision_allows_growth = residual_energy > 0
    else:
        return _make_result(
            status=RecognitionStatus.AMBIGUOUS_SILENCE,
            winner=None,
            before=bank,
            after=bank,
            residual=residual,
            total_energy=total_energy,
            total_energy_ball=total_energy_ball,
            entropy=entropy,
            mutation=False,
            reason="full-vector Arb enclosures do not certify a unique chamber",
        )

    after = bank
    mutation = False
    if (
        decision_allows_growth
        and growth_authority is not None
        and bank.rank < bank.max_rank
    ):
        after = _append_mode(bank, _grow_mode(topology, bank, state))
        mutation = True
    elif growth_authority is None and decision_allows_growth:
        reason += "; no upstream closed-experience growth authority was supplied"
    elif bank.rank >= bank.max_rank:
        reason += "; bank already has full field rank N"

    return _make_result(
        status=status,
        winner=winner,
        before=bank,
        after=after,
        residual=residual,
        total_energy=total_energy,
        total_energy_ball=total_energy_ball,
        entropy=entropy,
        mutation=mutation,
        reason=reason,
    )


__all__ = (
    "CertifiedMode",
    "CertifiedModeBank",
    "CertifiedResidual",
    "ENTROPY_OPERATOR_ID",
    "EntropyVectorReceipt",
    "MODE_OPERATOR_ID",
    "ModeGrowthAuthority",
    "ModeProbability",
    "NORMALIZED_MODE_EXPRESSION",
    "RECOGNITION_OPERATOR_ID",
    "RecognitionResult",
    "RecognitionStatus",
    "create_empty_mode_bank",
    "evaluate_mode_boundary",
    "mode_growth_authority_receipt_payload",
    "reevaluate_mode_expression",
)
