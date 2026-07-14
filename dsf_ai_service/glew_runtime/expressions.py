"""Reevaluatable full-field expressions for one closed GLEW experience.

The authority retained here is an expression DAG, never an interval snapshot.
It binds the exact initial field, every exact MapInject event, every exact
piecewise evolution authority, and any separately mounted Hermitian expression
leaf.  Evaluation starts again from those same leaves at pinned Arb precision.

One closed experience is the equal-weight centroid of *all* post-gate field
states.  The post-gate nodes share their preceding state nodes in the DAG; no
state is boxed and reintroduced between gates.  Hermitian leaves expose only
their canonical upper-triangle expression.  The evaluator constructs the
conjugate half from the same objects, so independently boxed matrix entries can
never become Hamiltonian authority through this boundary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Mapping, Protocol, Sequence

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
    FieldInjection,
    FieldEvolutionAuthority,
    MapInjection,
    MountedFieldTopology,
    SparseMapInjection,
    injection_exact_input_fractions,
)
from .model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_identifier,
    sha256_digest,
)


PRECISION_SCHEDULE_ID = "exact_input_span_power_of_two_then_explicit_doubling.v1"
CENTROID_OPERATOR_ID = "equal_weight_sum_of_every_post_gate_state.v1"
FIELD_EXPRESSION_SOLVER_ID = "shared_dag_augmented_acb_matrix_exponential.v1"
FIELD_EVALUATION_IDENTITY_ID = "closed_experience_field_evaluation_leaves.v1"


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


def _complex_payload(value: ExactComplex) -> dict[str, str]:
    return {"imag": _fraction_text(value.imag), "real": _fraction_text(value.real)}


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


def _exact_bit_length(value: Fraction) -> int:
    """Canonical binary information span of one exact rational input."""

    return max(1, abs(value.numerator).bit_length()) + value.denominator.bit_length()


def _next_power_of_two(value: int) -> int:
    if value <= 1:
        return 1
    return 1 << (value - 1).bit_length()


def precision_schedule_authority_receipt_payload(
    *, authority_id: str, maximum_precision_bits: int
) -> bytes:
    require_identifier(authority_id, "precision authority id")
    if (
        isinstance(maximum_precision_bits, bool)
        or not isinstance(maximum_precision_bits, int)
        or maximum_precision_bits <= 0
    ):
        raise ReceiptError("mounted maximum precision must be a positive integer")
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "backend": {
                "flint": FLINT_VERSION,
                "python_flint": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            },
            "initial_precision_formula": (
                "next_power_of_two(max_exact_rational_bit_length"
                "+bit_length(exact_input_count)+bit_length(field_dimension)"
                "+bit_length(post_gate_count))"
            ),
            "maximum_precision_bits": maximum_precision_bits,
            "refinement_rule": "double_only_after_mounted_indeterminate_proof_request",
            "schedule_id": PRECISION_SCHEDULE_ID,
            "schema": "glew.expression.precision_schedule_authority.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class PrecisionScheduleAuthority:
    authority_id: str
    maximum_precision_bits: int
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.authority_id, "precision authority id")
        if (
            isinstance(self.maximum_precision_bits, bool)
            or not isinstance(self.maximum_precision_bits, int)
            or self.maximum_precision_bits <= 0
        ):
            raise ReceiptError("mounted maximum precision must be a positive integer")
        sha256_digest(self.authority_receipt_sha256, "precision authority receipt")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "precision authority receipt"
        )
        expected = precision_schedule_authority_receipt_payload(
            authority_id=self.authority_id,
            maximum_precision_bits=self.maximum_precision_bits,
        )
        if mounted != expected:
            raise ReceiptError("precision schedule differs from its mounted authority")


def hermitian_leaf_reference_receipt_payload(
    *,
    leaf_id: str,
    dimension: int,
    provider_expression_receipt_sha256: str,
    dependency_receipt_sha256s: Sequence[str],
    exact_input_bit_lengths: Sequence[int],
    upper_nonzero_positions: Sequence[tuple[int, int]],
) -> bytes:
    require_identifier(leaf_id, "Hermitian leaf id")
    sha256_digest(
        provider_expression_receipt_sha256, "Hermitian provider expression receipt"
    )
    return _canonical_bytes(
        {
            "dependency_receipt_sha256s": list(dependency_receipt_sha256s),
            "dimension": dimension,
            "exact_input_bit_lengths": list(exact_input_bit_lengths),
            "hermitian_construction": (
                "provider_upper_triangle_then_same_object_exact_conjugate_assignment"
            ),
            "leaf_id": leaf_id,
            "provider_expression_receipt_sha256": (
                provider_expression_receipt_sha256
            ),
            "schema": "glew.expression.hermitian_leaf_reference.v1",
            "upper_nonzero_positions": [
                [row, column] for row, column in upper_nonzero_positions
            ],
        }
    )


@dataclass(frozen=True, slots=True)
class HermitianExpressionLeafReference:
    """Receipt-bound reference to a reevaluable correlated H expression."""

    leaf_id: str
    dimension: int
    provider_expression_receipt_sha256: str
    dependency_receipt_sha256s: tuple[str, ...]
    exact_input_bit_lengths: tuple[int, ...]
    upper_nonzero_positions: tuple[tuple[int, int], ...]
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        require_identifier(self.leaf_id, "Hermitian leaf id")
        if isinstance(self.dimension, bool) or not isinstance(self.dimension, int) or self.dimension <= 0:
            raise ReceiptError("Hermitian expression leaf dimension must be positive")
        sha256_digest(
            self.provider_expression_receipt_sha256,
            "Hermitian provider expression receipt",
        )
        sha256_digest(self.receipt_sha256, "Hermitian leaf reference receipt")
        if self.dependency_receipt_sha256s != tuple(
            sorted(set(self.dependency_receipt_sha256s))
        ):
            raise ReceiptError("Hermitian dependencies must be unique canonical digest order")
        for digest in self.dependency_receipt_sha256s:
            sha256_digest(digest, "Hermitian dependency receipt")
        if not self.exact_input_bit_lengths or any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in self.exact_input_bit_lengths
        ):
            raise ReceiptError("Hermitian leaf requires positive exact input bit lengths")
        if self.upper_nonzero_positions != tuple(sorted(set(self.upper_nonzero_positions))):
            raise ReceiptError("Hermitian upper positions must be unique canonical order")
        for row, column in self.upper_nonzero_positions:
            if row < 0 or column < row or column >= self.dimension:
                raise ReceiptError("Hermitian leaf position is not in the canonical upper triangle")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.provider_expression_receipt_sha256,
            "Hermitian provider expression receipt",
        )
        for digest in self.dependency_receipt_sha256s:
            receipt_registry.resolve(digest, "Hermitian dependency receipt")
        expected = hermitian_leaf_reference_receipt_payload(
            leaf_id=self.leaf_id,
            dimension=self.dimension,
            provider_expression_receipt_sha256=(
                self.provider_expression_receipt_sha256
            ),
            dependency_receipt_sha256s=self.dependency_receipt_sha256s,
            exact_input_bit_lengths=self.exact_input_bit_lengths,
            upper_nonzero_positions=self.upper_nonzero_positions,
        )
        if self.receipt_payload != expected or receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("Hermitian leaf reference differs from canonical receipt")
        mounted = receipt_registry.resolve(
            self.receipt_sha256, "Hermitian leaf reference receipt"
        )
        if mounted != expected:
            raise ReceiptError("Hermitian leaf reference differs from mounted bytes")


def create_hermitian_leaf_reference(
    *,
    leaf_id: str,
    dimension: int,
    provider_expression_receipt_sha256: str,
    dependency_receipt_sha256s: Sequence[str],
    exact_input_bit_lengths: Sequence[int],
    upper_nonzero_positions: Sequence[tuple[int, int]],
) -> HermitianExpressionLeafReference:
    dependencies = tuple(sorted(dependency_receipt_sha256s))
    positions = tuple(sorted(upper_nonzero_positions))
    bit_lengths = tuple(exact_input_bit_lengths)
    payload = hermitian_leaf_reference_receipt_payload(
        leaf_id=leaf_id,
        dimension=dimension,
        provider_expression_receipt_sha256=provider_expression_receipt_sha256,
        dependency_receipt_sha256s=dependencies,
        exact_input_bit_lengths=bit_lengths,
        upper_nonzero_positions=positions,
    )
    return HermitianExpressionLeafReference(
        leaf_id=leaf_id,
        dimension=dimension,
        provider_expression_receipt_sha256=provider_expression_receipt_sha256,
        dependency_receipt_sha256s=dependencies,
        exact_input_bit_lengths=bit_lengths,
        upper_nonzero_positions=positions,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


@dataclass(frozen=True, slots=True)
class EvaluatedHermitianUpperEntry:
    row: int
    column: int
    value: object


class HermitianExpressionEvaluator(Protocol):
    """Runtime evaluator for a mounted expression, such as correlated H_mem."""

    provider_expression_receipt_sha256: str
    dimension: int

    def evaluate_upper(
        self, *, flint: object, working_precision_bits: int
    ) -> Sequence[EvaluatedHermitianUpperEntry]: ...


@dataclass(frozen=True, slots=True)
class FieldExpressionStep:
    injection: FieldInjection
    authority: FieldEvolutionAuthority
    hermitian_leaves: tuple[HermitianExpressionLeafReference, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.injection, (MapInjection, SparseMapInjection)):
            raise ReceiptError(
                "field expression step requires a typed dense or sparse MapInject event"
            )
        if not isinstance(self.authority, FieldEvolutionAuthority):
            raise ReceiptError("field expression step requires exact evolution authority")
        if not all(
            isinstance(value, HermitianExpressionLeafReference)
            for value in self.hermitian_leaves
        ):
            raise ReceiptError("field expression step contains an invalid Hermitian leaf")
        digests = tuple(value.receipt_sha256 for value in self.hermitian_leaves)
        if digests != tuple(sorted(set(digests))):
            raise ReceiptError("Hermitian leaves must be unique canonical receipt order")


def _exact_upper_terms(
    authority: FieldEvolutionAuthority,
) -> tuple[tuple[int, int, ExactComplex], ...]:
    values = {(value.row, value.column): value.value for value in authority.hamiltonian}
    upper: list[tuple[int, int, ExactComplex]] = []
    for (row, column), value in values.items():
        if row > column:
            continue
        if row == column and value.imag != 0:
            raise ReceiptError("Hermitian diagonal authority must be exactly real")
        if row != column and values.get((column, row)) != value.conjugate():
            raise ReceiptError("Hamiltonian pair is not one structural conjugate expression")
        upper.append((row, column, value))
    return tuple(sorted(upper, key=lambda item: (item[0], item[1])))


def _combined_partition(
    dimension: int,
    exact_upper: Sequence[tuple[int, int, ExactComplex]],
    leaves: Sequence[HermitianExpressionLeafReference],
) -> tuple[tuple[int, ...], ...]:
    neighbors = [set() for _ in range(dimension)]
    positions = tuple((row, column) for row, column, _ in exact_upper) + tuple(
        position for leaf in leaves for position in leaf.upper_nonzero_positions
    )
    for row, column in positions:
        if row != column:
            neighbors[row].add(column)
            neighbors[column].add(row)
    unvisited = set(range(dimension))
    components: list[tuple[int, ...]] = []
    while unvisited:
        start = min(unvisited)
        pending = [start]
        component: set[int] = set()
        while pending:
            index = pending.pop()
            if index in component:
                continue
            component.add(index)
            pending.extend(sorted(neighbors[index] - component, reverse=True))
        unvisited -= component
        components.append(tuple(sorted(component)))
    return tuple(components)


def _expression_dag_payload(
    *,
    topology: MountedFieldTopology,
    initial_state: ExactFieldState,
    steps: Sequence[FieldExpressionStep],
    precision_authority: PrecisionScheduleAuthority,
) -> tuple[bytes, tuple[str, ...], tuple[int, ...]]:
    nodes: list[dict[str, object]] = []
    initial_node = _canonical_bytes(
        {
            "exact_state_authority_receipt_sha256": initial_state.authority_receipt_sha256,
            "kind": "exact_initial_state",
            "source_time": _fraction_text(initial_state.source_time),
            "topology_authority_receipt_sha256": topology.authority_receipt_sha256,
        }
    )
    previous_node_id = receipt_sha256(initial_node)
    nodes.append({"node_id": previous_node_id, "node": json.loads(initial_node)})
    post_gate_node_ids: list[str] = []
    for index, step in enumerate(steps):
        exact_upper = _exact_upper_terms(step.authority)
        components = _combined_partition(topology.dimension, exact_upper, step.hermitian_leaves)
        node = {
            "combined_component_partition": [list(value) for value in components],
            "exact_hermitian_upper": [
                {"column": column, "row": row, "value": _complex_payload(value)}
                for row, column, value in exact_upper
            ],
            "evolution_authority_receipt_sha256": step.authority.authority_receipt_sha256,
            "gate_index": index,
            "hermitian_leaf_reference_receipt_sha256s": [
                value.receipt_sha256 for value in step.hermitian_leaves
            ],
            "hermitian_rule": "upper_expression_plus_same_object_exact_conjugate",
            "kind": "post_gate_evolution_state",
            "map_injection_receipt_sha256": step.injection.receipt_sha256,
            "previous_state_node_id": previous_node_id,
            "source_time_end": _fraction_text(step.authority.source_time_end),
            "source_time_start": _fraction_text(step.authority.source_time_start),
        }
        node_payload = _canonical_bytes(node)
        previous_node_id = receipt_sha256(node_payload)
        post_gate_node_ids.append(previous_node_id)
        nodes.append({"node_id": previous_node_id, "node": node})
    centroid_node = {
        "divisor": len(post_gate_node_ids),
        "input_state_node_ids": post_gate_node_ids,
        "kind": "closed_experience_centroid",
        "operator_id": CENTROID_OPERATOR_ID,
    }
    centroid_node_payload = _canonical_bytes(centroid_node)
    centroid_node_id = receipt_sha256(centroid_node_payload)
    nodes.append({"node_id": centroid_node_id, "node": centroid_node})
    exact_bits = _collect_exact_input_bit_lengths(initial_state, steps)
    payload = _canonical_bytes(
        {
            "centroid_node_id": centroid_node_id,
            "dag_nodes": nodes,
            "exact_input_bit_lengths": list(exact_bits),
            "field_dimension": topology.dimension,
            "fiber_dimension": FIBER_DIMENSION,
            "post_gate_state_node_ids": post_gate_node_ids,
            "precision_authority_receipt_sha256": (
                precision_authority.authority_receipt_sha256
            ),
            "schema": "glew.expression.closed_experience_field.v1",
            "topology_authority_receipt_sha256": topology.authority_receipt_sha256,
        }
    )
    return payload, tuple(post_gate_node_ids), exact_bits


def _collect_exact_input_bit_lengths(
    initial_state: ExactFieldState, steps: Sequence[FieldExpressionStep]
) -> tuple[int, ...]:
    fractions: list[Fraction] = [initial_state.source_time]
    for value in initial_state.amplitudes:
        fractions.extend((value.real, value.imag))
    declared: list[int] = []
    for step in steps:
        fractions.extend(injection_exact_input_fractions(step.injection))
        authority = step.authority
        fractions.extend(
            (
                authority.source_time_start,
                authority.source_time_end,
                authority.hbar,
            )
        )
        for value in authority.hamiltonian:
            fractions.extend((value.value.real, value.value.imag))
        for value in authority.local_rates:
            fractions.extend((value.growth, value.decay))
        for value in authority.source:
            fractions.extend((value.value.real, value.value.imag))
        for leaf in step.hermitian_leaves:
            declared.extend(leaf.exact_input_bit_lengths)
    return tuple((*(_exact_bit_length(value) for value in fractions), *declared))


def field_evaluation_identity_payload(
    *,
    topology_authority_receipt_sha256: str,
    dimension: int,
    initial_state: ExactFieldState,
    steps: Sequence[FieldExpressionStep],
) -> bytes:
    """Canonical bytes over EXACTLY the exact leaves that
    ``evaluate_closed_experience_in_arb`` reads, and nothing else.

    Two closed-experience expressions with equal payloads here evaluate to the
    identical mathematical field at every shared Arb precision, because the
    evaluator is a deterministic function of precisely these leaves: the exact
    initial amplitudes, and per gate (in order) the exact Hermitian upper
    terms, the identities of any mounted Hermitian expression leaves, the exact
    local growth/decay rates, the exact affine source coefficients, the exact
    source-time delta, and hbar.  It deliberately omits every receipt that is
    pure bookkeeping for the numeric field: the MapInject/injection receipts
    (their integrated charge already appears as the exact ``source``
    coefficients), the evolution-authority receipt, the physical-profile
    receipt, the initial-state authority receipt, the absolute source-time
    endpoints, the authority id, and the source-time unit -- none of which the
    evaluator ever consults.  This is the field-content sibling of
    ``receipt_sha256``: same content-addressing discipline, with the
    request/scene bookkeeping (which the owner ruled has no physical authority)
    excluded so that two truly-identical physical experiences share one
    identity regardless of the distinct moments that named them.
    """

    return _canonical_bytes(
        {
            "dimension": dimension,
            "initial_amplitudes": [
                _complex_payload(value) for value in initial_state.amplitudes
            ],
            "operator_id": FIELD_EVALUATION_IDENTITY_ID,
            "schema": "glew.expression.field_evaluation_identity.v1",
            "steps": [
                {
                    "delta": _fraction_text(step.authority.delta),
                    "hamiltonian_upper": [
                        {
                            "column": column,
                            "row": row,
                            "value": _complex_payload(value),
                        }
                        for row, column, value in _exact_upper_terms(step.authority)
                    ],
                    "hbar": _fraction_text(step.authority.hbar),
                    "hermitian_leaves": [
                        {
                            "dimension": leaf.dimension,
                            "provider_expression_receipt_sha256": (
                                leaf.provider_expression_receipt_sha256
                            ),
                            "upper_nonzero_positions": [
                                [row, column]
                                for row, column in leaf.upper_nonzero_positions
                            ],
                        }
                        for leaf in step.hermitian_leaves
                    ],
                    "local_rates": [
                        {
                            "decay": _fraction_text(rate.decay),
                            "growth": _fraction_text(rate.growth),
                            "index": rate.index,
                        }
                        for rate in step.authority.local_rates
                    ],
                    "source": [
                        {
                            "index": coefficient.index,
                            "value": _complex_payload(coefficient.value),
                        }
                        for coefficient in step.authority.source
                    ],
                }
                for step in steps
            ],
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class ClosedExperienceFieldExpression:
    topology: MountedFieldTopology
    initial_state: ExactFieldState
    steps: tuple[FieldExpressionStep, ...]
    precision_authority: PrecisionScheduleAuthority
    post_gate_state_node_ids: tuple[str, ...]
    receipt_sha256: str
    receipt_payload: bytes

    @property
    def dimension(self) -> int:
        return self.topology.dimension

    @property
    def field_evaluation_identity_sha256(self) -> str:
        """Digest of this expression's numeric-field-defining leaves only.

        Equal iff two expressions evaluate to the identical mathematical field
        at every shared precision; independent of the receipt bookkeeping
        (request/scene identity, provenance, injection receipts) that the field
        evaluator never reads.  See ``field_evaluation_identity_payload``.
        """

        return receipt_sha256(
            field_evaluation_identity_payload(
                topology_authority_receipt_sha256=(
                    self.topology_authority_receipt_sha256
                ),
                dimension=self.dimension,
                initial_state=self.initial_state,
                steps=self.steps,
            )
        )

    @property
    def topology_authority_receipt_sha256(self) -> str:
        return self.topology.authority_receipt_sha256

    @property
    def exact_input_bit_lengths(self) -> tuple[int, ...]:
        return _collect_exact_input_bit_lengths(self.initial_state, self.steps)

    @property
    def initial_precision_bits(self) -> int:
        exact_bits = self.exact_input_bit_lengths
        raw = (
            max(exact_bits)
            + len(exact_bits).bit_length()
            + self.dimension.bit_length()
            + len(self.steps).bit_length()
        )
        return _next_power_of_two(raw)

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        if FIBER_DIMENSION != 19:
            raise ReceiptError("closed-experience field requires exact 19-coordinate fibers")
        self.topology.verify(receipt_registry)
        self.precision_authority.verify(receipt_registry)
        self.initial_state.verify(receipt_registry)
        if not self.topology.available or self.dimension != 19 * len(
            self.topology.ordered_port_fibers
        ):
            raise ReceiptError("closed-experience topology is not exact 19 times mounted ports")
        if self.initial_state.topology_authority_receipt_sha256 != self.topology.authority_receipt_sha256:
            raise ReceiptError("closed-experience initial state belongs to another topology")
        if len(self.initial_state.amplitudes) != self.dimension:
            raise ReceiptError("closed-experience initial state dimension differs from topology")
        if not self.steps:
            raise ReceiptError("closed experience requires at least one post-gate state")
        expected_start = self.initial_state.source_time
        previous_sparse_provenance: dict[
            tuple[str, str], tuple[str, int, Fraction]
        ] = {}
        for step in self.steps:
            step.injection.verify(self.topology, receipt_registry)
            step.authority.verify(self.topology, step.injection, receipt_registry)
            if step.authority.source_time_start != expected_start:
                raise ReceiptError("closed-experience gates are not one continuous source-time chain")
            if isinstance(step.injection, SparseMapInjection):
                if step.injection.source_time != step.authority.source_time_end:
                    raise ReceiptError(
                        "asynchronous expression event differs from its source-time boundary"
                    )
                for mapped in step.injection.mapped_fibers:
                    current = (
                        mapped.evidence.provenance.source_epoch,
                        mapped.evidence.provenance.source_index,
                        mapped.evidence.provenance.source_timestamp,
                    )
                    previous = previous_sparse_provenance.get(mapped.fiber.key)
                    if previous is not None:
                        if current[0] != previous[0]:
                            raise ReceiptError(
                                "asynchronous expression changed source epoch without mounted transition authority"
                            )
                        if current[1] <= previous[1] or current[2] <= previous[2]:
                            raise ReceiptError(
                                "asynchronous expression evidence is not in strict native causal order"
                            )
                    previous_sparse_provenance[mapped.fiber.key] = current
            for leaf in step.hermitian_leaves:
                leaf.verify(receipt_registry)
                if leaf.dimension != self.dimension:
                    raise ReceiptError("Hermitian expression leaf dimension differs from topology")
            components = _combined_partition(
                self.dimension,
                _exact_upper_terms(step.authority),
                step.hermitian_leaves,
            )
            if any(
                len(component) > step.authority.max_connected_component_dimension
                for component in components
            ):
                raise ReceiptError("expression Hamiltonian exceeds mounted component resource authority")
            expected_start = step.authority.source_time_end
        expected_payload, expected_nodes, _ = _expression_dag_payload(
            topology=self.topology,
            initial_state=self.initial_state,
            steps=self.steps,
            precision_authority=self.precision_authority,
        )
        if self.post_gate_state_node_ids != expected_nodes:
            raise ReceiptError("closed-experience DAG node identities were altered")
        if self.receipt_payload != expected_payload or receipt_sha256(expected_payload) != self.receipt_sha256:
            raise ReceiptError("closed-experience expression differs from canonical receipt")


def create_closed_experience_expression(
    *,
    topology: MountedFieldTopology,
    initial_state: ExactFieldState,
    steps: Sequence[FieldExpressionStep],
    precision_authority: PrecisionScheduleAuthority,
    receipt_registry: ReceiptRegistry,
) -> ClosedExperienceFieldExpression:
    canonical_steps = tuple(steps)
    payload, node_ids, _ = _expression_dag_payload(
        topology=topology,
        initial_state=initial_state,
        steps=canonical_steps,
        precision_authority=precision_authority,
    )
    expression = ClosedExperienceFieldExpression(
        topology=topology,
        initial_state=initial_state,
        steps=canonical_steps,
        precision_authority=precision_authority,
        post_gate_state_node_ids=node_ids,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    expression.verify(receipt_registry)
    return expression


class ExpressionEvaluationStatus(str, Enum):
    CERTIFIED = "certified"
    UNKNOWN = "unknown"


def indeterminate_proof_request_receipt_payload(
    *,
    request_id: str,
    expression_receipt_sha256: str,
    previous_evaluation_receipt_sha256: str,
    previous_precision_bits: int,
    proof_obligation: str,
) -> bytes:
    require_identifier(request_id, "proof request id")
    require_identifier(proof_obligation, "proof obligation")
    sha256_digest(expression_receipt_sha256, "proof expression receipt")
    sha256_digest(previous_evaluation_receipt_sha256, "previous evaluation receipt")
    return _canonical_bytes(
        {
            "expression_receipt_sha256": expression_receipt_sha256,
            "previous_evaluation_receipt_sha256": previous_evaluation_receipt_sha256,
            "previous_precision_bits": previous_precision_bits,
            "proof_obligation": proof_obligation,
            "request_id": request_id,
            "requested_action": "double_working_precision_once",
            "schema": "glew.expression.indeterminate_proof_request.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class IndeterminateProofRequest:
    request_id: str
    expression_receipt_sha256: str
    previous_evaluation_receipt_sha256: str
    previous_precision_bits: int
    proof_obligation: str
    authority_receipt_sha256: str

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        expected = indeterminate_proof_request_receipt_payload(
            request_id=self.request_id,
            expression_receipt_sha256=self.expression_receipt_sha256,
            previous_evaluation_receipt_sha256=(
                self.previous_evaluation_receipt_sha256
            ),
            previous_precision_bits=self.previous_precision_bits,
            proof_obligation=self.proof_obligation,
        )
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "indeterminate proof request receipt"
        )
        if receipt_sha256(expected) != self.authority_receipt_sha256 or mounted != expected:
            raise ReceiptError("indeterminate proof request differs from mounted bytes")


@dataclass(frozen=True, slots=True)
class FieldExpressionEvaluation:
    expression_receipt_sha256: str
    topology_authority_receipt_sha256: str
    dimension: int
    source_time: Fraction
    status: ExpressionEvaluationStatus
    amplitudes: tuple[CertifiedComplexBall, ...]
    working_precision_bits: int
    precision_authority_receipt_sha256: str
    proof_request_receipt_sha256: str | None
    reason: str
    receipt_sha256: str
    receipt_payload: bytes

    def verify(self) -> None:
        expected = _evaluation_receipt_payload(
            expression_receipt_sha256=self.expression_receipt_sha256,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            dimension=self.dimension,
            source_time=self.source_time,
            status=self.status,
            amplitudes=self.amplitudes,
            working_precision_bits=self.working_precision_bits,
            precision_authority_receipt_sha256=(
                self.precision_authority_receipt_sha256
            ),
            proof_request_receipt_sha256=self.proof_request_receipt_sha256,
            reason=self.reason,
        )
        if self.receipt_payload != expected or receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("field-expression evaluation differs from canonical receipt")
        if self.status is ExpressionEvaluationStatus.CERTIFIED:
            if len(self.amplitudes) != self.dimension:
                raise ReceiptError("certified field-expression result has wrong dimension")
        elif self.amplitudes:
            raise ReceiptError("UNKNOWN field-expression result cannot authorize amplitudes")


def _evaluation_receipt_payload(
    *,
    expression_receipt_sha256: str,
    topology_authority_receipt_sha256: str,
    dimension: int,
    source_time: Fraction,
    status: ExpressionEvaluationStatus,
    amplitudes: Sequence[CertifiedComplexBall],
    working_precision_bits: int,
    precision_authority_receipt_sha256: str,
    proof_request_receipt_sha256: str | None,
    reason: str,
) -> bytes:
    return _canonical_bytes(
        {
            "amplitudes": [_complex_ball_payload(value) for value in amplitudes],
            "backend": {
                "flint": FLINT_VERSION,
                "precision_bits": working_precision_bits,
                "python_flint": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            },
            "dimension": dimension,
            "expression_receipt_sha256": expression_receipt_sha256,
            "precision_authority_receipt_sha256": precision_authority_receipt_sha256,
            "proof_request_receipt_sha256": proof_request_receipt_sha256,
            "reason": reason,
            "schema": "glew.expression.closed_experience_evaluation.v1",
            "solver": FIELD_EXPRESSION_SOLVER_ID,
            "source_time": _fraction_text(source_time),
            "status": status.value,
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


def _make_evaluation(
    *,
    expression: ClosedExperienceFieldExpression,
    status: ExpressionEvaluationStatus,
    amplitudes: Sequence[CertifiedComplexBall],
    precision_bits: int,
    proof_request_receipt_sha256: str | None,
    reason: str,
) -> FieldExpressionEvaluation:
    values = tuple(amplitudes)
    source_time = expression.steps[-1].authority.source_time_end
    payload = _evaluation_receipt_payload(
        expression_receipt_sha256=expression.receipt_sha256,
        topology_authority_receipt_sha256=(
            expression.topology_authority_receipt_sha256
        ),
        dimension=expression.dimension,
        source_time=source_time,
        status=status,
        amplitudes=values,
        working_precision_bits=precision_bits,
        precision_authority_receipt_sha256=(
            expression.precision_authority.authority_receipt_sha256
        ),
        proof_request_receipt_sha256=proof_request_receipt_sha256,
        reason=reason,
    )
    result = FieldExpressionEvaluation(
        expression_receipt_sha256=expression.receipt_sha256,
        topology_authority_receipt_sha256=(
            expression.topology_authority_receipt_sha256
        ),
        dimension=expression.dimension,
        source_time=source_time,
        status=status,
        amplitudes=values,
        working_precision_bits=precision_bits,
        precision_authority_receipt_sha256=(
            expression.precision_authority.authority_receipt_sha256
        ),
        proof_request_receipt_sha256=proof_request_receipt_sha256,
        reason=reason,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    result.verify()
    return result


def _acb_exact(flint, value: ExactComplex):
    return flint.acb(
        arb_fraction(flint, value.real), arb_fraction(flint, value.imag)
    )


def _resolve_leaf_upper(
    *,
    leaf: HermitianExpressionLeafReference,
    evaluators: Mapping[str, HermitianExpressionEvaluator],
    flint,
    precision_bits: int,
    memo: dict[str, tuple[EvaluatedHermitianUpperEntry, ...]],
) -> tuple[EvaluatedHermitianUpperEntry, ...]:
    digest = leaf.provider_expression_receipt_sha256
    if digest in memo:
        return memo[digest]
    try:
        evaluator = evaluators[digest]
    except KeyError as exc:
        raise ReceiptError("mounted Hermitian expression has no runtime evaluator") from exc
    if (
        getattr(evaluator, "provider_expression_receipt_sha256", None) != digest
        or getattr(evaluator, "dimension", None) != leaf.dimension
    ):
        raise ReceiptError("Hermitian runtime evaluator identity differs from mounted leaf")
    values = tuple(
        evaluator.evaluate_upper(
            flint=flint,
            working_precision_bits=precision_bits,
        )
    )
    positions = tuple((value.row, value.column) for value in values)
    if positions != leaf.upper_nonzero_positions:
        raise ReceiptError("Hermitian runtime evaluator changed declared upper structure")
    for value in values:
        if not hasattr(value.value, "is_finite") or not value.value.is_finite():
            raise ReceiptError("Hermitian expression evaluation is nonfinite")
        if value.row == value.column and not value.value.imag.is_zero():
            raise ReceiptError("Hermitian expression diagonal is not exactly real")
    memo[digest] = values
    return values


def evaluate_closed_experience_in_arb(
    expression: ClosedExperienceFieldExpression,
    *,
    flint,
    precision_bits: int,
    hermitian_evaluators: Mapping[str, HermitianExpressionEvaluator],
) -> tuple[object, ...]:
    """Evaluate the DAG inside an existing pinned-Arb precision context.

    This surface exists for expression-backed memory.  It returns live Arb
    expressions, not persistent authority; callers must keep every dependent
    operation in the same context and receipt the eventual certified result.
    """

    current = tuple(
        _acb_exact(flint, value) for value in expression.initial_state.amplitudes
    )
    post_gate_states: list[tuple[object, ...]] = []
    leaf_memo: dict[str, tuple[EvaluatedHermitianUpperEntry, ...]] = {}
    for step in expression.steps:
        exact_upper = _exact_upper_terms(step.authority)
        components = _combined_partition(
            expression.dimension, exact_upper, step.hermitian_leaves
        )
        upper_values: dict[tuple[int, int], object] = {}
        for row, column, value in exact_upper:
            upper_values[(row, column)] = _acb_exact(flint, value)
        for leaf in step.hermitian_leaves:
            for value in _resolve_leaf_upper(
                leaf=leaf,
                evaluators=hermitian_evaluators,
                flint=flint,
                precision_bits=precision_bits,
                memo=leaf_memo,
            ):
                key = (value.row, value.column)
                upper_values[key] = upper_values.get(key, flint.acb(0)) + value.value

        rates = {value.index: value for value in step.authority.local_rates}
        source = {value.index: value.value for value in step.authority.source}
        delta = arb_fraction(flint, step.authority.delta)
        hbar = arb_fraction(flint, step.authority.hbar)
        evolved_state: list[object | None] = [None] * expression.dimension
        for component in components:
            local_index = {global_index: index for index, global_index in enumerate(component)}
            size = len(component)
            augmented = flint.acb_mat(size + 1, size + 1)
            for global_row in component:
                row = local_index[global_row]
                rate = rates.get(global_row)
                if rate is not None:
                    augmented[row, row] += flint.acb(
                        arb_fraction(flint, rate.growth - rate.decay)
                    )
                for global_column in component:
                    upper_key = (
                        (global_row, global_column)
                        if global_row <= global_column
                        else (global_column, global_row)
                    )
                    h_value = upper_values.get(upper_key)
                    if h_value is None:
                        continue
                    if global_row > global_column:
                        h_value = h_value.conjugate()
                    augmented[row, local_index[global_column]] += (
                        -flint.acb(0, 1) * h_value / hbar
                    )
                source_value = source.get(global_row)
                if source_value is not None:
                    augmented[row, size] = _acb_exact(flint, source_value)
            transition = (augmented * delta).exp()
            if not all(
                transition[row, column].is_finite()
                for row in range(size + 1)
                for column in range(size + 1)
            ):
                raise ReceiptError("field-expression transition is nonfinite")
            initial_augmented = flint.acb_mat(
                size + 1,
                1,
                [*(current[index] for index in component), flint.acb(1)],
            )
            evolved = transition * initial_augmented
            for row, global_index in enumerate(component):
                value = evolved[row, 0]
                if not value.is_finite():
                    raise ReceiptError("field-expression state is nonfinite")
                evolved_state[global_index] = value
        if any(value is None for value in evolved_state):
            raise ReceiptError("field-expression component partition lost a coordinate")
        current = tuple(value for value in evolved_state if value is not None)
        post_gate_states.append(current)

    divisor = arb_fraction(flint, Fraction(len(post_gate_states)))
    centroid = []
    for index in range(expression.dimension):
        total = flint.acb(0)
        for state in post_gate_states:
            total += state[index]
        centroid.append(total / divisor)
    return tuple(centroid)


def _evaluate_at_precision(
    expression: ClosedExperienceFieldExpression,
    *,
    precision_bits: int,
    hermitian_evaluators: Mapping[str, HermitianExpressionEvaluator],
) -> tuple[CertifiedComplexBall, ...]:
    flint = load_pinned_flint()
    with flint.ctx.workprec(precision_bits):
        centroid = evaluate_closed_experience_in_arb(
            expression,
            flint=flint,
            precision_bits=precision_bits,
            hermitian_evaluators=hermitian_evaluators,
        )
        return tuple(
            CertifiedComplexBall(
                real=canonical_ball(value.real, precision_bits),
                imag=canonical_ball(value.imag, precision_bits),
            )
            for value in centroid
        )


def evaluate_closed_experience_expression(
    expression: ClosedExperienceFieldExpression,
    *,
    receipt_registry: ReceiptRegistry,
    hermitian_evaluators: Mapping[str, HermitianExpressionEvaluator] | None = None,
    previous_evaluation: FieldExpressionEvaluation | None = None,
    indeterminate_request: IndeterminateProofRequest | None = None,
) -> FieldExpressionEvaluation:
    """Evaluate once, or double once after an explicit indeterminate request."""

    expression.verify(receipt_registry)
    evaluators = {} if hermitian_evaluators is None else hermitian_evaluators
    proof_digest: str | None = None
    if indeterminate_request is None:
        if previous_evaluation is not None:
            raise ReceiptError("previous evaluation requires an indeterminate proof request")
        precision_bits = expression.initial_precision_bits
    else:
        if previous_evaluation is None:
            raise ReceiptError("indeterminate proof request requires the previous evaluation")
        previous_evaluation.verify()
        indeterminate_request.verify(receipt_registry)
        if (
            previous_evaluation.status is not ExpressionEvaluationStatus.CERTIFIED
            or previous_evaluation.expression_receipt_sha256 != expression.receipt_sha256
            or indeterminate_request.expression_receipt_sha256 != expression.receipt_sha256
            or indeterminate_request.previous_evaluation_receipt_sha256
            != previous_evaluation.receipt_sha256
            or indeterminate_request.previous_precision_bits
            != previous_evaluation.working_precision_bits
        ):
            raise ReceiptError("indeterminate request does not continue this exact evaluation")
        precision_bits = previous_evaluation.working_precision_bits * 2
        proof_digest = indeterminate_request.authority_receipt_sha256

    if precision_bits > expression.precision_authority.maximum_precision_bits:
        return _make_evaluation(
            expression=expression,
            status=ExpressionEvaluationStatus.UNKNOWN,
            amplitudes=(),
            precision_bits=precision_bits,
            proof_request_receipt_sha256=proof_digest,
            reason="mounted precision maximum exhausted; proof remains UNKNOWN",
        )
    amplitudes = _evaluate_at_precision(
        expression,
        precision_bits=precision_bits,
        hermitian_evaluators=evaluators,
    )
    return _make_evaluation(
        expression=expression,
        status=ExpressionEvaluationStatus.CERTIFIED,
        amplitudes=amplitudes,
        precision_bits=precision_bits,
        proof_request_receipt_sha256=proof_digest,
        reason="complete expression reevaluated from exact shared DAG leaves",
    )


@dataclass(frozen=True, slots=True)
class ModeExpressionInput:
    """Non-rational adapter surface for the mode boundary.

    ``modes.evaluate_mode_boundary`` currently accepts only ``ExactFieldState``.
    It must learn this interface and perform its projection in the same Arb
    evaluation; calling code cannot turn these amplitudes into rational values.
    """

    expression: ClosedExperienceFieldExpression

    @property
    def dimension(self) -> int:
        return self.expression.dimension

    @property
    def topology_authority_receipt_sha256(self) -> str:
        return self.expression.topology_authority_receipt_sha256

    @property
    def expression_receipt_sha256(self) -> str:
        return self.expression.receipt_sha256

    def evaluate(
        self,
        *,
        receipt_registry: ReceiptRegistry,
        hermitian_evaluators: Mapping[str, HermitianExpressionEvaluator] | None = None,
        previous_evaluation: FieldExpressionEvaluation | None = None,
        indeterminate_request: IndeterminateProofRequest | None = None,
    ) -> FieldExpressionEvaluation:
        return evaluate_closed_experience_expression(
            self.expression,
            receipt_registry=receipt_registry,
            hermitian_evaluators=hermitian_evaluators,
            previous_evaluation=previous_evaluation,
            indeterminate_request=indeterminate_request,
        )


__all__ = (
    "CENTROID_OPERATOR_ID",
    "FIELD_EVALUATION_IDENTITY_ID",
    "ClosedExperienceFieldExpression",
    "EvaluatedHermitianUpperEntry",
    "ExpressionEvaluationStatus",
    "FieldExpressionEvaluation",
    "FieldExpressionStep",
    "HermitianExpressionEvaluator",
    "HermitianExpressionLeafReference",
    "IndeterminateProofRequest",
    "ModeExpressionInput",
    "PRECISION_SCHEDULE_ID",
    "PrecisionScheduleAuthority",
    "create_closed_experience_expression",
    "create_hermitian_leaf_reference",
    "evaluate_closed_experience_expression",
    "evaluate_closed_experience_in_arb",
    "field_evaluation_identity_payload",
    "hermitian_leaf_reference_receipt_payload",
    "indeterminate_proof_request_receipt_payload",
    "precision_schedule_authority_receipt_payload",
)
