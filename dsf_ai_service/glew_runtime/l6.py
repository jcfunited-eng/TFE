"""Exact fixed-42 L6 constraint mechanics and physical tangent candidate.

Six canonical modality blocks each expose all seven frozen L4 DSF fields.
Provider-native covectors are embedded only in their own lane block and the
complete matrix is ranked with exact Fraction elimination.

The candidate physical producer in this module accepts only a mounted exact
local response tangent with a mounted same-branch/cell authority.  Its rows
are the canonical exact left-nullspace basis of that tangent.  It never
derives rows from observed DSF values, kernel self-equations, hashes, buckets,
thresholds, numerical decompositions, or a desired lock result.  It is not
live authority unless real providers mount those inputs.

U_star remains one of the seven fields and may participate in receipted rows
and the joint full-field expression.  It is deliberately not a standalone L6
veto.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from types import ModuleType
from typing import Final, Protocol, runtime_checkable


class L6Lane(str, Enum):
    LANGUAGE = "language"
    SIGHT = "sight"
    SOUND = "sound"
    TOUCH = "touch"
    SMELL = "smell"
    TASTE = "taste"


class L4Field(str, Enum):
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
CANDIDATE_BRANCH_CELL_RECEIPT_FIELD: Final[str] = (
    "glew_l6_candidate_same_branch_cell_authority_v1"
)
CANDIDATE_LOCAL_TANGENT_RECEIPT_FIELD: Final[str] = (
    "glew_l6_candidate_local_response_tangent_v1"
)
CANDIDATE_LEFT_NULLSPACE_OPERATOR_ID: Final[str] = (
    "candidate-exact-provider-left-nullspace-v1"
)


def fixed42_column(lane: L6Lane, field_name: L4Field) -> int:
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
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    try:
        decoded = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest") from exc
    if len(decoded) != 32:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _require_fraction(value: object, *, coordinate: int) -> Fraction:
    if not isinstance(value, Fraction):
        raise TypeError(
            f"covector coefficient at coordinate {coordinate} must be a Fraction"
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


def receipt_sha256(payload: bytes) -> str:
    if not isinstance(payload, bytes):
        raise TypeError("receipt payload must be immutable bytes")
    return hashlib.sha256(payload).hexdigest()


def canonical_row_receipt_payload(
    *,
    lane: L6Lane,
    provider_id: str,
    native_port_id: str,
    operator_id: str,
    row_id: str,
    coefficients: tuple[Fraction, ...],
) -> bytes:
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
        _require_fraction(value, coordinate=index)
        for index, value in enumerate(coefficients)
    )
    return _canonical_receipt_bytes(
        {
            "coefficients": [
                [str(value.numerator), str(value.denominator)] for value in exact
            ],
            "field_order": [value.value for value in FIELD_ORDER],
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
    if not isinstance(lane, L6Lane):
        raise TypeError("lane must be an L6Lane")
    if not isinstance(row_receipt_sha256s, tuple):
        raise TypeError("row_receipt_sha256s must be an immutable tuple")
    for digest in row_receipt_sha256s:
        _require_sha256("row_receipt_sha256", digest)
    if len(set(row_receipt_sha256s)) != len(row_receipt_sha256s):
        raise ValueError("a completeness receipt cannot repeat a row digest")
    return _canonical_receipt_bytes(
        {
            "lane": lane.value,
            "row_receipt_sha256s": list(sorted(row_receipt_sha256s)),
            "schema": COMPLETENESS_RECEIPT_FIELD,
        }
    )


def _validate_candidate_tangent(
    perturbation_coordinate_ids: object,
    tangent: object,
) -> tuple[tuple[str, ...], tuple[tuple[Fraction, ...], ...]]:
    if not isinstance(perturbation_coordinate_ids, tuple):
        raise TypeError(
            "perturbation_coordinate_ids must be an immutable nonempty tuple"
        )
    if not perturbation_coordinate_ids:
        raise ValueError("at least one native physical perturbation is required")
    for coordinate_id in perturbation_coordinate_ids:
        _require_identifier("perturbation_coordinate_id", coordinate_id)
    if len(set(perturbation_coordinate_ids)) != len(perturbation_coordinate_ids):
        raise ValueError("native physical perturbation coordinates must be unique")

    if not isinstance(tangent, tuple):
        raise TypeError("local response tangent must be an immutable tuple")
    if len(tangent) != FIELDS_PER_LANE:
        raise ValueError("local response tangent must have seven DSF output rows")
    exact_rows: list[tuple[Fraction, ...]] = []
    for field_index, row in enumerate(tangent):
        if not isinstance(row, tuple):
            raise TypeError(
                f"local response tangent row {field_index} is not immutable"
            )
        if len(row) != len(perturbation_coordinate_ids):
            raise ValueError(
                "every local response tangent row must cover every declared "
                "physical perturbation coordinate"
            )
        exact_row: list[Fraction] = []
        for perturbation_index, value in enumerate(row):
            if not isinstance(value, Fraction):
                raise TypeError(
                    "local response tangent coefficient "
                    f"({field_index}, {perturbation_index}) must be a Fraction"
                )
            exact_row.append(value)
        exact_rows.append(tuple(exact_row))
    return perturbation_coordinate_ids, tuple(exact_rows)


def canonical_candidate_branch_cell_receipt_payload(
    *,
    lane: L6Lane,
    provider_id: str,
    native_port_id: str,
    branch_id: str,
    cell_id: str,
) -> bytes:
    """Encode the candidate proof that one tangent stays in one physical cell."""

    if not isinstance(lane, L6Lane):
        raise TypeError("lane must be an L6Lane")
    for name, value in (
        ("provider_id", provider_id),
        ("native_port_id", native_port_id),
        ("branch_id", branch_id),
        ("cell_id", cell_id),
    ):
        _require_identifier(name, value)
    return _canonical_receipt_bytes(
        {
            "branch_id": branch_id,
            "cell_id": cell_id,
            "field_order": [value.value for value in FIELD_ORDER],
            "lane": lane.value,
            "native_port_id": native_port_id,
            "provider_id": provider_id,
            "schema": CANDIDATE_BRANCH_CELL_RECEIPT_FIELD,
        }
    )


def canonical_candidate_local_tangent_receipt_payload(
    *,
    lane: L6Lane,
    provider_id: str,
    native_port_id: str,
    branch_id: str,
    cell_id: str,
    perturbation_coordinate_ids: tuple[str, ...],
    tangent: tuple[tuple[Fraction, ...], ...],
    branch_cell_receipt_sha256: str,
) -> bytes:
    """Encode one exact seven-by-native-perturbation candidate tangent."""

    if not isinstance(lane, L6Lane):
        raise TypeError("lane must be an L6Lane")
    for name, value in (
        ("provider_id", provider_id),
        ("native_port_id", native_port_id),
        ("branch_id", branch_id),
        ("cell_id", cell_id),
    ):
        _require_identifier(name, value)
    _require_sha256(
        "branch_cell_receipt_sha256",
        branch_cell_receipt_sha256,
    )
    coordinate_ids, exact_tangent = _validate_candidate_tangent(
        perturbation_coordinate_ids,
        tangent,
    )
    return _canonical_receipt_bytes(
        {
            "branch_cell_receipt_sha256": branch_cell_receipt_sha256,
            "branch_id": branch_id,
            "cell_id": cell_id,
            "field_order": [value.value for value in FIELD_ORDER],
            "lane": lane.value,
            "native_port_id": native_port_id,
            "orientation": "seven_dsf_outputs_by_native_physical_perturbations",
            "perturbation_coordinate_ids": list(coordinate_ids),
            "provider_id": provider_id,
            "schema": CANDIDATE_LOCAL_TANGENT_RECEIPT_FIELD,
            "tangent": [
                [
                    [str(value.numerator), str(value.denominator)]
                    for value in row
                ]
                for row in exact_tangent
            ],
        }
    )


@runtime_checkable
class MountedReceiptRegistry(Protocol):
    def resolve(self, digest: str, field_name: str) -> bytes | None:
        """Resolve exact canonical bytes, or None when not mounted."""


@dataclass(frozen=True)
class ConstraintRowProvenance:
    lane: L6Lane
    provider_id: str
    native_port_id: str
    operator_id: str
    receipt_sha256: str
    row_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.lane, L6Lane):
            raise TypeError("lane must be an L6Lane")
        for name in ("provider_id", "native_port_id", "operator_id", "row_id"):
            _require_identifier(name, getattr(self, name))
        _require_sha256("receipt_sha256", self.receipt_sha256)

    @property
    def identity(self) -> tuple[str, str, str, str, str, str]:
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
    provenance: ConstraintRowProvenance
    coefficients: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, ConstraintRowProvenance):
            raise TypeError("provenance must be ConstraintRowProvenance")
        if not isinstance(self.coefficients, tuple):
            raise TypeError("coefficients must be an immutable tuple")
        if len(self.coefficients) != FIELDS_PER_LANE:
            raise ValueError("native constraint covector must contain seven coefficients")
        exact = tuple(
            _require_fraction(value, coordinate=index)
            for index, value in enumerate(self.coefficients)
        )
        if not any(exact):
            raise ValueError("a zero covector is not a constraint row")


@dataclass(frozen=True)
class ConstraintRow:
    source: NativeConstraintCovector
    coefficients: tuple[Fraction, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source, NativeConstraintCovector):
            raise TypeError("source must be a NativeConstraintCovector")
        start = LANE_ORDER.index(self.source.provenance.lane) * FIELDS_PER_LANE
        embedded = [Fraction(0) for _ in range(N_START)]
        embedded[start : start + FIELDS_PER_LANE] = self.source.coefficients
        object.__setattr__(self, "coefficients", tuple(embedded))

    @property
    def provenance(self) -> ConstraintRowProvenance:
        return self.source.provenance

    @property
    def native_coefficients(self) -> tuple[Fraction, ...]:
        return self.source.coefficients


def embed_native_covector(covector: NativeConstraintCovector) -> ConstraintRow:
    if not isinstance(covector, NativeConstraintCovector):
        raise TypeError("covector must be a NativeConstraintCovector")
    return ConstraintRow(covector)


@dataclass(frozen=True)
class Fixed42ConstraintStack:
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
    n_start: int
    row_count: int
    rank: int
    n_effective: int
    pivot_columns: tuple[int, ...]

    @property
    def matrix_shape(self) -> tuple[int, int]:
        return (self.row_count, self.n_start)


def exact_rank_receipt(stack: Fixed42ConstraintStack) -> ExactRankReceipt:
    if not isinstance(stack, Fixed42ConstraintStack):
        raise TypeError("stack must be a Fixed42ConstraintStack")
    matrix = [list(row.coefficients) for row in stack.rows]
    pivot_row = 0
    pivots: list[int] = []
    for column in range(N_START):
        selected = next(
            (
                index
                for index in range(pivot_row, len(matrix))
                if matrix[index][column] != 0
            ),
            None,
        )
        if selected is None:
            continue
        matrix[pivot_row], matrix[selected] = matrix[selected], matrix[pivot_row]
        pivot = matrix[pivot_row][column]
        matrix[pivot_row] = [value / pivot for value in matrix[pivot_row]]
        for index in range(pivot_row + 1, len(matrix)):
            factor = matrix[index][column]
            if factor:
                matrix[index] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(
                        matrix[index], matrix[pivot_row], strict=True
                    )
                ]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    rank = len(pivots)
    return ExactRankReceipt(
        n_start=N_START,
        row_count=len(stack.rows),
        rank=rank,
        n_effective=N_START - rank,
        pivot_columns=tuple(pivots),
    )


def _canonical_primitive_covector(
    values: tuple[Fraction, ...],
) -> tuple[Fraction, ...]:
    if len(values) != FIELDS_PER_LANE:
        raise ValueError("candidate covector must contain seven coordinates")
    if not all(isinstance(value, Fraction) for value in values):
        raise TypeError("candidate covector coordinates must be exact Fractions")
    if not any(values):
        raise ValueError("a zero covector is not a constraint row")

    common_denominator = 1
    for value in values:
        common_denominator = math.lcm(common_denominator, value.denominator)
    integers = [
        value.numerator * (common_denominator // value.denominator)
        for value in values
    ]
    common_divisor = 0
    for value in integers:
        common_divisor = math.gcd(common_divisor, abs(value))
    primitive = [value // common_divisor for value in integers]
    first_nonzero = next(value for value in primitive if value)
    if first_nonzero < 0:
        primitive = [-value for value in primitive]
    return tuple(Fraction(value) for value in primitive)


def candidate_exact_left_nullspace_basis(
    tangent: tuple[tuple[Fraction, ...], ...],
) -> tuple[tuple[Fraction, ...], ...]:
    """Return the canonical exact basis of ker(J transpose).

    J is seven DSF output rows by one or more native physical perturbation
    columns.  Reduced row echelon form is performed over Fraction only.  The
    basis is ordered by its canonical free DSF coordinate and each vector is
    normalized to primitive integers with positive first nonzero coordinate.
    """

    if not isinstance(tangent, tuple) or len(tangent) != FIELDS_PER_LANE:
        raise ValueError("candidate tangent must have seven DSF output rows")
    if any(not isinstance(row, tuple) for row in tangent):
        raise TypeError("candidate tangent rows must be immutable tuples")
    widths = {len(row) for row in tangent}
    if len(widths) != 1:
        raise ValueError("candidate tangent rows must have equal width")
    width = next(iter(widths))
    if width == 0:
        raise ValueError("candidate tangent needs a physical perturbation coordinate")
    for row_index, row in enumerate(tangent):
        for column_index, value in enumerate(row):
            if not isinstance(value, Fraction):
                raise TypeError(
                    "candidate tangent coefficient "
                    f"({row_index}, {column_index}) must be a Fraction"
                )

    equations = [
        [tangent[field_index][perturbation_index] for field_index in range(7)]
        for perturbation_index in range(width)
    ]
    pivot_row = 0
    pivot_columns: list[int] = []
    for column in range(FIELDS_PER_LANE):
        selected = next(
            (
                index
                for index in range(pivot_row, len(equations))
                if equations[index][column] != 0
            ),
            None,
        )
        if selected is None:
            continue
        equations[pivot_row], equations[selected] = (
            equations[selected],
            equations[pivot_row],
        )
        pivot = equations[pivot_row][column]
        equations[pivot_row] = [
            value / pivot for value in equations[pivot_row]
        ]
        for index in range(len(equations)):
            if index == pivot_row:
                continue
            factor = equations[index][column]
            if factor:
                equations[index] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(
                        equations[index],
                        equations[pivot_row],
                        strict=True,
                    )
                ]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == len(equations):
            break

    free_columns = tuple(
        column
        for column in range(FIELDS_PER_LANE)
        if column not in set(pivot_columns)
    )
    basis: list[tuple[Fraction, ...]] = []
    for free_column in free_columns:
        vector = [Fraction(0) for _ in range(FIELDS_PER_LANE)]
        vector[free_column] = Fraction(1)
        for equation_index, pivot_column in enumerate(pivot_columns):
            vector[pivot_column] = -equations[equation_index][free_column]
        canonical = _canonical_primitive_covector(tuple(vector))
        for perturbation_index in range(width):
            annihilation = sum(
                (
                    canonical[field_index]
                    * tangent[field_index][perturbation_index]
                    for field_index in range(FIELDS_PER_LANE)
                ),
                Fraction(0),
            )
            if annihilation != 0:
                raise ArithmeticError(
                    "exact left-nullspace construction failed its annihilation proof"
                )
        basis.append(canonical)
    return tuple(basis)


@dataclass(frozen=True)
class CandidateProviderTangentClaim:
    """Untrusted candidate input; the producer must verify every mounted fact."""

    lane: L6Lane
    provider_id: str
    native_port_id: str
    branch_id: str | None
    cell_id: str | None
    perturbation_coordinate_ids: tuple[str, ...] | None
    tangent: tuple[tuple[object, ...], ...] | None
    branch_cell_receipt_sha256: str | None
    tangent_receipt_sha256: str | None


class CandidateConstraintProductionStatus(str, Enum):
    KNOWN = "known"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CandidateProviderConstraintSet:
    lane: L6Lane
    provider_id: str
    native_port_id: str
    branch_id: str
    cell_id: str
    branch_cell_receipt_sha256: str
    tangent_receipt_sha256: str
    rows: tuple[ConstraintRow, ...]
    row_receipt_payloads: tuple[bytes, ...]


@dataclass(frozen=True)
class CandidateConstraintProduction:
    status: CandidateConstraintProductionStatus
    stack: Fixed42ConstraintStack | None
    provider_sets: tuple[CandidateProviderConstraintSet, ...]
    reason: str


def _candidate_unknown(reason: str) -> CandidateConstraintProduction:
    return CandidateConstraintProduction(
        status=CandidateConstraintProductionStatus.UNKNOWN,
        stack=None,
        provider_sets=(),
        reason=reason,
    )


def _candidate_claim_failure(claim: CandidateProviderTangentClaim) -> str | None:
    try:
        if not isinstance(claim.lane, L6Lane):
            return "candidate provider lane is missing or invalid"
        for name, value in (
            ("provider_id", claim.provider_id),
            ("native_port_id", claim.native_port_id),
            ("branch_id", claim.branch_id),
            ("cell_id", claim.cell_id),
        ):
            _require_identifier(name, value)
        _require_sha256(
            "branch_cell_receipt_sha256",
            claim.branch_cell_receipt_sha256,
        )
        _require_sha256(
            "tangent_receipt_sha256",
            claim.tangent_receipt_sha256,
        )
        _validate_candidate_tangent(
            claim.perturbation_coordinate_ids,
            claim.tangent,
        )
    except (TypeError, ValueError) as exc:
        return str(exc)
    return None


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


def produce_candidate_fixed42_constraints(
    claims: tuple[CandidateProviderTangentClaim, ...] | None,
    receipt_registry: MountedReceiptRegistry | None,
) -> CandidateConstraintProduction:
    """Produce candidate rows only from mounted exact physical tangents.

    This is intentionally labelled candidate authority.  It becomes usable
    live only when real providers mount the exact tangent and same-branch/cell
    receipts.  A physical full-rank tangent resolves to a known empty row set.
    Any missing or inexact provider fact resolves to UNKNOWN with no partial
    stack.
    """

    if claims is None or not isinstance(claims, tuple) or not claims:
        return _candidate_unknown("mounted provider tangent claims are missing")
    if receipt_registry is None or not isinstance(
        receipt_registry,
        MountedReceiptRegistry,
    ):
        return _candidate_unknown("immutable mounted receipt registry is missing")

    verified_claims: list[CandidateProviderTangentClaim] = []
    identities: set[tuple[L6Lane, str, str]] = set()
    for claim in claims:
        if not isinstance(claim, CandidateProviderTangentClaim):
            return _candidate_unknown("a provider tangent claim has invalid type")
        failure = _candidate_claim_failure(claim)
        if failure is not None:
            return _candidate_unknown(f"provider tangent is unknown: {failure}")
        identity = (claim.lane, claim.provider_id, claim.native_port_id)
        if identity in identities:
            return _candidate_unknown(
                "duplicate provider/native-port tangent claims are indeterminate"
            )
        identities.add(identity)
        verified_claims.append(claim)

    verified_claims.sort(
        key=lambda claim: (
            LANE_ORDER.index(claim.lane),
            claim.provider_id,
            claim.native_port_id,
        )
    )
    provider_sets: list[CandidateProviderConstraintSet] = []
    all_rows: list[ConstraintRow] = []

    for claim in verified_claims:
        branch_payload = canonical_candidate_branch_cell_receipt_payload(
            lane=claim.lane,
            provider_id=claim.provider_id,
            native_port_id=claim.native_port_id,
            branch_id=claim.branch_id,
            cell_id=claim.cell_id,
        )
        if receipt_sha256(branch_payload) != claim.branch_cell_receipt_sha256:
            return _candidate_unknown(
                "same-branch/cell authority receipt does not bind the claim"
            )
        failure = _mounted_payload_failure(
            receipt_registry,
            digest=claim.branch_cell_receipt_sha256,
            field_name=CANDIDATE_BRANCH_CELL_RECEIPT_FIELD,
            expected_payload=branch_payload,
        )
        if failure is not None:
            return _candidate_unknown(failure)

        tangent = tuple(
            tuple(value for value in row)
            for row in claim.tangent
        )
        tangent_payload = canonical_candidate_local_tangent_receipt_payload(
            lane=claim.lane,
            provider_id=claim.provider_id,
            native_port_id=claim.native_port_id,
            branch_id=claim.branch_id,
            cell_id=claim.cell_id,
            perturbation_coordinate_ids=claim.perturbation_coordinate_ids,
            tangent=tangent,
            branch_cell_receipt_sha256=claim.branch_cell_receipt_sha256,
        )
        if receipt_sha256(tangent_payload) != claim.tangent_receipt_sha256:
            return _candidate_unknown(
                "local response tangent receipt does not bind the exact tangent"
            )
        failure = _mounted_payload_failure(
            receipt_registry,
            digest=claim.tangent_receipt_sha256,
            field_name=CANDIDATE_LOCAL_TANGENT_RECEIPT_FIELD,
            expected_payload=tangent_payload,
        )
        if failure is not None:
            return _candidate_unknown(failure)

        basis = candidate_exact_left_nullspace_basis(tangent)
        rows: list[ConstraintRow] = []
        row_payloads: list[bytes] = []
        for basis_index, coefficients in enumerate(basis):
            if not any(coefficients):
                return _candidate_unknown(
                    "left-nullspace producer attempted to emit a zero row"
                )
            row_id = (
                f"left-nullspace-{basis_index:02d}-"
                f"{claim.tangent_receipt_sha256}"
            )
            row_payload = canonical_row_receipt_payload(
                lane=claim.lane,
                provider_id=claim.provider_id,
                native_port_id=claim.native_port_id,
                operator_id=CANDIDATE_LEFT_NULLSPACE_OPERATOR_ID,
                row_id=row_id,
                coefficients=coefficients,
            )
            provenance = ConstraintRowProvenance(
                lane=claim.lane,
                provider_id=claim.provider_id,
                native_port_id=claim.native_port_id,
                operator_id=CANDIDATE_LEFT_NULLSPACE_OPERATOR_ID,
                receipt_sha256=receipt_sha256(row_payload),
                row_id=row_id,
            )
            row = embed_native_covector(
                NativeConstraintCovector(
                    provenance=provenance,
                    coefficients=coefficients,
                )
            )
            rows.append(row)
            row_payloads.append(row_payload)

        provider_set = CandidateProviderConstraintSet(
            lane=claim.lane,
            provider_id=claim.provider_id,
            native_port_id=claim.native_port_id,
            branch_id=claim.branch_id,
            cell_id=claim.cell_id,
            branch_cell_receipt_sha256=claim.branch_cell_receipt_sha256,
            tangent_receipt_sha256=claim.tangent_receipt_sha256,
            rows=tuple(rows),
            row_receipt_payloads=tuple(row_payloads),
        )
        provider_sets.append(provider_set)
        all_rows.extend(rows)

    return CandidateConstraintProduction(
        status=CandidateConstraintProductionStatus.KNOWN,
        stack=Fixed42ConstraintStack(tuple(all_rows)),
        provider_sets=tuple(provider_sets),
        reason=(
            "candidate rows are exactly derived from mounted provider tangents; "
            "live authority still depends on those provider mounts"
        ),
    )


@dataclass(frozen=True)
class ActiveLaneState:
    """Lane completeness plus retained U_star joint-field observation."""

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
            self.constraint_set_complete,
            bool,
        ):
            raise TypeError("constraint_set_complete must be bool or None")
        if self.constraint_set_receipt_sha256 is not None:
            _require_sha256(
                "constraint_set_receipt_sha256",
                self.constraint_set_receipt_sha256,
            )


@dataclass(frozen=True)
class L6PredicateInputs:
    active_lanes: tuple[ActiveLaneState, ...] | None
    disruption_clear: bool | None

    def __post_init__(self) -> None:
        if self.active_lanes is not None:
            if not isinstance(self.active_lanes, tuple):
                raise TypeError("active_lanes must be an immutable tuple or None")
            if any(
                not isinstance(value, ActiveLaneState)
                for value in self.active_lanes
            ):
                raise TypeError("every active lane must be an ActiveLaneState")
        if self.disruption_clear is not None and not isinstance(
            self.disruption_clear,
            bool,
        ):
            raise TypeError("disruption_clear must be bool or None")


@dataclass(frozen=True)
class ArbCaptureProof:
    python_flint_version: str
    flint_version: str
    threads: int
    precision_bits: int
    expression: str
    threshold_ball: str
    n_effective: int
    below_threshold: bool


class L6EvaluationStatus(str, Enum):
    LOCK = "lock"
    NO_LOCK = "no_lock"
    UNKNOWN_NO_LOCK = "unknown_no_lock"


@dataclass(frozen=True)
class L6Evaluation:
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
    python_version = getattr(flint, "__version__", None)
    flint_version = getattr(flint, "__FLINT_VERSION__", None)
    if python_version != PINNED_PYTHON_FLINT_VERSION:
        return None, (
            "python-flint version mismatch: expected "
            f"{PINNED_PYTHON_FLINT_VERSION}, received {python_version!r}"
        )
    if flint_version != PINNED_FLINT_VERSION:
        return None, (
            f"FLINT version mismatch: expected {PINNED_FLINT_VERSION}, "
            f"received {flint_version!r}"
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
            python_flint_version=python_version,
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
    if status is L6EvaluationStatus.LOCK:
        structural_lock: bool | None = True
    elif status is L6EvaluationStatus.NO_LOCK:
        structural_lock = False
    else:
        structural_lock = None
    if recovery_factor not in (None, 0, 1):
        raise ValueError("recovery_factor must be zero, one, or unknown")
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


def _receipt_authority_failure(
    stack: Fixed42ConstraintStack,
    lane_states: tuple[ActiveLaneState, ...],
    registry: MountedReceiptRegistry | None,
) -> str | None:
    if registry is None or not isinstance(registry, MountedReceiptRegistry):
        return "immutable mounted receipt registry is missing"
    for row in stack.rows:
        provenance = row.provenance
        expected = canonical_row_receipt_payload(
            lane=provenance.lane,
            provider_id=provenance.provider_id,
            native_port_id=provenance.native_port_id,
            operator_id=provenance.operator_id,
            row_id=provenance.row_id,
            coefficients=row.native_coefficients,
        )
        digest = receipt_sha256(expected)
        if provenance.receipt_sha256 != digest:
            return (
                "constraint row fields do not match provenance receipt SHA-256 "
                f"{provenance.receipt_sha256}"
            )
        failure = _mounted_payload_failure(
            registry,
            digest=provenance.receipt_sha256,
            field_name=ROW_RECEIPT_FIELD,
            expected_payload=expected,
        )
        if failure is not None:
            return failure
    for lane_state in lane_states:
        digest = lane_state.constraint_set_receipt_sha256
        if digest is None:
            return "an active lane constraint-set completeness receipt is missing"
        row_digests = tuple(
            row.provenance.receipt_sha256
            for row in stack.rows
            if row.provenance.lane is lane_state.lane
        )
        expected = canonical_completeness_receipt_payload(
            lane=lane_state.lane,
            row_receipt_sha256s=row_digests,
        )
        if digest != receipt_sha256(expected):
            return (
                f"{lane_state.lane.value} completeness receipt does not bind "
                "the exact active row set"
            )
        failure = _mounted_payload_failure(
            registry,
            digest=digest,
            field_name=COMPLETENESS_RECEIPT_FIELD,
            expected_payload=expected,
        )
        if failure is not None:
            return failure
    return None


def evaluate_l6(
    stack: Fixed42ConstraintStack,
    predicates: L6PredicateInputs | None = None,
    receipt_registry: MountedReceiptRegistry | None = None,
) -> L6Evaluation:
    """Evaluate fixed-42 capture without a standalone U_star veto."""

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
    active_ids = tuple(value.lane for value in lane_states)
    if len(set(active_ids)) != len(active_ids):
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="active lane evidence contains duplicate lanes",
        )
    if active_ids != tuple(lane for lane in LANE_ORDER if lane in set(active_ids)):
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="active lane evidence is not in canonical lane order",
        )
    if any(
        value.constraint_set_complete is None
        or value.constraint_set_receipt_sha256 is None
        for value in lane_states
    ):
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="an active lane constraint-set completeness receipt is missing",
        )
    if any(not value.constraint_set_complete for value in lane_states):
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="an active lane native constraint set is incomplete",
        )
    row_lanes = {row.provenance.lane for row in stack.rows}
    if not row_lanes.issubset(set(active_ids)):
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason="a constraint row belongs to a lane that is not active",
            recovery_factor=int(predicates.disruption_clear),
        )
    authority_failure = _receipt_authority_failure(
        stack,
        lane_states,
        receipt_registry,
    )
    if authority_failure is not None:
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason=authority_failure,
            recovery_factor=int(predicates.disruption_clear),
        )
    if len(active_ids) < 4:
        return _result(
            status=L6EvaluationStatus.NO_LOCK,
            rank_receipt=rank_receipt,
            reason="fewer than four valid active lanes",
            recovery_factor=int(predicates.disruption_clear),
        )
    if not predicates.disruption_clear:
        return _result(
            status=L6EvaluationStatus.NO_LOCK,
            rank_receipt=rank_receipt,
            reason="the disruption latch is not clear",
            recovery_factor=0,
        )
    proof, backend_failure = _arb_capture_proof(rank_receipt.n_effective)
    if proof is None:
        return _result(
            status=L6EvaluationStatus.UNKNOWN_NO_LOCK,
            rank_receipt=rank_receipt,
            reason=backend_failure or "Arb proof unavailable",
            recovery_factor=1,
        )
    if not proof.below_threshold:
        return _result(
            status=L6EvaluationStatus.NO_LOCK,
            rank_receipt=rank_receipt,
            arb_proof=proof,
            reason="exact combined rank does not enter the geometric capture basin",
            recovery_factor=1,
        )
    return _result(
        status=L6EvaluationStatus.LOCK,
        rank_receipt=rank_receipt,
        arb_proof=proof,
        reason="all corrected fixed-42 lock predicates are certified",
        recovery_factor=1,
    )


__all__ = [
    "ARB_PRECISION_BITS",
    "CANDIDATE_BRANCH_CELL_RECEIPT_FIELD",
    "CANDIDATE_LEFT_NULLSPACE_OPERATOR_ID",
    "CANDIDATE_LOCAL_TANGENT_RECEIPT_FIELD",
    "COMPLETENESS_RECEIPT_FIELD",
    "ActiveLaneState",
    "ArbCaptureProof",
    "CandidateConstraintProduction",
    "CandidateConstraintProductionStatus",
    "CandidateProviderConstraintSet",
    "CandidateProviderTangentClaim",
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
    "candidate_exact_left_nullspace_basis",
    "canonical_candidate_branch_cell_receipt_payload",
    "canonical_candidate_local_tangent_receipt_payload",
    "canonical_completeness_receipt_payload",
    "canonical_row_receipt_payload",
    "embed_native_covector",
    "evaluate_l6",
    "exact_rank_receipt",
    "fixed42_column",
    "produce_candidate_fixed42_constraints",
    "receipt_sha256",
]
