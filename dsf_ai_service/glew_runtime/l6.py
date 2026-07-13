"""Executable exact fixed-42 L6 constraint and lock boundary for GLEW.

Six canonical modality blocks each expose the seven frozen L4 DSF coordinates.
A signed native provider emits one or more exact seven-coefficient covectors in
that order.  Direct embedding places each covector in its modality block and
nowhere else.  Multiple native ports remain multiple rows; rows are never
averaged or reconstructed from DSF values.

The vertically stacked matrix is ranked once with exact ``Fraction`` Gaussian
elimination.  The capture comparison ``n_effective < 42/e`` is certified only
by python-flint 0.9.0 backed by FLINT 3.6.0 Arb in single-thread mode.  Missing
predicate evidence, mismatched rows, unavailable or mismatched Arb, and an
indeterminate interval proof all produce ``UNKNOWN_NO_LOCK``.
"""

from __future__ import annotations

import importlib
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from types import ModuleType
from typing import Final, Protocol, runtime_checkable


class L6Lane(str, Enum):
    """Canonical fixed order of the six GLEW modality blocks."""

    LANGUAGE = "language"
    SIGHT = "sight"
    SOUND = "sound"
    TOUCH = "touch"
    SMELL = "smell"
    TASTE = "taste"


class L4Field(str, Enum):
    """Canonical seven-coordinate L4 DSF field order within every lane."""

    D_K = "D_k"
    M_K = "M_k"
    R_REV_K = "R_rev_k"
    U_STAR_K = "U_star_k"
    C_K = "C_k"
    P_K = "P_k"
    B_K = "B_k"


LANE_ORDER: Final[tuple[L6Lane, ...]] = tuple(L6Lane)
FIELD_ORDER: Final[tuple[L4Field, ...]] = tuple(L4Field)
FIELDS_PER_LANE: Final[int] = len(FIELD_ORDER)
N_START: Final[int] = len(LANE_ORDER) * FIELDS_PER_LANE

PINNED_PYTHON_FLINT_VERSION: Final[str] = "0.9.0"
PINNED_FLINT_VERSION: Final[str] = "3.6.0"
_BACKEND_LIMB_BITS: Final[int] = 64
ARB_PRECISION_BITS: Final[int] = 1 << (
    (N_START.bit_length() + _BACKEND_LIMB_BITS - 1).bit_length()
)
ROW_RECEIPT_FIELD: Final[str] = "glew_l6_row_receipt_v1"
COMPLETENESS_RECEIPT_FIELD: Final[str] = "glew_l6_completeness_receipt_v1"


def fixed42_column(lane: L6Lane, field_name: L4Field) -> int:
    """Return the canonical zero-based column for a lane and L4 field."""

    if not isinstance(lane, L6Lane):
        raise TypeError("lane must be an L6Lane")
    if not isinstance(field_name, L4Field):
        raise TypeError("field_name must be an L4Field")
    return LANE_ORDER.index(lane) * FIELDS_PER_LANE + FIELD_ORDER.index(field_name)


def _require_identifier(name: str, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value or value != value.strip() or "\x00" in value:
        raise ValueError(f"{name} must be a nonempty canonical identifier")


def _require_sha256(name: str, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if len(value) != 64 or value != value.lower():
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    try:
        decoded = bytes.fromhex(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest") from error
    if len(decoded) != 32:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _require_fraction(value: object, *, coordinate: int) -> Fraction:
    if not isinstance(value, Fraction):
        raise TypeError(
            f"covector coefficient at coordinate {coordinate} must be a "
            "Fraction; implicit coercion and floating point are forbidden"
        )
    return value


def _canonical_receipt_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_row_receipt_payload(
    *,
    lane: L6Lane,
    provider_id: str,
    native_port_id: str,
    operator_id: str,
    row_id: str,
    coefficients: tuple[Fraction, ...],
) -> bytes:
    """Encode the immutable mounted receipt payload for one native row."""

    if not isinstance(lane, L6Lane):
        raise TypeError("lane must be an L6Lane")
    for name, value in (
        ("provider_id", provider_id),
        ("native_port_id", native_port_id),
        ("operator_id", operator_id),
        ("row_id", row_id),
    ):
        _require_identifier(name, value)
    if not isinstance(coefficients, tuple) or len(coefficients) != FIELDS_PER_LANE:
        raise ValueError("row receipt requires exactly seven coefficients")
    exact = tuple(
        _require_fraction(value, coordinate=coordinate)
        for coordinate, value in enumerate(coefficients)
    )
    return _canonical_receipt_bytes(
        {
            "coefficients": [
                [str(value.numerator), str(value.denominator)] for value in exact
            ],
            "field_order": [field_name.value for field_name in FIELD_ORDER],
            "lane": lane.value,
            "native_port_id": native_port_id,
            "operator_id": operator_id,
            "provider_id": provider_id,
            "row_id": row_id,
            "schema": ROW_RECEIPT_FIELD,
        }
    )


def canonical_completeness_receipt_payload(
    *, lane: L6Lane, row_receipt_sha256s: tuple[str, ...]
) -> bytes:
    """Encode one lane's complete canonical set of mounted nonzero rows."""

    if not isinstance(lane, L6Lane):
        raise TypeError("lane must be an L6Lane")
    if not isinstance(row_receipt_sha256s, tuple):
        raise TypeError("row_receipt_sha256s must be an immutable tuple")
    for digest in row_receipt_sha256s:
        _require_sha256("row_receipt_sha256", digest)
    if len(set(row_receipt_sha256s)) != len(row_receipt_sha256s):
        raise ValueError("a completeness receipt cannot repeat a row digest")
    ordered = tuple(sorted(row_receipt_sha256s))
    return _canonical_receipt_bytes(
        {
            "lane": lane.value,
            "row_receipt_sha256s": list(ordered),
            "schema": COMPLETENESS_RECEIPT_FIELD,
        }
    )


def receipt_sha256(payload: bytes) -> str:
    """Return the content address of exact immutable receipt bytes."""

    if not isinstance(payload, bytes):
        raise TypeError("receipt payload must be immutable bytes")
    return hashlib.sha256(payload).hexdigest()


@runtime_checkable
class MountedReceiptRegistry(Protocol):
    """Read-only boundary to the immutable receipts mounted for this weave."""

    def resolve(self, digest: str, field_name: str) -> bytes | None:
        """Resolve exact canonical bytes, or ``None`` when not mounted."""


@dataclass(frozen=True)
class ConstraintRowProvenance:
    """Identity retained from one signed provider's native output row."""

    lane: L6Lane
    provider_id: str
    native_port_id: str
    operator_id: str
    receipt_sha256: str
    row_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.lane, L6Lane):
            raise TypeError("lane must be an L6Lane")
        for name in (
            "provider_id",
            "native_port_id",
            "operator_id",
            "row_id",
        ):
            _require_identifier(name, getattr(self, name))
        _require_sha256("receipt_sha256", self.receipt_sha256)

    @property
    def identity(self) -> tuple[str, str, str, str, str, str]:
        """Return the complete non-hash identity for duplicate rejection."""

        return (
            self.lane.value,
            self.provider_id,
            self.native_port_id,
            self.operator_id,
            self.receipt_sha256,
            self.row_id,
        )


@dataclass(frozen=True)
class NativeConstraintCovector:
    """One provider-emitted exact covector in canonical seven-field order."""

    provenance: ConstraintRowProvenance
    coefficients: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, ConstraintRowProvenance):
            raise TypeError("provenance must be ConstraintRowProvenance")
        if not isinstance(self.coefficients, tuple):
            raise TypeError("coefficients must be an immutable tuple")
        if len(self.coefficients) != FIELDS_PER_LANE:
            raise ValueError(
                f"native constraint covector must contain {FIELDS_PER_LANE} "
                "canonical L4 coefficients"
            )
        exact = tuple(
            _require_fraction(value, coordinate=coordinate)
            for coordinate, value in enumerate(self.coefficients)
        )
        if not any(exact):
            raise ValueError("a zero covector is not a constraint row")


@dataclass(frozen=True)
class ConstraintRow:
    """A native covector embedded directly into its fixed seven-column block."""

    source: NativeConstraintCovector
    coefficients: tuple[Fraction, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source, NativeConstraintCovector):
            raise TypeError("source must be a NativeConstraintCovector")
        block_start = (
            LANE_ORDER.index(self.source.provenance.lane) * FIELDS_PER_LANE
        )
        embedded = [Fraction(0) for _ in range(N_START)]
        embedded[block_start : block_start + FIELDS_PER_LANE] = (
            self.source.coefficients
        )
        object.__setattr__(self, "coefficients", tuple(embedded))

    @property
    def provenance(self) -> ConstraintRowProvenance:
        return self.source.provenance

    @property
    def native_coefficients(self) -> tuple[Fraction, ...]:
        return self.source.coefficients


def embed_native_covector(covector: NativeConstraintCovector) -> ConstraintRow:
    """Directly embed one exact native covector without averaging or scoring."""

    if not isinstance(covector, NativeConstraintCovector):
        raise TypeError("covector must be a NativeConstraintCovector")
    return ConstraintRow(source=covector)


@dataclass(frozen=True)
class Fixed42ConstraintStack:
    """A vertical stack of separately preserved native constraint rows."""

    rows: tuple[ConstraintRow, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.rows, tuple):
            raise TypeError("rows must be an immutable tuple")
        if any(not isinstance(row, ConstraintRow) for row in self.rows):
            raise TypeError("every stack member must be a ConstraintRow")

        identities = tuple(row.provenance.identity for row in self.rows)
        if len(set(identities)) != len(identities):
            raise ValueError("duplicate constraint-row provenance is forbidden")


@dataclass(frozen=True)
class ExactRankReceipt:
    """Exact one-matrix rank evidence for a fixed-42 row stack."""

    n_start: int
    row_count: int
    rank: int
    n_effective: int
    pivot_columns: tuple[int, ...]

    @property
    def matrix_shape(self) -> tuple[int, int]:
        return (self.row_count, self.n_start)


def exact_rank_receipt(stack: Fixed42ConstraintStack) -> ExactRankReceipt:
    """Compute one exact rank over the vertically stacked rows."""

    if not isinstance(stack, Fixed42ConstraintStack):
        raise TypeError("stack must be a Fixed42ConstraintStack")

    matrix = [list(row.coefficients) for row in stack.rows]
    pivot_row = 0
    pivot_columns: list[int] = []

    for column in range(N_START):
        selected = next(
            (
                row_index
                for row_index in range(pivot_row, len(matrix))
                if matrix[row_index][column] != 0
            ),
            None,
        )
        if selected is None:
            continue

        matrix[pivot_row], matrix[selected] = matrix[selected], matrix[pivot_row]
        pivot = matrix[pivot_row][column]
        matrix[pivot_row] = [value / pivot for value in matrix[pivot_row]]

        for row_index in range(pivot_row + 1, len(matrix)):
            factor = matrix[row_index][column]
            if factor == 0:
                continue
            matrix[row_index] = [
                value - factor * pivot_value
                for value, pivot_value in zip(
                    matrix[row_index], matrix[pivot_row], strict=True
                )
            ]

        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break

    rank = len(pivot_columns)
    return ExactRankReceipt(
        n_start=N_START,
        row_count=len(stack.rows),
        rank=rank,
        n_effective=N_START - rank,
        pivot_columns=tuple(pivot_columns),
    )


@dataclass(frozen=True)
class ActiveLaneState:
    """One valid active lane and its exact L4 uncertainty value."""

    lane: L6Lane
    u_star: Fraction | None
    constraint_set_complete: bool | None
    constraint_set_receipt_sha256: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.lane, L6Lane):
            raise TypeError("lane must be an L6Lane")
        if self.u_star is not None and not isinstance(self.u_star, Fraction):
            raise TypeError("u_star must be a Fraction or explicit None")
        if self.constraint_set_complete is not None and not isinstance(
            self.constraint_set_complete, bool
        ):
            raise TypeError("constraint_set_complete must be bool or explicit None")
        if self.constraint_set_receipt_sha256 is not None:
            _require_sha256(
                "constraint_set_receipt_sha256",
                self.constraint_set_receipt_sha256,
            )


@dataclass(frozen=True)
class L6PredicateInputs:
    """Complete external predicates required by the corrected lock."""

    active_lanes: tuple[ActiveLaneState, ...] | None
    disruption_clear: bool | None

    def __post_init__(self) -> None:
        if self.active_lanes is not None:
            if not isinstance(self.active_lanes, tuple):
                raise TypeError("active_lanes must be an immutable tuple or None")
            if any(
                not isinstance(lane_state, ActiveLaneState)
                for lane_state in self.active_lanes
            ):
                raise TypeError("every active lane must be an ActiveLaneState")
        if self.disruption_clear is not None and not isinstance(
            self.disruption_clear, bool
        ):
            raise TypeError("disruption_clear must be bool or explicit None")


@dataclass(frozen=True)
class ArbCaptureProof:
    """Pinned-backend interval proof for the geometric capture comparison."""

    python_flint_version: str
    flint_version: str
    threads: int
    precision_bits: int
    expression: str
    threshold_ball: str
    n_effective: int
    below_threshold: bool


class L6EvaluationStatus(str, Enum):
    """Three-valued corrected L6 disposition."""

    LOCK = "lock"
    NO_LOCK = "no_lock"
    UNKNOWN_NO_LOCK = "unknown_no_lock"


@dataclass(frozen=True)
class L6Evaluation:
    """Corrected L6 result with exact rank and optional Arb proof receipt."""

    status: L6EvaluationStatus
    structural_lock: bool | None
    rank_receipt: ExactRankReceipt
    omega: Fraction | None
    arb_proof: ArbCaptureProof | None
    reason: str


def _import_flint() -> ModuleType:
    return importlib.import_module("flint")


def _arb_capture_proof(
    n_effective: int,
) -> tuple[ArbCaptureProof | None, str | None]:
    try:
        flint = _import_flint()
    except ModuleNotFoundError as exc:
        if exc.name != "flint":
            raise
        return None, "python-flint is unavailable"

    python_flint_version = getattr(flint, "__version__", None)
    flint_version = getattr(flint, "__FLINT_VERSION__", None)
    if python_flint_version != PINNED_PYTHON_FLINT_VERSION:
        return (
            None,
            "python-flint version mismatch: expected "
            f"{PINNED_PYTHON_FLINT_VERSION}, received {python_flint_version!r}",
        )
    if flint_version != PINNED_FLINT_VERSION:
        return (
            None,
            "FLINT version mismatch: expected "
            f"{PINNED_FLINT_VERSION}, received {flint_version!r}",
        )

    threads = getattr(flint.ctx, "threads", None)
    if threads != 1:
        return None, f"FLINT thread mismatch: expected 1, received {threads!r}"

    with flint.ctx.workprec(ARB_PRECISION_BITS):
        threshold = flint.arb(N_START) / flint.arb(1).exp()
        candidate = flint.arb(n_effective)
        if not threshold.is_finite() or not candidate.is_finite():
            return None, "Arb produced a nonfinite capture comparison"
        below = candidate < threshold
        above = threshold < candidate
        if below == above:
            return None, "Arb capture comparison is indeterminate"
        proof = ArbCaptureProof(
            python_flint_version=python_flint_version,
            flint_version=flint_version,
            threads=threads,
            precision_bits=ARB_PRECISION_BITS,
            expression="n_effective < 42/exp(1)",
            threshold_ball=threshold.str(40),
            n_effective=n_effective,
            below_threshold=below,
        )
    return proof, None


def _result(
    *,
    status: L6EvaluationStatus,
    rank_receipt: ExactRankReceipt,
    reason: str,
    arb_proof: ArbCaptureProof | None = None,
    recovery_factor: int | None = None,
) -> L6Evaluation:
    structural_lock: bool | None
    if status is L6EvaluationStatus.LOCK:
        structural_lock = True
    elif status is L6EvaluationStatus.NO_LOCK:
        structural_lock = False
    else:
        structural_lock = None
    if recovery_factor not in (None, 0, 1):
        raise ValueError("recovery_factor must be exactly zero, one, or unknown")
    omega = (
        None
        if recovery_factor is None
        else Fraction(rank_receipt.rank * recovery_factor, N_START)
    )
    return L6Evaluation(
        status=status,
        structural_lock=structural_lock,
        rank_receipt=rank_receipt,
        omega=omega,
        arb_proof=arb_proof,
        reason=reason,
    )


def _mounted_payload_failure(
    registry: MountedReceiptRegistry,
    *,
    digest: str,
    field_name: str,
    expected_payload: bytes,
) -> str | None:
    mounted = registry.resolve(digest, field_name)
    if mounted is None:
        return f"{field_name} {digest} is not mounted"
    if not isinstance(mounted, bytes):
        return f"{field_name} {digest} is not immutable bytes"
    if receipt_sha256(mounted) != digest:
        return f"mounted {field_name} bytes do not match digest {digest}"
    if mounted != expected_payload:
        return f"mounted {field_name} payload does not match the active field"
    return None


def _receipt_authority_failure(
    stack: Fixed42ConstraintStack,
    lane_states: tuple[ActiveLaneState, ...],
    registry: MountedReceiptRegistry | None,
) -> str | None:
    if registry is None or not isinstance(registry, MountedReceiptRegistry):
        return "immutable mounted receipt registry is missing"

    for row in stack.rows:
        provenance = row.provenance
        expected_payload = canonical_row_receipt_payload(
            lane=provenance.lane,
            provider_id=provenance.provider_id,
            native_port_id=provenance.native_port_id,
            operator_id=provenance.operator_id,
            row_id=provenance.row_id,
            coefficients=row.native_coefficients,
        )
        expected_digest = receipt_sha256(expected_payload)
        if provenance.receipt_sha256 != expected_digest:
            return (
                "constraint row fields do not match provenance receipt SHA-256 "
                f"{provenance.receipt_sha256}"
            )
        mounted_failure = _mounted_payload_failure(
            registry,
            digest=provenance.receipt_sha256,
            field_name=ROW_RECEIPT_FIELD,
            expected_payload=expected_payload,
        )
        if mounted_failure is not None:
            return mounted_failure

    for lane_state in lane_states:
        completeness_digest = lane_state.constraint_set_receipt_sha256
        if completeness_digest is None:
            return "an active lane constraint-set completeness receipt is missing"
        row_digests = tuple(
            row.provenance.receipt_sha256
            for row in stack.rows
            if row.provenance.lane is lane_state.lane
        )
        expected_payload = canonical_completeness_receipt_payload(
            lane=lane_state.lane,
            row_receipt_sha256s=row_digests,
        )
        expected_digest = receipt_sha256(expected_payload)
        if completeness_digest != expected_digest:
            return (
                f"{lane_state.lane.value} completeness receipt does not bind "
                "the exact active row set"
            )
        mounted_failure = _mounted_payload_failure(
            registry,
            digest=completeness_digest,
            field_name=COMPLETENESS_RECEIPT_FIELD,
            expected_payload=expected_payload,
        )
        if mounted_failure is not None:
            return mounted_failure

    return None


def evaluate_l6(
    stack: Fixed42ConstraintStack,
    predicates: L6PredicateInputs | None = None,
    receipt_registry: MountedReceiptRegistry | None = None,
) -> L6Evaluation:
    """Evaluate the corrected fixed-42 lock, failing closed on unknowns."""

    rank_receipt = exact_rank_receipt(stack)
    if predicates is None:
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="L6 predicate inputs are missing",
        )
    if not isinstance(predicates, L6PredicateInputs):
        raise TypeError("predicates must be L6PredicateInputs or None")
    if predicates.active_lanes is None:
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="active lane evidence is missing",
        )
    if predicates.disruption_clear is None:
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="disruption state is missing",
        )

    lane_states = predicates.active_lanes
    active_lane_ids = tuple(state.lane for state in lane_states)
    if len(set(active_lane_ids)) != len(active_lane_ids):
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="active lane evidence contains duplicate lanes",
        )
    if active_lane_ids != tuple(
        lane for lane in LANE_ORDER if lane in set(active_lane_ids)
    ):
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="active lane evidence is not in canonical lane order",
        )
    if any(state.u_star is None for state in lane_states):
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="an active lane U_star value is missing",
        )
    if any(
        state.constraint_set_complete is None
        or state.constraint_set_receipt_sha256 is None
        for state in lane_states
    ):
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="an active lane constraint-set completeness receipt is missing",
        )
    if any(not state.constraint_set_complete for state in lane_states):
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="an active lane native constraint set is incomplete",
        )

    row_lane_ids = {row.provenance.lane for row in stack.rows}
    active_lane_set = set(active_lane_ids)
    if not row_lane_ids.issubset(active_lane_set):
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="a constraint row belongs to a lane that is not active",
            recovery_factor=int(predicates.disruption_clear),
        )

    authority_failure = _receipt_authority_failure(
        stack, lane_states, receipt_registry
    )
    if authority_failure is not None:
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason=authority_failure,
            recovery_factor=int(predicates.disruption_clear),
        )
    if len(active_lane_ids) < 4:
        return _result(
            status=L6EvaluationStatus.NO_LOCK,
            rank_receipt=rank_receipt,
            reason="fewer than four valid active lanes",
            recovery_factor=int(predicates.disruption_clear),
        )
    if any(state.u_star != 0 for state in lane_states):
        return _result(
            status=L6EvaluationStatus.NO_LOCK,
            rank_receipt=rank_receipt,
            reason="at least one active lane has nonzero U_star",
            recovery_factor=int(predicates.disruption_clear),
        )
    if not predicates.disruption_clear:
        return _result(
            status=L6EvaluationStatus.NO_LOCK,
            rank_receipt=rank_receipt,
            reason="the disruption latch is not clear",
            recovery_factor=0,
        )
    arb_proof, backend_failure = _arb_capture_proof(rank_receipt.n_effective)
    if arb_proof is None:
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason=backend_failure or "Arb proof unavailable",
            recovery_factor=1,
        )
    if not arb_proof.below_threshold:
        return _result(
            status=L6EvaluationStatus.NO_LOCK,
            rank_receipt=rank_receipt,
            arb_proof=arb_proof,
            reason="exact combined rank does not enter the geometric capture basin",
            recovery_factor=1,
        )
    return _result(
        status=L6EvaluationStatus.LOCK,
        rank_receipt=rank_receipt,
        arb_proof=arb_proof,
        reason="all corrected fixed-42 lock predicates are certified",
        recovery_factor=1,
    )


__all__ = [
    "ARB_PRECISION_BITS",
    "COMPLETENESS_RECEIPT_FIELD",
    "ActiveLaneState",
    "ArbCaptureProof",
    "ConstraintRow",
    "ConstraintRowProvenance",
    "ExactRankReceipt",
    "FIELD_ORDER",
    "FIELDS_PER_LANE",
    "Fixed42ConstraintStack",
    "L4Field",
    "L6Evaluation",
    "L6EvaluationStatus",
    "L6Lane",
    "L6PredicateInputs",
    "LANE_ORDER",
    "MountedReceiptRegistry",
    "N_START",
    "NativeConstraintCovector",
    "PINNED_FLINT_VERSION",
    "PINNED_PYTHON_FLINT_VERSION",
    "ROW_RECEIPT_FIELD",
    "canonical_completeness_receipt_payload",
    "canonical_row_receipt_payload",
    "embed_native_covector",
    "evaluate_l6",
    "exact_rank_receipt",
    "fixed42_column",
    "receipt_sha256",
]
