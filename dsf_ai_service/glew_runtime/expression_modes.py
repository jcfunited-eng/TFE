"""Expression-backed full-field mode memory and unique-dominance boundary.

Modes retain the source closed-experience expression, not a rationalized vector
or a stored interval representative.  On every boundary evaluation all source
expressions and the present experience are reevaluated at one deterministic
shared Arb precision.  The ordered basis, modal activations, orthogonal
residual, and complete probability vector are formed in that same context.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Mapping, Sequence

from .certified_backend import (
    FLINT_VERSION,
    PYTHON_FLINT_VERSION,
    PYTHON_FLINT_WHEEL_SHA256,
    CertifiedBall,
    canonical_ball,
    load_pinned_flint,
)
from .expressions import (
    ClosedExperienceFieldExpression,
    HermitianExpressionEvaluator,
    PrecisionScheduleAuthority,
    evaluate_closed_experience_in_arb,
)
from .field import MountedFieldTopology
from .model import ReceiptError, ReceiptRegistry, receipt_sha256, sha256_digest


EXPRESSION_MODE_OPERATOR_ID = "reevaluated_shared_arb_gram_schmidt.v1"
EXPRESSION_RECOGNITION_OPERATOR_ID = "unique_full_interval_vector_dominance.v1"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


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


def _bounds(value: CertifiedBall) -> tuple[Fraction, Fraction]:
    return (
        Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent,
        Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent,
    )


def _certified_positive(value: CertifiedBall) -> bool:
    return _bounds(value)[0] > 0


def _certified_zero(value: CertifiedBall) -> bool:
    return _bounds(value) == (Fraction(0), Fraction(0))


def _energy(flint, values: Sequence[object]):
    result = flint.arb(0)
    for value in values:
        result += value.real * value.real + value.imag * value.imag
    return result


def _inner(flint, left: Sequence[object], right: Sequence[object]):
    if len(left) != len(right):
        raise ReceiptError("expression-mode inner-product dimensions differ")
    result = flint.acb(0)
    for left_value, right_value in zip(left, right, strict=True):
        result += left_value.conjugate() * right_value
    return result


def _orthogonal_residual(
    flint, source: Sequence[object], normalized_modes: Sequence[Sequence[object]]
) -> tuple[object, ...]:
    residual = tuple(source)
    for mode in normalized_modes:
        coefficient = _inner(flint, mode, residual)
        residual = tuple(
            value - component * coefficient
            for value, component in zip(residual, mode, strict=True)
        )
    return residual


def _certified_reciprocal_basis_activation_energies(
    flint,
    raw_sources: Sequence[Sequence[object]],
    present: Sequence[object],
    precision_bits: int,
) -> tuple[tuple[object, ...] | None, tuple[str, CertifiedBall] | None]:
    """Certify the exact raw-source Gram matrix is nonsingular and return each
    stored source's own reciprocal-basis activation energy against present.

    Projecting the present vector onto a sequentially Gram-Schmidt-
    orthonormalized basis is order-dependent: an earlier stored source's
    orthonormal mode absorbs whatever energy a later, structurally related
    source shares with it, so the later source can never uniquely dominate its
    own recognition.  The reciprocal (dual) basis removes that bias.  Let G be
    the exact Gram matrix of the raw (never orthogonalized) stored sources,
    G[i][j] = <source_i, source_j>, and b the vector of raw-source inner
    products against the present vector, b[i] = <source_i, present>.  The
    reciprocal coefficients c solve G @ c = b.  When present is exactly one
    stored source, c is exactly the standard basis vector naming that source
    alone -- independent of insertion order and independent of how much exact
    structure the stored sources share -- because b then equals the matching
    column of G exactly, and G^-1 times its own column is a unit vector.  Each
    source's activation energy is its coefficient's squared modulus scaled by
    its own exact self energy, which is exactly the existing orthonormal-basis
    projection energy in the degenerate case where the stored sources are
    already mutually orthogonal.
    """

    rank = len(raw_sources)
    if rank == 0:
        return (), None
    self_energies = tuple(_energy(flint, source) for source in raw_sources)
    rows: list[list[object]] = []
    for row in range(rank):
        entries: list[object] = []
        for column in range(rank):
            if column < row:
                entries.append(rows[column][row].conjugate())
            elif column == row:
                entries.append(flint.acb(self_energies[row]))
            else:
                entries.append(
                    _inner(flint, raw_sources[row], raw_sources[column])
                )
        rows.append(entries)
    gram = flint.acb_mat(rank, rank, [value for row in rows for value in row])
    determinant_ball = canonical_ball(gram.det().real, precision_bits)
    if not _certified_positive(determinant_ball):
        return None, (
            "stored source expressions do not certify a nonsingular exact "
            "reciprocal-basis Gram matrix",
            determinant_ball,
        )
    projections = flint.acb_mat(
        rank,
        1,
        [_inner(flint, source, present) for source in raw_sources],
    )
    try:
        coefficients = gram.solve(projections)
    except ZeroDivisionError:
        return None, (
            "certified nonsingular exact reciprocal-basis Gram matrix could "
            "not be solved",
            determinant_ball,
        )
    activations = tuple(
        (
            coefficients[index, 0].real * coefficients[index, 0].real
            + coefficients[index, 0].imag * coefficients[index, 0].imag
        )
        * self_energies[index]
        for index in range(rank)
    )
    return activations, None


def _mode_growth_proof_payload(
    *,
    mode_index: int,
    source_expression_receipt_sha256: str,
    pre_growth_bank_receipt_sha256: str,
    certified_residual_energy: CertifiedBall,
    working_precision_bits: int,
) -> bytes:
    return _canonical_bytes(
        {
            "certified_residual_energy": _ball_payload(certified_residual_energy),
            "growth_condition": "certified_residual_energy_lower_bound_strictly_positive",
            "mode_index": mode_index,
            "operator_id": EXPRESSION_MODE_OPERATOR_ID,
            "pre_growth_bank_receipt_sha256": pre_growth_bank_receipt_sha256,
            "schema": "glew.expression_mode.growth_proof.v1",
            "source_expression_receipt_sha256": source_expression_receipt_sha256,
            "working_precision_bits": working_precision_bits,
        }
    )


def _mode_payload(
    *,
    mode_index: int,
    source_expression_receipt_sha256: str,
    pre_growth_bank_receipt_sha256: str,
    growth_proof_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "growth_proof_receipt_sha256": growth_proof_receipt_sha256,
            "mode_index": mode_index,
            "normalization": "reevaluate_then_ordered_shared_arb_gram_schmidt",
            "operator_id": EXPRESSION_MODE_OPERATOR_ID,
            "pre_growth_bank_receipt_sha256": pre_growth_bank_receipt_sha256,
            "schema": "glew.expression_mode.source_expression.v1",
            "source_expression_receipt_sha256": source_expression_receipt_sha256,
            "stored_numeric_representative": None,
        }
    )


@dataclass(frozen=True, slots=True)
class ExpressionMode:
    mode_index: int
    source_expression: ClosedExperienceFieldExpression
    pre_growth_bank_receipt_sha256: str
    growth_proof_receipt_sha256: str
    growth_proof_receipt_payload: bytes
    receipt_sha256: str
    receipt_payload: bytes

    def verify(self, *, expected_index: int, receipt_registry: ReceiptRegistry) -> None:
        if self.mode_index != expected_index:
            raise ReceiptError("expression mode index differs from canonical bank order")
        sha256_digest(self.pre_growth_bank_receipt_sha256, "pre-growth bank receipt")
        self.source_expression.verify(receipt_registry)
        if (
            not self.growth_proof_receipt_payload
            or receipt_sha256(self.growth_proof_receipt_payload)
            != self.growth_proof_receipt_sha256
        ):
            raise ReceiptError("expression mode growth proof is not content-bound")
        proof = json.loads(self.growth_proof_receipt_payload)
        if (
            proof.get("mode_index") != self.mode_index
            or proof.get("source_expression_receipt_sha256")
            != self.source_expression.receipt_sha256
            or proof.get("pre_growth_bank_receipt_sha256")
            != self.pre_growth_bank_receipt_sha256
            or proof.get("growth_condition")
            != "certified_residual_energy_lower_bound_strictly_positive"
        ):
            raise ReceiptError("expression mode growth proof names different dependencies")
        try:
            encoded_energy = proof["certified_residual_energy"]
            certified_energy = CertifiedBall(
                lower_mantissa=encoded_energy["lower_mantissa"],
                lower_exponent=encoded_energy["lower_exponent"],
                upper_mantissa=encoded_energy["upper_mantissa"],
                upper_exponent=encoded_energy["upper_exponent"],
                working_precision_bits=encoded_energy["working_precision_bits"],
                python_flint_version=encoded_energy["python_flint_version"],
                flint_version=encoded_energy["flint_version"],
                wheel_sha256=encoded_energy["wheel_sha256"],
            )
        except (KeyError, TypeError) as exc:
            raise ReceiptError("expression mode growth proof energy is malformed") from exc
        if not _certified_positive(certified_energy):
            raise ReceiptError("stored expression mode lacks certified positive growth")
        expected_proof = _mode_growth_proof_payload(
            mode_index=self.mode_index,
            source_expression_receipt_sha256=self.source_expression.receipt_sha256,
            pre_growth_bank_receipt_sha256=self.pre_growth_bank_receipt_sha256,
            certified_residual_energy=certified_energy,
            working_precision_bits=proof.get("working_precision_bits"),
        )
        if expected_proof != self.growth_proof_receipt_payload:
            raise ReceiptError("expression mode growth proof is not canonical")
        expected = _mode_payload(
            mode_index=self.mode_index,
            source_expression_receipt_sha256=self.source_expression.receipt_sha256,
            pre_growth_bank_receipt_sha256=self.pre_growth_bank_receipt_sha256,
            growth_proof_receipt_sha256=self.growth_proof_receipt_sha256,
        )
        if self.receipt_payload != expected or receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("expression mode differs from canonical receipt")


def _bank_payload(
    *,
    topology_authority_receipt_sha256: str,
    dimension: int,
    precision_authority_receipt_sha256: str,
    modes: Sequence[ExpressionMode],
) -> bytes:
    return _canonical_bytes(
        {
            "dimension": dimension,
            "max_rank": dimension,
            "mode_receipt_sha256s": [value.receipt_sha256 for value in modes],
            "operator_id": EXPRESSION_MODE_OPERATOR_ID,
            "precision_authority_receipt_sha256": precision_authority_receipt_sha256,
            "rank": len(modes),
            "schema": "glew.expression_mode.bank.v1",
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class ExpressionModeBank:
    topology_authority_receipt_sha256: str
    dimension: int
    precision_authority: PrecisionScheduleAuthority
    modes: tuple[ExpressionMode, ...]
    receipt_sha256: str
    receipt_payload: bytes

    @property
    def rank(self) -> int:
        return len(self.modes)

    @property
    def max_rank(self) -> int:
        return self.dimension

    def verify(
        self, *, topology: MountedFieldTopology, receipt_registry: ReceiptRegistry
    ) -> None:
        topology.verify(receipt_registry)
        self.precision_authority.verify(receipt_registry)
        if self.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
            raise ReceiptError("expression mode bank belongs to a different topology")
        if self.dimension != topology.dimension or self.rank > self.dimension:
            raise ReceiptError("expression mode bank dimension or rank is invalid")
        expected_pre_growth = _bank_payload(
            topology_authority_receipt_sha256=self.topology_authority_receipt_sha256,
            dimension=self.dimension,
            precision_authority_receipt_sha256=(
                self.precision_authority.authority_receipt_sha256
            ),
            modes=(),
        )
        previous_digest = receipt_sha256(expected_pre_growth)
        for index, mode in enumerate(self.modes):
            mode.verify(expected_index=index, receipt_registry=receipt_registry)
            if mode.pre_growth_bank_receipt_sha256 != previous_digest:
                raise ReceiptError("expression mode does not name its exact pre-growth bank")
            if (
                mode.source_expression.topology_authority_receipt_sha256
                != self.topology_authority_receipt_sha256
                or mode.source_expression.precision_authority.authority_receipt_sha256
                != self.precision_authority.authority_receipt_sha256
            ):
                raise ReceiptError("stored expression mode carries different field authority")
            prefix = self.modes[: index + 1]
            prefix_payload = _bank_payload(
                topology_authority_receipt_sha256=self.topology_authority_receipt_sha256,
                dimension=self.dimension,
                precision_authority_receipt_sha256=(
                    self.precision_authority.authority_receipt_sha256
                ),
                modes=prefix,
            )
            previous_digest = receipt_sha256(prefix_payload)
        expected = _bank_payload(
            topology_authority_receipt_sha256=self.topology_authority_receipt_sha256,
            dimension=self.dimension,
            precision_authority_receipt_sha256=(
                self.precision_authority.authority_receipt_sha256
            ),
            modes=self.modes,
        )
        if self.receipt_payload != expected or receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("expression mode bank differs from canonical receipt")


@dataclass(frozen=True, slots=True)
class ReevaluatedExpressionModeEndpoint:
    """One live normalized Arb endpoint with stable mode identity."""

    mode_index: int
    mode_receipt_sha256: str
    source_expression_receipt_sha256: str
    normalized_amplitudes: tuple[object, ...]


def reevaluate_expression_mode_endpoints_in_arb(
    *,
    topology: MountedFieldTopology,
    bank: ExpressionModeBank,
    receipt_registry: ReceiptRegistry,
    flint,
    precision_bits: int,
    hermitian_evaluators: Mapping[str, HermitianExpressionEvaluator] | None = None,
    active_coordinates: Sequence[int] | None = None,
) -> tuple[ReevaluatedExpressionModeEndpoint, ...]:
    """Rebuild stable mode endpoints without a stored numeric representative.

    The full ordered basis is rebuilt first.  A current validity mask, when
    supplied by H_mem, is then applied and each endpoint is normalized again;
    the endpoint receipt remains the individual stable mode receipt.
    """

    bank.verify(topology=topology, receipt_registry=receipt_registry)
    if isinstance(precision_bits, bool) or not isinstance(precision_bits, int) or precision_bits <= 0:
        raise ReceiptError("expression endpoint precision must be positive")
    required = max(
        (mode.source_expression.initial_precision_bits for mode in bank.modes),
        default=1,
    )
    if precision_bits < required:
        raise ReceiptError("expression endpoint precision is below deterministic shared precision")
    if precision_bits > bank.precision_authority.maximum_precision_bits:
        raise ReceiptError("expression endpoint precision exceeds mounted maximum")
    if active_coordinates is None:
        active = tuple(range(bank.dimension))
    else:
        active = tuple(active_coordinates)
        if (
            not active
            or active != tuple(sorted(set(active)))
            or any(index < 0 or index >= bank.dimension for index in active)
        ):
            raise ReceiptError("expression endpoint validity coordinates are invalid")
    evaluators = {} if hermitian_evaluators is None else hermitian_evaluators
    normalized: list[tuple[object, ...]] = []
    for mode in bank.modes:
        source = evaluate_closed_experience_in_arb(
            mode.source_expression,
            flint=flint,
            precision_bits=precision_bits,
            hermitian_evaluators=evaluators,
        )
        residual = _orthogonal_residual(flint, source, normalized)
        energy = _energy(flint, residual)
        energy_ball = canonical_ball(energy, precision_bits)
        if not _certified_positive(energy_ball):
            raise ReceiptError("stored expression modes do not certify an independent endpoint basis")
        norm = energy.sqrt()
        normalized.append(tuple(value / norm for value in residual))

    endpoints: list[ReevaluatedExpressionModeEndpoint] = []
    active_set = set(active)
    for mode, full_endpoint in zip(bank.modes, normalized, strict=True):
        masked = tuple(
            value if index in active_set else flint.acb(0)
            for index, value in enumerate(full_endpoint)
        )
        masked_energy = _energy(flint, masked)
        masked_energy_ball = canonical_ball(masked_energy, precision_bits)
        if not _certified_positive(masked_energy_ball):
            raise ReceiptError("current validity mask cannot certify a nonzero expression endpoint")
        masked_norm = masked_energy.sqrt()
        endpoints.append(
            ReevaluatedExpressionModeEndpoint(
                mode_index=mode.mode_index,
                mode_receipt_sha256=mode.receipt_sha256,
                source_expression_receipt_sha256=(
                    mode.source_expression.receipt_sha256
                ),
                normalized_amplitudes=tuple(value / masked_norm for value in masked),
            )
        )
    return tuple(endpoints)


def _make_bank(
    *,
    topology: MountedFieldTopology,
    precision_authority: PrecisionScheduleAuthority,
    modes: Sequence[ExpressionMode],
) -> ExpressionModeBank:
    values = tuple(modes)
    payload = _bank_payload(
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        dimension=topology.dimension,
        precision_authority_receipt_sha256=precision_authority.authority_receipt_sha256,
        modes=values,
    )
    return ExpressionModeBank(
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        dimension=topology.dimension,
        precision_authority=precision_authority,
        modes=values,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


def create_empty_expression_mode_bank(
    *,
    topology: MountedFieldTopology,
    precision_authority: PrecisionScheduleAuthority,
    receipt_registry: ReceiptRegistry,
) -> ExpressionModeBank:
    topology.verify(receipt_registry)
    precision_authority.verify(receipt_registry)
    if not topology.available:
        raise ReceiptError("expression mode bank requires a mounted field")
    bank = _make_bank(
        topology=topology, precision_authority=precision_authority, modes=()
    )
    bank.verify(topology=topology, receipt_registry=receipt_registry)
    return bank


@dataclass(frozen=True, slots=True)
class ExpressionModeProbability:
    mode_index: int
    mode_receipt_sha256: str
    certified_activation_energy: CertifiedBall
    certified_probability: CertifiedBall


class ExpressionRecognitionStatus(str, Enum):
    BOOTSTRAP_SILENCE = "bootstrap_silence"
    RECOGNIZED = "recognized"
    NOVEL_SILENCE = "novel_silence"
    AMBIGUOUS_SILENCE = "ambiguous_silence"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExpressionModeBoundaryResult:
    status: ExpressionRecognitionStatus
    winner_mode_index: int | None
    input_expression_receipt_sha256: str
    pre_growth_bank: ExpressionModeBank
    post_growth_bank: ExpressionModeBank
    mode_probabilities: tuple[ExpressionModeProbability, ...]
    certified_residual_energy: CertifiedBall | None
    certified_residual_probability: CertifiedBall | None
    certified_total_energy: CertifiedBall | None
    working_precision_bits: int
    mutation: bool
    reason: str
    receipt_sha256: str
    receipt_payload: bytes

    def verify(self) -> None:
        expected = _result_payload(
            status=self.status,
            winner_mode_index=self.winner_mode_index,
            input_expression_receipt_sha256=self.input_expression_receipt_sha256,
            pre_growth_bank_receipt_sha256=self.pre_growth_bank.receipt_sha256,
            post_growth_bank_receipt_sha256=self.post_growth_bank.receipt_sha256,
            mode_probabilities=self.mode_probabilities,
            certified_residual_energy=self.certified_residual_energy,
            certified_residual_probability=self.certified_residual_probability,
            certified_total_energy=self.certified_total_energy,
            working_precision_bits=self.working_precision_bits,
            mutation=self.mutation,
            reason=self.reason,
        )
        if self.receipt_payload != expected or receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("expression-mode boundary result differs from receipt")
        if self.mutation != (
            self.pre_growth_bank.receipt_sha256
            != self.post_growth_bank.receipt_sha256
        ):
            raise ReceiptError("expression-mode mutation flag differs from bank state")


def _probability_payload(value: ExpressionModeProbability) -> dict[str, object]:
    return {
        "certified_activation_energy": _ball_payload(
            value.certified_activation_energy
        ),
        "certified_probability": _ball_payload(value.certified_probability),
        "mode_index": value.mode_index,
        "mode_receipt_sha256": value.mode_receipt_sha256,
    }


def _result_payload(
    *,
    status: ExpressionRecognitionStatus,
    winner_mode_index: int | None,
    input_expression_receipt_sha256: str,
    pre_growth_bank_receipt_sha256: str,
    post_growth_bank_receipt_sha256: str,
    mode_probabilities: Sequence[ExpressionModeProbability],
    certified_residual_energy: CertifiedBall | None,
    certified_residual_probability: CertifiedBall | None,
    certified_total_energy: CertifiedBall | None,
    working_precision_bits: int,
    mutation: bool,
    reason: str,
) -> bytes:
    return _canonical_bytes(
        {
            "backend": {
                "flint": FLINT_VERSION,
                "precision_bits": working_precision_bits,
                "python_flint": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            },
            "certified_residual_energy": (
                None
                if certified_residual_energy is None
                else _ball_payload(certified_residual_energy)
            ),
            "certified_residual_probability": (
                None
                if certified_residual_probability is None
                else _ball_payload(certified_residual_probability)
            ),
            "certified_total_energy": (
                None
                if certified_total_energy is None
                else _ball_payload(certified_total_energy)
            ),
            "decision_rule": "one_lower_bound_strictly_exceeds_every_other_upper_bound",
            "input_expression_receipt_sha256": input_expression_receipt_sha256,
            "mode_probabilities": [_probability_payload(value) for value in mode_probabilities],
            "mutation": mutation,
            "operator_id": EXPRESSION_RECOGNITION_OPERATOR_ID,
            "post_growth_bank_receipt_sha256": post_growth_bank_receipt_sha256,
            "pre_growth_bank_receipt_sha256": pre_growth_bank_receipt_sha256,
            "reason": reason,
            "schema": "glew.expression_mode.boundary_result.v1",
            "status": status.value,
            "winner_mode_index": winner_mode_index,
        }
    )


def _make_result(
    *,
    status: ExpressionRecognitionStatus,
    winner: int | None,
    input_expression: ClosedExperienceFieldExpression,
    before: ExpressionModeBank,
    after: ExpressionModeBank,
    probabilities: Sequence[ExpressionModeProbability],
    residual_energy: CertifiedBall | None,
    residual_probability: CertifiedBall | None,
    total_energy: CertifiedBall | None,
    precision_bits: int,
    reason: str,
) -> ExpressionModeBoundaryResult:
    mutation = before.receipt_sha256 != after.receipt_sha256
    payload = _result_payload(
        status=status,
        winner_mode_index=winner,
        input_expression_receipt_sha256=input_expression.receipt_sha256,
        pre_growth_bank_receipt_sha256=before.receipt_sha256,
        post_growth_bank_receipt_sha256=after.receipt_sha256,
        mode_probabilities=probabilities,
        certified_residual_energy=residual_energy,
        certified_residual_probability=residual_probability,
        certified_total_energy=total_energy,
        working_precision_bits=precision_bits,
        mutation=mutation,
        reason=reason,
    )
    result = ExpressionModeBoundaryResult(
        status=status,
        winner_mode_index=winner,
        input_expression_receipt_sha256=input_expression.receipt_sha256,
        pre_growth_bank=before,
        post_growth_bank=after,
        mode_probabilities=tuple(probabilities),
        certified_residual_energy=residual_energy,
        certified_residual_probability=residual_probability,
        certified_total_energy=total_energy,
        working_precision_bits=precision_bits,
        mutation=mutation,
        reason=reason,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    result.verify()
    return result


def _append_expression_mode(
    *,
    topology: MountedFieldTopology,
    bank: ExpressionModeBank,
    source_expression: ClosedExperienceFieldExpression,
    certified_residual_energy: CertifiedBall,
    precision_bits: int,
) -> ExpressionModeBank:
    if not _certified_positive(certified_residual_energy):
        raise ReceiptError("expression mode growth lacks certified positive residual")
    proof_payload = _mode_growth_proof_payload(
        mode_index=bank.rank,
        source_expression_receipt_sha256=source_expression.receipt_sha256,
        pre_growth_bank_receipt_sha256=bank.receipt_sha256,
        certified_residual_energy=certified_residual_energy,
        working_precision_bits=precision_bits,
    )
    proof_digest = receipt_sha256(proof_payload)
    mode_payload = _mode_payload(
        mode_index=bank.rank,
        source_expression_receipt_sha256=source_expression.receipt_sha256,
        pre_growth_bank_receipt_sha256=bank.receipt_sha256,
        growth_proof_receipt_sha256=proof_digest,
    )
    mode = ExpressionMode(
        mode_index=bank.rank,
        source_expression=source_expression,
        pre_growth_bank_receipt_sha256=bank.receipt_sha256,
        growth_proof_receipt_sha256=proof_digest,
        growth_proof_receipt_payload=proof_payload,
        receipt_sha256=receipt_sha256(mode_payload),
        receipt_payload=mode_payload,
    )
    return _make_bank(
        topology=topology,
        precision_authority=bank.precision_authority,
        modes=(*bank.modes, mode),
    )


def evaluate_expression_mode_boundary(
    *,
    topology: MountedFieldTopology,
    bank: ExpressionModeBank,
    input_expression: ClosedExperienceFieldExpression,
    receipt_registry: ReceiptRegistry,
    hermitian_evaluators: Mapping[str, HermitianExpressionEvaluator] | None = None,
) -> ExpressionModeBoundaryResult:
    """Reevaluate the full bank with exact correlation and certified refinement.

    Every attempt reevaluates every stored source expression and the present
    expression at one shared Arb precision.  An indeterminate enclosure is
    retried only by exact doubling under the mounted precision authority.  No
    tolerance, midpoint, threshold, or carried numeric representative obtains
    decision authority.

    When the present expression receipt is exactly one stored source-expression
    receipt, both name the same immutable DAG.  Its residual against the
    complete basis that contains it is algebraically zero.  That correlation is
    retained as exact zero instead of subtracting two interval evaluations of
    the same DAG and thereby inventing enclosure width.
    """

    bank.verify(topology=topology, receipt_registry=receipt_registry)
    input_expression.verify(receipt_registry)
    if (
        input_expression.topology_authority_receipt_sha256
        != topology.authority_receipt_sha256
        or input_expression.precision_authority.authority_receipt_sha256
        != bank.precision_authority.authority_receipt_sha256
    ):
        raise ReceiptError("input expression carries different mode-bank authority")

    expressions = tuple(mode.source_expression for mode in bank.modes) + (
        input_expression,
    )
    proof_precisions = tuple(
        json.loads(mode.growth_proof_receipt_payload)["working_precision_bits"]
        for mode in bank.modes
    )
    precision_candidates = tuple(
        value.initial_precision_bits for value in expressions
    ) + proof_precisions
    precision_bits = max(precision_candidates)
    maximum_precision_bits = bank.precision_authority.maximum_precision_bits
    if precision_bits > maximum_precision_bits:
        return _make_result(
            status=ExpressionRecognitionStatus.UNKNOWN,
            winner=None,
            input_expression=input_expression,
            before=bank,
            after=bank,
            probabilities=(),
            residual_energy=None,
            residual_probability=None,
            total_energy=None,
            precision_bits=precision_bits,
            reason="deterministic shared precision exceeds mounted maximum",
        )

    matching_mode_index = next(
        (
            mode.mode_index
            for mode in bank.modes
            if mode.source_expression.receipt_sha256
            == input_expression.receipt_sha256
        ),
        None,
    )
    evaluators = {} if hermitian_evaluators is None else hermitian_evaluators
    flint = load_pinned_flint()

    while True:
        basis_failure: tuple[str, CertifiedBall] | None = None
        probabilities: tuple[ExpressionModeProbability, ...] = ()
        total_energy_ball: CertifiedBall | None = None
        residual_energy_ball: CertifiedBall | None = None
        residual_probability_ball: CertifiedBall | None = None
        winners: tuple[int, ...] = ()

        with flint.ctx.workprec(precision_bits):
            expression_memo: dict[str, tuple[object, ...]] = {}

            def field(
                expression: ClosedExperienceFieldExpression,
            ) -> tuple[object, ...]:
                if expression.receipt_sha256 not in expression_memo:
                    expression_memo[expression.receipt_sha256] = (
                        evaluate_closed_experience_in_arb(
                            expression,
                            flint=flint,
                            precision_bits=precision_bits,
                            hermitian_evaluators=evaluators,
                        )
                    )
                return expression_memo[expression.receipt_sha256]

            normalized_modes: list[tuple[object, ...]] = []
            raw_sources: list[tuple[object, ...]] = []
            for mode in bank.modes:
                source = field(mode.source_expression)
                raw_sources.append(source)
                residual = _orthogonal_residual(
                    flint,
                    source,
                    normalized_modes,
                )
                residual_energy_value = _energy(flint, residual)
                certified = canonical_ball(
                    residual_energy_value,
                    precision_bits,
                )
                if not _certified_positive(certified):
                    basis_failure = (
                        "stored source expressions do not certify an "
                        "independent basis at shared precision",
                        certified,
                    )
                    break
                norm = residual_energy_value.sqrt()
                normalized_modes.append(
                    tuple(value / norm for value in residual)
                )

            if basis_failure is None:
                present = field(input_expression)
                total_energy_value = _energy(flint, present)
                total_energy_ball = canonical_ball(
                    total_energy_value,
                    precision_bits,
                )
                if not _certified_positive(total_energy_ball):
                    basis_failure = (
                        "present full-field energy is not certified positive",
                        total_energy_ball,
                    )
                else:
                    activation_values, gram_failure = (
                        _certified_reciprocal_basis_activation_energies(
                            flint,
                            raw_sources,
                            present,
                            precision_bits,
                        )
                    )
                    if gram_failure is not None:
                        basis_failure = gram_failure
                    else:
                        if matching_mode_index is None:
                            present_residual = _orthogonal_residual(
                                flint,
                                present,
                                normalized_modes,
                            )
                            residual_energy_value = _energy(
                                flint,
                                present_residual,
                            )
                        else:
                            residual_energy_value = flint.arb(0)
                        residual_energy_ball = canonical_ball(
                            residual_energy_value,
                            precision_bits,
                        )
                        residual_probability_ball = canonical_ball(
                            residual_energy_value / total_energy_value,
                            precision_bits,
                        )
                        probabilities = tuple(
                            ExpressionModeProbability(
                                mode_index=index,
                                mode_receipt_sha256=mode.receipt_sha256,
                                certified_activation_energy=canonical_ball(
                                    activation,
                                    precision_bits,
                                ),
                                certified_probability=canonical_ball(
                                    activation / total_energy_value,
                                    precision_bits,
                                ),
                            )
                            for index, (mode, activation) in enumerate(
                                zip(
                                    bank.modes,
                                    activation_values,
                                    strict=True,
                                )
                            )
                        )
                        if bank.rank >= 2:
                            probability_bounds = tuple(
                                _bounds(value.certified_probability)
                                for value in probabilities
                            )
                            residual_bounds = _bounds(
                                residual_probability_ball
                            )
                            all_bounds = (
                                *probability_bounds,
                                residual_bounds,
                            )
                            winners = tuple(
                                index
                                for index, (lower, _) in enumerate(all_bounds)
                                if all(
                                    lower > other_upper
                                    for other_index, (
                                        _,
                                        other_upper,
                                    ) in enumerate(all_bounds)
                                    if other_index != index
                                )
                            )

        if basis_failure is None:
            if (
                bank.rank < 2
                and residual_energy_ball is not None
                and _certified_positive(residual_energy_ball)
                and bank.rank < bank.max_rank
            ):
                after = _append_expression_mode(
                    topology=topology,
                    bank=bank,
                    source_expression=input_expression,
                    certified_residual_energy=residual_energy_ball,
                    precision_bits=precision_bits,
                )
                return _make_result(
                    status=ExpressionRecognitionStatus.BOOTSTRAP_SILENCE,
                    winner=None,
                    input_expression=input_expression,
                    before=bank,
                    after=after,
                    probabilities=probabilities,
                    residual_energy=residual_energy_ball,
                    residual_probability=residual_probability_ball,
                    total_energy=total_energy_ball,
                    precision_bits=precision_bits,
                    reason=(
                        "independent closed experience stored; two-mode "
                        "bootstrap remains silent"
                    ),
                )
            if (
                bank.rank < 2
                and residual_energy_ball is not None
                and _certified_zero(residual_energy_ball)
            ):
                return _make_result(
                    status=ExpressionRecognitionStatus.BOOTSTRAP_SILENCE,
                    winner=None,
                    input_expression=input_expression,
                    before=bank,
                    after=bank,
                    probabilities=probabilities,
                    residual_energy=residual_energy_ball,
                    residual_probability=residual_probability_ball,
                    total_energy=total_energy_ball,
                    precision_bits=precision_bits,
                    reason=(
                        "bootstrap experience is the exact stored expression "
                        "DAG; correlated residual is zero"
                    ),
                )
            if bank.rank >= 2 and len(winners) == 1:
                unique = winners[0]
                after = bank
                if (
                    residual_energy_ball is not None
                    and _certified_positive(residual_energy_ball)
                    and bank.rank < bank.max_rank
                ):
                    after = _append_expression_mode(
                        topology=topology,
                        bank=bank,
                        source_expression=input_expression,
                        certified_residual_energy=residual_energy_ball,
                        precision_bits=precision_bits,
                    )
                if unique < bank.rank:
                    return _make_result(
                        status=ExpressionRecognitionStatus.RECOGNIZED,
                        winner=unique,
                        input_expression=input_expression,
                        before=bank,
                        after=after,
                        probabilities=probabilities,
                        residual_energy=residual_energy_ball,
                        residual_probability=residual_probability_ball,
                        total_energy=total_energy_ball,
                        precision_bits=precision_bits,
                        reason=(
                            "one stored expression mode uniquely dominates "
                            "the complete interval vector"
                        ),
                    )
                return _make_result(
                    status=ExpressionRecognitionStatus.NOVEL_SILENCE,
                    winner=None,
                    input_expression=input_expression,
                    before=bank,
                    after=after,
                    probabilities=probabilities,
                    residual_energy=residual_energy_ball,
                    residual_probability=residual_probability_ball,
                    total_energy=total_energy_ball,
                    precision_bits=precision_bits,
                    reason=(
                        "orthogonal residual uniquely dominates; novel "
                        "experience remains silent"
                    ),
                )

        next_precision = precision_bits * 2
        if next_precision <= maximum_precision_bits:
            precision_bits = next_precision
            continue

        if basis_failure is not None:
            failure_reason, failed_ball = basis_failure
            return _make_result(
                status=ExpressionRecognitionStatus.UNKNOWN,
                winner=None,
                input_expression=input_expression,
                before=bank,
                after=bank,
                probabilities=(),
                residual_energy=failed_ball,
                residual_probability=None,
                total_energy=total_energy_ball,
                precision_bits=precision_bits,
                reason=(
                    f"{failure_reason}; mounted precision maximum exhausted"
                ),
            )
        if bank.rank < 2:
            return _make_result(
                status=ExpressionRecognitionStatus.UNKNOWN,
                winner=None,
                input_expression=input_expression,
                before=bank,
                after=bank,
                probabilities=probabilities,
                residual_energy=residual_energy_ball,
                residual_probability=residual_probability_ball,
                total_energy=total_energy_ball,
                precision_bits=precision_bits,
                reason=(
                    "bootstrap residual remains neither certified positive "
                    "nor exact zero after mounted precision exhaustion"
                ),
            )
        return _make_result(
            status=ExpressionRecognitionStatus.AMBIGUOUS_SILENCE,
            winner=None,
            input_expression=input_expression,
            before=bank,
            after=bank,
            probabilities=probabilities,
            residual_energy=residual_energy_ball,
            residual_probability=residual_probability_ball,
            total_energy=total_energy_ball,
            precision_bits=precision_bits,
            reason=(
                "full interval probability vector has no unique dominance "
                "chamber after mounted precision exhaustion"
            ),
        )


__all__ = (
    "EXPRESSION_MODE_OPERATOR_ID",
    "EXPRESSION_RECOGNITION_OPERATOR_ID",
    "ExpressionMode",
    "ExpressionModeBank",
    "ExpressionModeBoundaryResult",
    "ExpressionModeProbability",
    "ExpressionRecognitionStatus",
    "ReevaluatedExpressionModeEndpoint",
    "create_empty_expression_mode_bank",
    "evaluate_expression_mode_boundary",
    "reevaluate_expression_mode_endpoints_in_arb",
)


