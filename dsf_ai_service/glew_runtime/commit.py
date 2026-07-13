"""Fail-closed expression-backed full-field GLEW commit authority.

The commit boundary accepts only the stable expression recognition result.
It never accepts the legacy rational ``RecognitionResult`` as full-field
authority and never converts an expression result into that legacy type.

One stored expression mode may commit only when its certified probability
lower bound strictly exceeds every other stored-mode upper bound and the
orthogonal-residual upper bound, and every independent full-field authority is
present and affirmative.  Missing or indeterminate evidence is UNKNOWN; no
score, vocabulary lookup, threshold substitute, or fallback can authorize a
commit.
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
)
from .expression_modes import (
    ExpressionModeBoundaryResult,
    ExpressionRecognitionStatus,
)
from .field import (
    EvidenceValidityState,
    MountedFieldTopology,
    PortTransportEvidence,
    StructuralFactState,
)
from .l6 import L6Evaluation, L6EvaluationStatus, N_START
from .model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)


COMMIT_OPERATOR_ID = "glew.full_field_expression_unique_mode_commit.v1"
PENDING_GLOBAL_UF_OPERATOR_ID = (
    "glew.full_field_expression_pending_global_uf_conjunction.v1"
)


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


def _strict_json(payload: bytes, description: str) -> dict[str, object]:
    if not isinstance(payload, bytes) or not payload:
        raise ReceiptError(f"{description} must be nonempty exact bytes")

    def reject_constant(value: str) -> None:
        raise ReceiptError(f"{description} contains forbidden constant {value}")

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ReceiptError(f"{description} contains duplicate key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"{description} is not strict canonical JSON") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise ReceiptError(f"{description} is not canonical JSON")
    return value


def _parse_fraction(value: object, description: str) -> Fraction:
    if not isinstance(value, str):
        raise ReceiptError(f"{description} must be an exact fraction string")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ReceiptError(f"{description} is not an exact fraction") from exc
    if _fraction_text(result) != value:
        raise ReceiptError(f"{description} is not a canonical exact fraction")
    return result


def _mounted_exact(
    registry: ReceiptRegistry,
    digest: str,
    expected: bytes,
    description: str,
) -> None:
    mounted = registry.resolve(digest, description)
    if mounted != expected or receipt_sha256(expected) != digest:
        raise ReceiptError(f"{description} differs from mounted authority bytes")


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


def _ball_bounds(value: CertifiedBall) -> tuple[Fraction, Fraction]:
    if not isinstance(value, CertifiedBall):
        raise ReceiptError("expression probability is not a certified ball")
    if (
        value.python_flint_version != PYTHON_FLINT_VERSION
        or value.flint_version != FLINT_VERSION
        or value.wheel_sha256 != PYTHON_FLINT_WHEEL_SHA256
    ):
        raise ReceiptError("expression probability has different backend authority")
    lower = Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent
    upper = Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent
    if lower > upper:
        raise ReceiptError("expression probability interval is inverted")
    return lower, upper


class BinaryAuthorityKind(str, Enum):
    SAFE_MODE_CLEAR = "safe_mode_clear"
    GLOBAL_UF_VALIDATION = "global_uf_validation"


class AuthorityDisposition(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


def binary_authority_receipt_payload(
    *,
    authority_id: str,
    kind: BinaryAuthorityKind,
    disposition: AuthorityDisposition,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    source_operator_receipt_sha256: str,
) -> bytes:
    require_identifier(authority_id, "binary authority id")
    if not isinstance(kind, BinaryAuthorityKind):
        raise ReceiptError("binary authority kind must be typed")
    if not isinstance(disposition, AuthorityDisposition):
        raise ReceiptError("binary authority disposition must be typed")
    for value, name in (
        (topology_authority_receipt_sha256, "binary topology receipt"),
        (closed_experience_receipt_sha256, "binary experience receipt"),
        (source_operator_receipt_sha256, "binary source receipt"),
    ):
        sha256_digest(value, name)
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "closed_experience_receipt_sha256": closed_experience_receipt_sha256,
            "disposition": disposition.value,
            "kind": kind.value,
            "schema": "glew.commit.binary_authority.v1",
            "source_operator_receipt_sha256": source_operator_receipt_sha256,
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class BinaryCommitAuthority:
    authority_id: str
    kind: BinaryAuthorityKind
    disposition: AuthorityDisposition
    topology_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    source_operator_receipt_sha256: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.authority_id, "binary authority id")
        if not isinstance(self.kind, BinaryAuthorityKind):
            raise ReceiptError("binary authority kind must be typed")
        if not isinstance(self.disposition, AuthorityDisposition):
            raise ReceiptError("binary authority disposition must be typed")
        for value, name in (
            (self.topology_authority_receipt_sha256, "binary topology receipt"),
            (self.closed_experience_receipt_sha256, "binary experience receipt"),
            (self.source_operator_receipt_sha256, "binary source receipt"),
            (self.authority_receipt_sha256, "binary authority receipt"),
        ):
            sha256_digest(value, name)

    def verify(
        self,
        *,
        expected_kind: BinaryAuthorityKind,
        topology_receipt: str,
        experience_receipt: str,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.kind is not expected_kind:
            raise ReceiptError("a binary authority was supplied in the wrong role")
        if self.topology_authority_receipt_sha256 != topology_receipt:
            raise ReceiptError("binary authority belongs to a different topology")
        if self.closed_experience_receipt_sha256 != experience_receipt:
            raise ReceiptError("binary authority belongs to a different experience")
        receipt_registry.resolve(
            self.source_operator_receipt_sha256,
            f"{self.kind.value} source-operator receipt",
        )
        expected = binary_authority_receipt_payload(
            authority_id=self.authority_id,
            kind=self.kind,
            disposition=self.disposition,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            source_operator_receipt_sha256=self.source_operator_receipt_sha256,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            f"{self.kind.value} authority receipt",
        )


class EventSupportState(str, Enum):
    POSITIVE = "positive"
    ZERO = "zero"
    UNKNOWN = "unknown"


def event_support_authority_receipt_payload(
    *,
    authority_id: str,
    state: EventSupportState,
    exact_r_event: Fraction | None,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    source_operator_receipt_sha256: str,
) -> bytes:
    require_identifier(authority_id, "R_event authority id")
    if not isinstance(state, EventSupportState):
        raise ReceiptError("R_event state must be typed")
    if state is EventSupportState.POSITIVE:
        require_fraction(exact_r_event, "positive R_event")
        if exact_r_event <= 0:
            raise ReceiptError("positive R_event must prove value greater than zero")
    elif state is EventSupportState.ZERO:
        require_fraction(exact_r_event, "zero R_event")
        if exact_r_event != 0:
            raise ReceiptError("zero R_event must carry exact zero")
    elif exact_r_event is not None:
        raise ReceiptError("unknown R_event cannot carry a nominal value")
    for value, name in (
        (topology_authority_receipt_sha256, "R_event topology receipt"),
        (closed_experience_receipt_sha256, "R_event experience receipt"),
        (source_operator_receipt_sha256, "R_event source receipt"),
    ):
        sha256_digest(value, name)
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "closed_experience_receipt_sha256": closed_experience_receipt_sha256,
            "exact_R_event": (
                None if exact_r_event is None else _fraction_text(exact_r_event)
            ),
            "schema": "glew.commit.event_support_authority.v1",
            "source_operator_receipt_sha256": source_operator_receipt_sha256,
            "state": state.value,
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
            "unit": "dimensionless",
        }
    )


@dataclass(frozen=True, slots=True)
class EventSupportAuthority:
    authority_id: str
    state: EventSupportState
    exact_r_event: Fraction | None
    topology_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    source_operator_receipt_sha256: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        event_support_authority_receipt_payload(
            authority_id=self.authority_id,
            state=self.state,
            exact_r_event=self.exact_r_event,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            source_operator_receipt_sha256=self.source_operator_receipt_sha256,
        )
        sha256_digest(self.authority_receipt_sha256, "R_event authority receipt")

    def verify(
        self,
        *,
        topology_receipt: str,
        experience_receipt: str,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.topology_authority_receipt_sha256 != topology_receipt:
            raise ReceiptError("R_event authority belongs to a different topology")
        if self.closed_experience_receipt_sha256 != experience_receipt:
            raise ReceiptError("R_event authority belongs to a different experience")
        receipt_registry.resolve(
            self.source_operator_receipt_sha256,
            "R_event source-operator receipt",
        )
        expected = event_support_authority_receipt_payload(
            authority_id=self.authority_id,
            state=self.state,
            exact_r_event=self.exact_r_event,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            source_operator_receipt_sha256=self.source_operator_receipt_sha256,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "R_event authority receipt",
        )


class GovernedFact(str, Enum):
    S_UF = "S_UF"
    R_UF = "R_UF"


class ApplicabilityState(str, Enum):
    REQUIRED = "required"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


def l5_applicability_receipt_payload(
    *,
    authority_id: str,
    lane_id: str,
    port_id: str,
    fact: GovernedFact,
    state: ApplicabilityState,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    source_governance_receipt_sha256: str,
) -> bytes:
    for value, name in (
        (authority_id, "L5 authority id"),
        (lane_id, "L5 lane id"),
        (port_id, "L5 port id"),
    ):
        require_identifier(value, name)
    if not isinstance(fact, GovernedFact):
        raise ReceiptError("L5 applicability fact must be typed")
    if not isinstance(state, ApplicabilityState):
        raise ReceiptError("L5 applicability state must be typed")
    for value, name in (
        (topology_authority_receipt_sha256, "L5 topology receipt"),
        (closed_experience_receipt_sha256, "L5 experience receipt"),
        (source_governance_receipt_sha256, "L5 governance receipt"),
    ):
        sha256_digest(value, name)
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "closed_experience_receipt_sha256": closed_experience_receipt_sha256,
            "fact": fact.value,
            "lane_id": lane_id,
            "port_id": port_id,
            "schema": "glew.commit.l5_applicability.v1",
            "source_governance_receipt_sha256": source_governance_receipt_sha256,
            "state": state.value,
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class L5Applicability:
    authority_id: str
    lane_id: str
    port_id: str
    fact: GovernedFact
    state: ApplicabilityState
    topology_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    source_governance_receipt_sha256: str
    authority_receipt_sha256: str

    @property
    def key(self) -> tuple[str, str, GovernedFact]:
        return (self.lane_id, self.port_id, self.fact)

    def __post_init__(self) -> None:
        l5_applicability_receipt_payload(
            authority_id=self.authority_id,
            lane_id=self.lane_id,
            port_id=self.port_id,
            fact=self.fact,
            state=self.state,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            source_governance_receipt_sha256=(
                self.source_governance_receipt_sha256
            ),
        )
        sha256_digest(self.authority_receipt_sha256, "L5 applicability receipt")

    def verify(
        self,
        *,
        topology_receipt: str,
        experience_receipt: str,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.topology_authority_receipt_sha256 != topology_receipt:
            raise ReceiptError("L5 applicability belongs to a different topology")
        if self.closed_experience_receipt_sha256 != experience_receipt:
            raise ReceiptError("L5 applicability belongs to a different experience")
        receipt_registry.resolve(
            self.source_governance_receipt_sha256,
            "L5 source-governance receipt",
        )
        expected = l5_applicability_receipt_payload(
            authority_id=self.authority_id,
            lane_id=self.lane_id,
            port_id=self.port_id,
            fact=self.fact,
            state=self.state,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            source_governance_receipt_sha256=(
                self.source_governance_receipt_sha256
            ),
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "L5 applicability receipt",
        )


def closed_experience_seal_receipt_payload(
    *,
    experience_id: str,
    topology_authority_receipt_sha256: str,
    input_expression_receipt_sha256: str,
    recognition_receipt_sha256: str,
    ordered_evidence_receipt_sha256s: Sequence[str],
    source_time_start: Fraction,
    source_time_end: Fraction,
    structural_time_unit: str,
) -> bytes:
    require_identifier(experience_id, "closed experience id")
    require_identifier(structural_time_unit, "closed experience time unit")
    require_fraction(source_time_start, "closed experience source_time_start")
    require_fraction(source_time_end, "closed experience source_time_end")
    if source_time_end <= source_time_start:
        raise ReceiptError("closed experience requires positive source-time duration")
    for value, name in (
        (topology_authority_receipt_sha256, "closed topology receipt"),
        (input_expression_receipt_sha256, "closed input-expression receipt"),
        (recognition_receipt_sha256, "closed recognition receipt"),
    ):
        sha256_digest(value, name)
    if not ordered_evidence_receipt_sha256s:
        raise ReceiptError("closed experience requires typed evidence receipts")
    for digest in ordered_evidence_receipt_sha256s:
        sha256_digest(digest, "closed experience evidence receipt")
    if len(set(ordered_evidence_receipt_sha256s)) != len(
        ordered_evidence_receipt_sha256s
    ):
        raise ReceiptError("closed experience repeats an evidence receipt")
    return _canonical_bytes(
        {
            "close_authority": "explicit_context_close",
            "experience_id": experience_id,
            "input_expression_receipt_sha256": input_expression_receipt_sha256,
            "ordered_evidence_receipt_sha256s": list(
                ordered_evidence_receipt_sha256s
            ),
            "recognition_receipt_sha256": recognition_receipt_sha256,
            "schema": "glew.commit.closed_expression_experience.v1",
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "structural_time_unit": structural_time_unit,
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


def _expression_extent(
    *,
    expression_payload: bytes,
    topology_receipt: str,
    structural_time_unit: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[Fraction, Fraction]:
    expression = _strict_json(expression_payload, "input field expression")
    if (
        expression.get("schema") != "glew.expression.closed_experience_field.v1"
        or expression.get("topology_authority_receipt_sha256") != topology_receipt
    ):
        raise ReceiptError("input expression belongs to another field topology")
    nodes = expression.get("dag_nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ReceiptError("input expression has no exact DAG nodes")
    initial_times: list[Fraction] = []
    post_nodes: list[dict[str, object]] = []
    for wrapper in nodes:
        if not isinstance(wrapper, dict) or not isinstance(wrapper.get("node"), dict):
            raise ReceiptError("input expression DAG node is malformed")
        node = wrapper["node"]
        if node.get("kind") == "exact_initial_state":
            initial_times.append(
                _parse_fraction(node.get("source_time"), "expression start time")
            )
        elif node.get("kind") == "post_gate_evolution_state":
            post_nodes.append(node)
    if len(initial_times) != 1 or not post_nodes:
        raise ReceiptError("input expression lacks one initial and post-gate chain")
    expected_start = initial_times[0]
    for node in post_nodes:
        start = _parse_fraction(node.get("source_time_start"), "gate start time")
        end = _parse_fraction(node.get("source_time_end"), "gate end time")
        if start != expected_start or end <= start:
            raise ReceiptError("input expression gate times are not continuous")
        authority_digest = node.get("evolution_authority_receipt_sha256")
        if not isinstance(authority_digest, str):
            raise ReceiptError("input expression gate lacks evolution authority")
        authority_payload = receipt_registry.resolve(
            authority_digest,
            "input expression evolution authority",
        )
        authority = _strict_json(
            authority_payload,
            "input expression evolution authority",
        )
        if (
            authority.get("source_time_start") != _fraction_text(start)
            or authority.get("source_time_end") != _fraction_text(end)
            or authority.get("source_time_unit") != structural_time_unit
            or authority.get("topology_authority_receipt_sha256")
            != topology_receipt
        ):
            raise ReceiptError("expression evolution authority differs from sealed time")
        expected_start = end
    return initial_times[0], expected_start


@dataclass(frozen=True, slots=True)
class ClosedExperienceSeal:
    experience_id: str
    topology_authority_receipt_sha256: str
    input_expression_receipt_sha256: str
    recognition_receipt_sha256: str
    ordered_evidence_receipt_sha256s: tuple[str, ...]
    source_time_start: Fraction
    source_time_end: Fraction
    structural_time_unit: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        closed_experience_seal_receipt_payload(
            experience_id=self.experience_id,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            input_expression_receipt_sha256=(
                self.input_expression_receipt_sha256
            ),
            recognition_receipt_sha256=self.recognition_receipt_sha256,
            ordered_evidence_receipt_sha256s=(
                self.ordered_evidence_receipt_sha256s
            ),
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            structural_time_unit=self.structural_time_unit,
        )
        sha256_digest(self.authority_receipt_sha256, "closed-experience seal")

    def verify(
        self,
        *,
        topology: MountedFieldTopology,
        recognition: ExpressionModeBoundaryResult,
        evidence: Sequence[PortTransportEvidence],
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.topology_authority_receipt_sha256 != (
            topology.authority_receipt_sha256
        ):
            raise ReceiptError("closed experience belongs to a different topology")
        if self.recognition_receipt_sha256 != recognition.receipt_sha256:
            raise ReceiptError("closed experience names a different recognition result")
        if self.input_expression_receipt_sha256 != (
            recognition.input_expression_receipt_sha256
        ):
            raise ReceiptError("closed experience names a different input expression")
        evidence_receipts = tuple(value.evidence_receipt_sha256 for value in evidence)
        if evidence_receipts != self.ordered_evidence_receipt_sha256s:
            raise ReceiptError("closed experience evidence order differs from seal")
        expected = closed_experience_seal_receipt_payload(
            experience_id=self.experience_id,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            input_expression_receipt_sha256=(
                self.input_expression_receipt_sha256
            ),
            recognition_receipt_sha256=self.recognition_receipt_sha256,
            ordered_evidence_receipt_sha256s=(
                self.ordered_evidence_receipt_sha256s
            ),
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            structural_time_unit=self.structural_time_unit,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "closed-experience seal",
        )
        expression_payload = receipt_registry.resolve(
            self.input_expression_receipt_sha256,
            "closed input-expression receipt",
        )
        start, end = _expression_extent(
            expression_payload=expression_payload,
            topology_receipt=topology.authority_receipt_sha256,
            structural_time_unit=self.structural_time_unit,
            receipt_registry=receipt_registry,
        )
        if start != self.source_time_start or end != self.source_time_end:
            raise ReceiptError("closed experience time span differs from expression")


def l6_evaluation_receipt_payload(evaluation: L6Evaluation) -> bytes:
    if not isinstance(evaluation, L6Evaluation):
        raise ReceiptError("commit boundary requires a typed L6 evaluation")
    rank = evaluation.rank_receipt
    proof = evaluation.arb_proof
    return _canonical_bytes(
        {
            "arb_proof": (
                None
                if proof is None
                else {
                    "below_threshold": proof.below_threshold,
                    "expression": proof.expression,
                    "flint_version": proof.flint_version,
                    "n_effective": proof.n_effective,
                    "precision_bits": proof.precision_bits,
                    "python_flint_version": proof.python_flint_version,
                    "threads": proof.threads,
                    "threshold_ball": proof.threshold_ball,
                }
            ),
            "omega": None if evaluation.omega is None else _fraction_text(evaluation.omega),
            "rank_receipt": {
                "n_effective": rank.n_effective,
                "n_start": rank.n_start,
                "pivot_columns": list(rank.pivot_columns),
                "rank": rank.rank,
                "row_count": rank.row_count,
            },
            "reason": evaluation.reason,
            "schema": "glew.commit.fixed42_evaluation.v1",
            "status": evaluation.status.value,
            "structural_lock": evaluation.structural_lock,
        }
    )


def l6_scope_authority_receipt_payload(
    *,
    authority_id: str,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    l6_evaluation_receipt_sha256: str,
) -> bytes:
    require_identifier(authority_id, "L6 scope authority id")
    for value, name in (
        (topology_authority_receipt_sha256, "L6 topology receipt"),
        (closed_experience_receipt_sha256, "L6 experience receipt"),
        (l6_evaluation_receipt_sha256, "L6 evaluation receipt"),
    ):
        sha256_digest(value, name)
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "closed_experience_receipt_sha256": closed_experience_receipt_sha256,
            "l6_evaluation_receipt_sha256": l6_evaluation_receipt_sha256,
            "schema": "glew.commit.fixed42_scope_authority.v1",
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class L6ScopeAuthority:
    authority_id: str
    topology_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    l6_evaluation_receipt_sha256: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        l6_scope_authority_receipt_payload(
            authority_id=self.authority_id,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            l6_evaluation_receipt_sha256=self.l6_evaluation_receipt_sha256,
        )
        sha256_digest(self.authority_receipt_sha256, "L6 scope authority receipt")

    def verify(
        self,
        *,
        topology_receipt: str,
        experience_receipt: str,
        evaluation: L6Evaluation,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.topology_authority_receipt_sha256 != topology_receipt:
            raise ReceiptError("L6 scope belongs to a different topology")
        if self.closed_experience_receipt_sha256 != experience_receipt:
            raise ReceiptError("L6 scope belongs to a different experience")
        evaluation_payload = l6_evaluation_receipt_payload(evaluation)
        if receipt_sha256(evaluation_payload) != self.l6_evaluation_receipt_sha256:
            raise ReceiptError("L6 scope names a different evaluation")
        _mounted_exact(
            receipt_registry,
            self.l6_evaluation_receipt_sha256,
            evaluation_payload,
            "L6 evaluation receipt",
        )
        expected = l6_scope_authority_receipt_payload(
            authority_id=self.authority_id,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            l6_evaluation_receipt_sha256=self.l6_evaluation_receipt_sha256,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "L6 scope authority receipt",
        )


class CommitStatus(str, Enum):
    COMMIT = "commit"
    NO_COMMIT = "no_commit"
    UNKNOWN_NO_COMMIT = "unknown_no_commit"


class PendingGlobalUFStatus(str, Enum):
    READY_EXCEPT_GLOBAL_UF = "ready_except_global_uf"
    NO_COMMIT = "no_commit"
    UNKNOWN = "unknown"


def _pending_global_uf_payload(
    *,
    status: PendingGlobalUFStatus,
    selected_mode_index: int | None,
    selected_mode_receipt_sha256: str | None,
    findings: Sequence[str],
    topology_receipt: str,
    experience_receipt: str,
    expression_recognition_receipt: str,
    pre_growth_expression_bank_receipt: str,
    l6_evaluation_receipt: str,
    safe_mode_receipt: str,
    event_support_receipt: str,
    evidence_receipts: Sequence[str],
    applicability_receipts: Sequence[str],
) -> bytes:
    if not isinstance(status, PendingGlobalUFStatus):
        raise ReceiptError("pending Global-UF conjunction status is not typed")
    for value, description in (
        (topology_receipt, "pending conjunction topology"),
        (experience_receipt, "pending conjunction experience"),
        (
            expression_recognition_receipt,
            "pending conjunction recognition",
        ),
        (
            pre_growth_expression_bank_receipt,
            "pending conjunction pre-growth bank",
        ),
        (l6_evaluation_receipt, "pending conjunction L6"),
        (safe_mode_receipt, "pending conjunction SafeMode"),
        (event_support_receipt, "pending conjunction R_event"),
    ):
        sha256_digest(value, description)
    for values, description in (
        (evidence_receipts, "pending conjunction evidence"),
        (applicability_receipts, "pending conjunction L5 applicability"),
    ):
        for value in values:
            sha256_digest(value, description)
    if not isinstance(findings, Sequence) or isinstance(findings, (str, bytes)):
        raise ReceiptError("pending conjunction findings are not a sequence")
    for finding in findings:
        require_identifier(finding, "pending conjunction finding")
    if status is PendingGlobalUFStatus.READY_EXCEPT_GLOBAL_UF:
        if (
            isinstance(selected_mode_index, bool)
            or not isinstance(selected_mode_index, int)
            or selected_mode_index < 0
            or selected_mode_receipt_sha256 is None
            or findings
        ):
            raise ReceiptError(
                "ready pending conjunction lacks one exact selected mode"
            )
        sha256_digest(
            selected_mode_receipt_sha256,
            "pending conjunction selected mode",
        )
    elif (
        selected_mode_index is not None
        or selected_mode_receipt_sha256 is not None
        or not findings
    ):
        raise ReceiptError(
            "non-ready pending conjunction has selection or no finding"
        )
    return _canonical_bytes(
        {
            "applicability_receipt_sha256s": list(
                applicability_receipts
            ),
            "closed_experience_receipt_sha256": experience_receipt,
            "event_support_receipt_sha256": event_support_receipt,
            "evidence_receipt_sha256s": list(evidence_receipts),
            "expression_recognition_receipt_sha256": (
                expression_recognition_receipt
            ),
            "findings": list(findings),
            "global_uf_state": "pending_not_evaluated",
            "l6_evaluation_receipt_sha256": l6_evaluation_receipt,
            "operator": PENDING_GLOBAL_UF_OPERATOR_ID,
            "pre_growth_expression_bank_receipt_sha256": (
                pre_growth_expression_bank_receipt
            ),
            "safe_mode_receipt_sha256": safe_mode_receipt,
            "schema": "glew.commit.pending_global_uf_conjunction.v1",
            "selected_mode_index": selected_mode_index,
            "selected_mode_receipt_sha256": selected_mode_receipt_sha256,
            "status": status.value,
            "topology_authority_receipt_sha256": topology_receipt,
        }
    )


@dataclass(frozen=True, slots=True)
class PendingGlobalUFConjunction:
    status: PendingGlobalUFStatus
    selected_mode_index: int | None
    selected_mode_receipt_sha256: str | None
    findings: tuple[str, ...]
    topology_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    expression_recognition_receipt_sha256: str
    pre_growth_expression_bank_receipt_sha256: str
    l6_evaluation_receipt_sha256: str
    safe_mode_receipt_sha256: str
    event_support_receipt_sha256: str
    evidence_receipt_sha256s: tuple[str, ...]
    applicability_receipt_sha256s: tuple[str, ...]
    receipt_sha256: str
    receipt_payload: bytes

    @property
    def ready_except_global_uf(self) -> bool:
        return self.status is PendingGlobalUFStatus.READY_EXCEPT_GLOBAL_UF

    def verify(self) -> None:
        expected = _pending_global_uf_payload(
            status=self.status,
            selected_mode_index=self.selected_mode_index,
            selected_mode_receipt_sha256=(
                self.selected_mode_receipt_sha256
            ),
            findings=self.findings,
            topology_receipt=self.topology_authority_receipt_sha256,
            experience_receipt=self.closed_experience_receipt_sha256,
            expression_recognition_receipt=(
                self.expression_recognition_receipt_sha256
            ),
            pre_growth_expression_bank_receipt=(
                self.pre_growth_expression_bank_receipt_sha256
            ),
            l6_evaluation_receipt=self.l6_evaluation_receipt_sha256,
            safe_mode_receipt=self.safe_mode_receipt_sha256,
            event_support_receipt=self.event_support_receipt_sha256,
            evidence_receipts=self.evidence_receipt_sha256s,
            applicability_receipts=self.applicability_receipt_sha256s,
        )
        if (
            self.receipt_payload != expected
            or receipt_sha256(expected) != self.receipt_sha256
        ):
            raise ReceiptError(
                "pending Global-UF conjunction differs from receipt"
            )


def _decision_payload(
    *,
    status: CommitStatus,
    selected_mode_index: int | None,
    selected_mode_receipt_sha256: str | None,
    findings: Sequence[str],
    topology_receipt: str,
    experience_receipt: str,
    expression_recognition_receipt: str,
    pre_growth_expression_bank_receipt: str,
    l6_evaluation_receipt: str,
    safe_mode_receipt: str,
    event_support_receipt: str,
    global_uf_receipt: str,
    evidence_receipts: Sequence[str],
    applicability_receipts: Sequence[str],
) -> bytes:
    return _canonical_bytes(
        {
            "applicability_receipt_sha256s": list(applicability_receipts),
            "closed_experience_receipt_sha256": experience_receipt,
            "event_support_receipt_sha256": event_support_receipt,
            "evidence_receipt_sha256s": list(evidence_receipts),
            "expression_recognition_receipt_sha256": (
                expression_recognition_receipt
            ),
            "findings": list(findings),
            "global_uf_receipt_sha256": global_uf_receipt,
            "l6_evaluation_receipt_sha256": l6_evaluation_receipt,
            "operator": COMMIT_OPERATOR_ID,
            "pre_growth_expression_bank_receipt_sha256": (
                pre_growth_expression_bank_receipt
            ),
            "safe_mode_receipt_sha256": safe_mode_receipt,
            "schema": "glew.commit.full_field_expression_decision.v1",
            "selected_mode_index": selected_mode_index,
            "selected_mode_receipt_sha256": selected_mode_receipt_sha256,
            "status": status.value,
            "topology_authority_receipt_sha256": topology_receipt,
        }
    )


@dataclass(frozen=True, slots=True)
class CommitDecision:
    status: CommitStatus
    selected_mode_index: int | None
    selected_mode_receipt_sha256: str | None
    findings: tuple[str, ...]
    topology_authority_receipt_sha256: str
    closed_experience_receipt_sha256: str
    expression_recognition_receipt_sha256: str
    pre_growth_expression_bank_receipt_sha256: str
    l6_evaluation_receipt_sha256: str
    safe_mode_receipt_sha256: str
    event_support_receipt_sha256: str
    global_uf_receipt_sha256: str
    evidence_receipt_sha256s: tuple[str, ...]
    applicability_receipt_sha256s: tuple[str, ...]
    receipt_sha256: str
    receipt_payload: bytes

    @property
    def committed(self) -> bool:
        return self.status is CommitStatus.COMMIT

    def verify(self) -> None:
        expected = _decision_payload(
            status=self.status,
            selected_mode_index=self.selected_mode_index,
            selected_mode_receipt_sha256=self.selected_mode_receipt_sha256,
            findings=self.findings,
            topology_receipt=self.topology_authority_receipt_sha256,
            experience_receipt=self.closed_experience_receipt_sha256,
            expression_recognition_receipt=(
                self.expression_recognition_receipt_sha256
            ),
            pre_growth_expression_bank_receipt=(
                self.pre_growth_expression_bank_receipt_sha256
            ),
            l6_evaluation_receipt=self.l6_evaluation_receipt_sha256,
            safe_mode_receipt=self.safe_mode_receipt_sha256,
            event_support_receipt=self.event_support_receipt_sha256,
            global_uf_receipt=self.global_uf_receipt_sha256,
            evidence_receipts=self.evidence_receipt_sha256s,
            applicability_receipts=self.applicability_receipt_sha256s,
        )
        if expected != self.receipt_payload or receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("commit decision fields differ from immutable receipt")
        if self.status is CommitStatus.COMMIT:
            if self.selected_mode_index is None or self.selected_mode_receipt_sha256 is None:
                raise ReceiptError("commit receipt does not name one stable expression mode")
        elif self.selected_mode_index is not None or self.selected_mode_receipt_sha256 is not None:
            raise ReceiptError("silent decision cannot carry a selected mode")


def _verify_l6_internal(evaluation: L6Evaluation) -> None:
    rank = evaluation.rank_receipt
    if rank.n_start != N_START:
        raise ReceiptError("L6 evaluation does not use fixed 42 columns")
    if rank.rank < 0 or rank.n_effective != N_START - rank.rank:
        raise ReceiptError("L6 rank receipt is internally inconsistent")
    if len(rank.pivot_columns) != rank.rank or tuple(sorted(rank.pivot_columns)) != (
        rank.pivot_columns
    ):
        raise ReceiptError("L6 rank receipt has inconsistent pivots")
    if evaluation.status is L6EvaluationStatus.LOCK:
        proof = evaluation.arb_proof
        if evaluation.structural_lock is not True or proof is None:
            raise ReceiptError("L6 LOCK lacks a structural-lock proof")
        if (
            proof.python_flint_version != PYTHON_FLINT_VERSION
            or proof.flint_version != FLINT_VERSION
            or proof.threads != 1
            or proof.expression != "n_effective < 42/exp(1)"
            or proof.n_effective != rank.n_effective
            or not proof.below_threshold
        ):
            raise ReceiptError("L6 LOCK proof has inconsistent backend or geometry")
    elif evaluation.status is L6EvaluationStatus.NO_LOCK:
        if evaluation.structural_lock is not False:
            raise ReceiptError("L6 NO_LOCK carries inconsistent truth state")
    elif evaluation.status is L6EvaluationStatus.UNKNOWN_NO_LOCK:
        if evaluation.structural_lock is not None:
            raise ReceiptError("unknown L6 carries a selected truth value")
    else:
        raise ReceiptError("L6 evaluation status is not typed")


def _verify_expression_recognition(
    *,
    topology: MountedFieldTopology,
    recognition: ExpressionModeBoundaryResult,
    receipt_registry: ReceiptRegistry,
) -> tuple[bool, int | None, str | None, bool]:
    if not isinstance(recognition, ExpressionModeBoundaryResult):
        raise ReceiptError(
            "commit boundary requires ExpressionModeBoundaryResult; legacy "
            "RecognitionResult is not full-field authority"
        )
    recognition.verify()
    recognition.pre_growth_bank.verify(
        topology=topology,
        receipt_registry=receipt_registry,
    )
    recognition.post_growth_bank.verify(
        topology=topology,
        receipt_registry=receipt_registry,
    )
    _mounted_exact(
        receipt_registry,
        recognition.receipt_sha256,
        recognition.receipt_payload,
        "expression recognition result receipt",
    )
    for bank, description in (
        (recognition.pre_growth_bank, "pre-growth expression bank receipt"),
        (recognition.post_growth_bank, "post-growth expression bank receipt"),
    ):
        _mounted_exact(
            receipt_registry,
            bank.receipt_sha256,
            bank.receipt_payload,
            description,
        )
        for mode in bank.modes:
            _mounted_exact(
                receipt_registry,
                mode.receipt_sha256,
                mode.receipt_payload,
                "stable expression mode receipt",
            )
            _mounted_exact(
                receipt_registry,
                mode.growth_proof_receipt_sha256,
                mode.growth_proof_receipt_payload,
                "expression mode growth proof receipt",
            )
    expression_payload = receipt_registry.resolve(
        recognition.input_expression_receipt_sha256,
        "recognition input-expression receipt",
    )
    expression = _strict_json(expression_payload, "recognition input expression")
    if (
        expression.get("schema") != "glew.expression.closed_experience_field.v1"
        or expression.get("topology_authority_receipt_sha256")
        != topology.authority_receipt_sha256
        or expression.get("field_dimension") != topology.dimension
    ):
        raise ReceiptError("recognition input expression differs from topology")

    bank = recognition.pre_growth_bank
    if bank.rank < 2:
        return False, None, "bootstrap_requires_two_pre_growth_expression_modes", False
    if recognition.status is ExpressionRecognitionStatus.UNKNOWN:
        return False, None, "expression_recognition_unknown", True
    if recognition.status is ExpressionRecognitionStatus.AMBIGUOUS_SILENCE:
        return False, None, "expression_recognition_ambiguous", True
    if recognition.status is not ExpressionRecognitionStatus.RECOGNIZED:
        return False, None, f"expression_recognition_{recognition.status.value}", False

    winner = recognition.winner_mode_index
    if winner is None or winner < 0 or winner >= bank.rank:
        raise ReceiptError("recognized expression result does not name a pre-growth mode")
    probabilities = recognition.mode_probabilities
    if len(probabilities) != bank.rank:
        raise ReceiptError("expression recognition omitted a pre-growth probability")
    for index, (probability, mode) in enumerate(
        zip(probabilities, bank.modes, strict=True)
    ):
        if probability.mode_index != index or probability.mode_receipt_sha256 != (
            mode.receipt_sha256
        ):
            raise ReceiptError("expression probability names a different stable bank")
    if recognition.certified_residual_probability is None:
        raise ReceiptError("recognized expression result lacks residual probability")
    winner_lower, _ = _ball_bounds(
        probabilities[winner].certified_probability
    )
    residual_upper = _ball_bounds(
        recognition.certified_residual_probability
    )[1]
    other_uppers = tuple(
        _ball_bounds(value.certified_probability)[1]
        for index, value in enumerate(probabilities)
        if index != winner
    )
    if winner_lower <= residual_upper or any(
        winner_lower <= upper for upper in other_uppers
    ):
        raise ReceiptError("recognized expression mode lacks unique interval dominance")
    return True, winner, None, False


@dataclass(frozen=True, slots=True)
class _VerifiedCommitConjunction:
    topology: MountedFieldTopology
    recognition: ExpressionModeBoundaryResult
    l6_scope: L6ScopeAuthority
    closed_experience: ClosedExperienceSeal
    safe_mode: BinaryCommitAuthority
    event_support: EventSupportAuthority
    global_uf_validation: BinaryCommitAuthority | None
    evidence: tuple[PortTransportEvidence, ...]
    l5_applicability: tuple[L5Applicability, ...]
    winner_mode_index: int | None
    unknown_findings: tuple[str, ...]
    negative_findings: tuple[str, ...]

    @property
    def findings(self) -> tuple[str, ...]:
        return (*self.unknown_findings, *self.negative_findings)

    @property
    def selected_mode_receipt_sha256(self) -> str | None:
        if self.winner_mode_index is None:
            return None
        return self.recognition.pre_growth_bank.modes[
            self.winner_mode_index
        ].receipt_sha256


def _evaluate_verified_commit_conjunction(
    *,
    topology: MountedFieldTopology,
    recognition: ExpressionModeBoundaryResult,
    l6_evaluation: L6Evaluation,
    l6_scope: L6ScopeAuthority,
    closed_experience: ClosedExperienceSeal,
    safe_mode: BinaryCommitAuthority,
    event_support: EventSupportAuthority,
    evidence: tuple[PortTransportEvidence, ...],
    l5_applicability: tuple[L5Applicability, ...],
    global_uf_validation: BinaryCommitAuthority | None,
    receipt_registry: ReceiptRegistry,
) -> _VerifiedCommitConjunction:
    """Verify the one physical conjunction used by pending and final commit."""

    if not isinstance(topology, MountedFieldTopology):
        raise ReceiptError("commit boundary requires a mounted topology")
    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("commit boundary requires an immutable registry")
    if not isinstance(evidence, tuple) or not all(
        isinstance(value, PortTransportEvidence) for value in evidence
    ):
        raise ReceiptError("commit evidence must be an immutable typed tuple")
    if not isinstance(l5_applicability, tuple) or not all(
        isinstance(value, L5Applicability) for value in l5_applicability
    ):
        raise ReceiptError("L5 applicability must be an immutable typed tuple")
    if global_uf_validation is not None and not isinstance(
        global_uf_validation,
        BinaryCommitAuthority,
    ):
        raise ReceiptError("Global-UF authority must be typed or explicitly pending")

    topology.verify(receipt_registry)
    recognition_ok, winner, recognition_finding, recognition_unknown = (
        _verify_expression_recognition(
            topology=topology,
            recognition=recognition,
            receipt_registry=receipt_registry,
        )
    )
    closed_experience.verify(
        topology=topology,
        recognition=recognition,
        evidence=evidence,
        receipt_registry=receipt_registry,
    )
    experience_receipt = closed_experience.authority_receipt_sha256
    topology_receipt = topology.authority_receipt_sha256
    safe_mode.verify(
        expected_kind=BinaryAuthorityKind.SAFE_MODE_CLEAR,
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        receipt_registry=receipt_registry,
    )
    if global_uf_validation is not None:
        global_uf_validation.verify(
            expected_kind=BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
            topology_receipt=topology_receipt,
            experience_receipt=experience_receipt,
            receipt_registry=receipt_registry,
        )
    event_support.verify(
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        receipt_registry=receipt_registry,
    )
    _verify_l6_internal(l6_evaluation)
    l6_scope.verify(
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        evaluation=l6_evaluation,
        receipt_registry=receipt_registry,
    )

    unknown: list[str] = []
    negative: list[str] = []
    if safe_mode.disposition is AuthorityDisposition.UNKNOWN:
        unknown.append("safe_mode_unknown")
    elif safe_mode.disposition is AuthorityDisposition.FAIL:
        negative.append("safe_mode_active")
    if global_uf_validation is not None:
        if global_uf_validation.disposition is AuthorityDisposition.UNKNOWN:
            unknown.append("global_uf_validation_unknown")
        elif global_uf_validation.disposition is AuthorityDisposition.FAIL:
            negative.append("global_uf_validation_failed")
    if l6_evaluation.status is L6EvaluationStatus.UNKNOWN_NO_LOCK:
        unknown.append("fixed42_L6_unknown")
    elif l6_evaluation.status is L6EvaluationStatus.NO_LOCK:
        negative.append("fixed42_L6_no_lock")

    topology_keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
    evidence_keys = tuple(value.key for value in evidence)
    if set(evidence_keys) != set(topology_keys):
        unknown.append("typed_evidence_does_not_cover_mounted_topology")
    seen_evidence: set[str] = set()
    for value in evidence:
        value.verify(receipt_registry)
        if value.evidence_receipt_sha256 in seen_evidence:
            raise ReceiptError("closed experience repeats typed evidence")
        seen_evidence.add(value.evidence_receipt_sha256)
        if not (
            closed_experience.source_time_start
            <= value.provenance.source_timestamp
            <= closed_experience.source_time_end
        ):
            raise ReceiptError("typed evidence lies outside closed experience")
        if value.validity.state is EvidenceValidityState.UNKNOWN:
            unknown.append(f"evidence_unknown:{value.lane_id}:{value.port_id}")
        elif value.validity.state is EvidenceValidityState.INVALID:
            negative.append(f"evidence_invalid:{value.lane_id}:{value.port_id}")

    expected_applicability_keys = tuple(
        (fiber.lane_id, fiber.port_id, fact)
        for fiber in topology.ordered_port_fibers
        for fact in (GovernedFact.S_UF, GovernedFact.R_UF)
    )
    actual_applicability_keys = tuple(
        value.key for value in l5_applicability
    )
    if actual_applicability_keys != expected_applicability_keys:
        raise ReceiptError(
            "L5 applicability must cover topology ports in canonical fact order"
        )
    evidence_by_key: dict[
        tuple[str, str],
        list[PortTransportEvidence],
    ] = {}
    for value in evidence:
        evidence_by_key.setdefault(value.key, []).append(value)
    for applicability in l5_applicability:
        applicability.verify(
            topology_receipt=topology_receipt,
            experience_receipt=experience_receipt,
            receipt_registry=receipt_registry,
        )
        if applicability.state is ApplicabilityState.UNKNOWN:
            unknown.append(
                f"L5_applicability_unknown:{applicability.lane_id}:"
                f"{applicability.port_id}:{applicability.fact.value}"
            )
            continue
        if applicability.state is ApplicabilityState.NOT_APPLICABLE:
            continue
        records = evidence_by_key.get(
            (applicability.lane_id, applicability.port_id),
            [],
        )
        for record in records:
            state = (
                record.support_floor.state
                if applicability.fact is GovernedFact.S_UF
                else record.resonance.state
            )
            if state is not StructuralFactState.AVAILABLE:
                unknown.append(
                    f"required_{applicability.fact.value}_unavailable:"
                    f"{applicability.lane_id}:{applicability.port_id}"
                )

    if recognition_finding is not None:
        if recognition_unknown:
            unknown.append(recognition_finding)
        else:
            negative.append(recognition_finding)
    if not recognition_ok:
        winner = None
    if not unknown and not negative and winner is None:
        raise ReceiptError(
            "commit conjunction passed without a recognized mode"
        )
    return _VerifiedCommitConjunction(
        topology=topology,
        recognition=recognition,
        l6_scope=l6_scope,
        closed_experience=closed_experience,
        safe_mode=safe_mode,
        event_support=event_support,
        global_uf_validation=global_uf_validation,
        evidence=evidence,
        l5_applicability=l5_applicability,
        winner_mode_index=winner,
        unknown_findings=tuple(unknown),
        negative_findings=tuple(negative),
    )


def _make_pending_global_uf_conjunction(
    conjunction: _VerifiedCommitConjunction,
) -> PendingGlobalUFConjunction:
    if conjunction.global_uf_validation is not None:
        raise ReceiptError(
            "pending conjunction cannot carry a Global-UF authority"
        )
    if conjunction.unknown_findings:
        status = PendingGlobalUFStatus.UNKNOWN
    elif conjunction.negative_findings:
        status = PendingGlobalUFStatus.NO_COMMIT
    else:
        status = PendingGlobalUFStatus.READY_EXCEPT_GLOBAL_UF
    ready = status is PendingGlobalUFStatus.READY_EXCEPT_GLOBAL_UF
    winner = conjunction.winner_mode_index if ready else None
    selected = (
        conjunction.selected_mode_receipt_sha256 if ready else None
    )
    evidence_receipts = tuple(
        value.evidence_receipt_sha256 for value in conjunction.evidence
    )
    applicability_receipts = tuple(
        value.authority_receipt_sha256
        for value in conjunction.l5_applicability
    )
    payload = _pending_global_uf_payload(
        status=status,
        selected_mode_index=winner,
        selected_mode_receipt_sha256=selected,
        findings=conjunction.findings,
        topology_receipt=(
            conjunction.topology.authority_receipt_sha256
        ),
        experience_receipt=(
            conjunction.closed_experience.authority_receipt_sha256
        ),
        expression_recognition_receipt=(
            conjunction.recognition.receipt_sha256
        ),
        pre_growth_expression_bank_receipt=(
            conjunction.recognition.pre_growth_bank.receipt_sha256
        ),
        l6_evaluation_receipt=(
            conjunction.l6_scope.l6_evaluation_receipt_sha256
        ),
        safe_mode_receipt=(
            conjunction.safe_mode.authority_receipt_sha256
        ),
        event_support_receipt=(
            conjunction.event_support.authority_receipt_sha256
        ),
        evidence_receipts=evidence_receipts,
        applicability_receipts=applicability_receipts,
    )
    result = PendingGlobalUFConjunction(
        status=status,
        selected_mode_index=winner,
        selected_mode_receipt_sha256=selected,
        findings=conjunction.findings,
        topology_authority_receipt_sha256=(
            conjunction.topology.authority_receipt_sha256
        ),
        closed_experience_receipt_sha256=(
            conjunction.closed_experience.authority_receipt_sha256
        ),
        expression_recognition_receipt_sha256=(
            conjunction.recognition.receipt_sha256
        ),
        pre_growth_expression_bank_receipt_sha256=(
            conjunction.recognition.pre_growth_bank.receipt_sha256
        ),
        l6_evaluation_receipt_sha256=(
            conjunction.l6_scope.l6_evaluation_receipt_sha256
        ),
        safe_mode_receipt_sha256=(
            conjunction.safe_mode.authority_receipt_sha256
        ),
        event_support_receipt_sha256=(
            conjunction.event_support.authority_receipt_sha256
        ),
        evidence_receipt_sha256s=evidence_receipts,
        applicability_receipt_sha256s=applicability_receipts,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    result.verify()
    return result


def _make_decision(
    conjunction: _VerifiedCommitConjunction,
) -> CommitDecision:
    global_uf = conjunction.global_uf_validation
    if global_uf is None:
        raise ReceiptError("final commit requires Global-UF authority")
    if conjunction.unknown_findings:
        status = CommitStatus.UNKNOWN_NO_COMMIT
    elif conjunction.negative_findings:
        status = CommitStatus.NO_COMMIT
    else:
        status = CommitStatus.COMMIT
    committed = status is CommitStatus.COMMIT
    winner = conjunction.winner_mode_index if committed else None
    selected = (
        conjunction.selected_mode_receipt_sha256 if committed else None
    )
    evidence_receipts = tuple(
        value.evidence_receipt_sha256 for value in conjunction.evidence
    )
    applicability_receipts = tuple(
        value.authority_receipt_sha256
        for value in conjunction.l5_applicability
    )
    payload = _decision_payload(
        status=status,
        selected_mode_index=winner,
        selected_mode_receipt_sha256=selected,
        findings=conjunction.findings,
        topology_receipt=(
            conjunction.topology.authority_receipt_sha256
        ),
        experience_receipt=(
            conjunction.closed_experience.authority_receipt_sha256
        ),
        expression_recognition_receipt=(
            conjunction.recognition.receipt_sha256
        ),
        pre_growth_expression_bank_receipt=(
            conjunction.recognition.pre_growth_bank.receipt_sha256
        ),
        l6_evaluation_receipt=(
            conjunction.l6_scope.l6_evaluation_receipt_sha256
        ),
        safe_mode_receipt=(
            conjunction.safe_mode.authority_receipt_sha256
        ),
        event_support_receipt=(
            conjunction.event_support.authority_receipt_sha256
        ),
        global_uf_receipt=global_uf.authority_receipt_sha256,
        evidence_receipts=evidence_receipts,
        applicability_receipts=applicability_receipts,
    )
    result = CommitDecision(
        status=status,
        selected_mode_index=winner,
        selected_mode_receipt_sha256=selected,
        findings=conjunction.findings,
        topology_authority_receipt_sha256=(
            conjunction.topology.authority_receipt_sha256
        ),
        closed_experience_receipt_sha256=(
            conjunction.closed_experience.authority_receipt_sha256
        ),
        expression_recognition_receipt_sha256=(
            conjunction.recognition.receipt_sha256
        ),
        pre_growth_expression_bank_receipt_sha256=(
            conjunction.recognition.pre_growth_bank.receipt_sha256
        ),
        l6_evaluation_receipt_sha256=(
            conjunction.l6_scope.l6_evaluation_receipt_sha256
        ),
        safe_mode_receipt_sha256=(
            conjunction.safe_mode.authority_receipt_sha256
        ),
        event_support_receipt_sha256=(
            conjunction.event_support.authority_receipt_sha256
        ),
        global_uf_receipt_sha256=global_uf.authority_receipt_sha256,
        evidence_receipt_sha256s=evidence_receipts,
        applicability_receipt_sha256s=applicability_receipts,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    result.verify()
    return result


def evaluate_pending_global_uf_conjunction(
    *,
    topology: MountedFieldTopology,
    recognition: ExpressionModeBoundaryResult,
    l6_evaluation: L6Evaluation,
    l6_scope: L6ScopeAuthority,
    closed_experience: ClosedExperienceSeal,
    safe_mode: BinaryCommitAuthority,
    event_support: EventSupportAuthority,
    evidence: tuple[PortTransportEvidence, ...],
    l5_applicability: tuple[L5Applicability, ...],
    receipt_registry: ReceiptRegistry,
) -> PendingGlobalUFConjunction:
    """Evaluate every final commit fact except the recursively pending Global-UF."""

    conjunction = _evaluate_verified_commit_conjunction(
        topology=topology,
        recognition=recognition,
        l6_evaluation=l6_evaluation,
        l6_scope=l6_scope,
        closed_experience=closed_experience,
        safe_mode=safe_mode,
        event_support=event_support,
        evidence=evidence,
        l5_applicability=l5_applicability,
        global_uf_validation=None,
        receipt_registry=receipt_registry,
    )
    return _make_pending_global_uf_conjunction(conjunction)


def evaluate_commit_boundary(
    *,
    topology: MountedFieldTopology,
    recognition: ExpressionModeBoundaryResult,
    l6_evaluation: L6Evaluation,
    l6_scope: L6ScopeAuthority,
    closed_experience: ClosedExperienceSeal,
    safe_mode: BinaryCommitAuthority,
    event_support: EventSupportAuthority,
    evidence: tuple[PortTransportEvidence, ...],
    l5_applicability: tuple[L5Applicability, ...],
    global_uf_validation: BinaryCommitAuthority,
    receipt_registry: ReceiptRegistry,
) -> CommitDecision:
    """Run the same conjunction plus the final verified Global-UF authority.

    R_event is verified and retained in both pending and final receipts, but it
    is not an expression/output veto.  Its magnitude authorizes persistence at
    the separate origin-bound growth boundary.
    """

    conjunction = _evaluate_verified_commit_conjunction(
        topology=topology,
        recognition=recognition,
        l6_evaluation=l6_evaluation,
        l6_scope=l6_scope,
        closed_experience=closed_experience,
        safe_mode=safe_mode,
        event_support=event_support,
        evidence=evidence,
        l5_applicability=l5_applicability,
        global_uf_validation=global_uf_validation,
        receipt_registry=receipt_registry,
    )
    return _make_decision(conjunction)


__all__ = (
    "ApplicabilityState",
    "AuthorityDisposition",
    "BinaryAuthorityKind",
    "BinaryCommitAuthority",
    "COMMIT_OPERATOR_ID",
    "PENDING_GLOBAL_UF_OPERATOR_ID",
    "ClosedExperienceSeal",
    "CommitDecision",
    "CommitStatus",
    "EventSupportAuthority",
    "EventSupportState",
    "GovernedFact",
    "L5Applicability",
    "L6ScopeAuthority",
    "PendingGlobalUFConjunction",
    "PendingGlobalUFStatus",
    "binary_authority_receipt_payload",
    "closed_experience_seal_receipt_payload",
    "evaluate_commit_boundary",
    "evaluate_pending_global_uf_conjunction",
    "event_support_authority_receipt_payload",
    "l5_applicability_receipt_payload",
    "l6_evaluation_receipt_payload",
    "l6_scope_authority_receipt_payload",
)
