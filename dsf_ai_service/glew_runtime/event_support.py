"""Exact dimensionless event support for clean GLEW experiences.

For every field-evolution interval this operator keeps the most recently
closed evidence record for every non-language native port.  A port that does
not close at the current boundary contributes no new source charge; retaining
its physical state for geometry is not reinjection, interpolation, or a held
sample.

Once every mounted non-language port has a current record and at least four
distinct lived lanes are represented, the operator forms the exact Gram
matrix of the independent 19-coordinate port records and evaluates

    R_geometry = det(K) / product(diag(K)).

Every native port remains a separate Gram vector.  The interval drive is the
exact non-language source energy already mounted in the field authority,

    P_joint = sum(|J_i|^2) / (hbar * E_mem),

and the closed-experience support is

    R_event = sum(R_geometry * P_joint * delta_time).

All arithmetic is Fraction arithmetic.  There is no floor, epsilon, clamp,
normalization, lane average, score, or positive threshold.  Missing physical
energy authority is UNKNOWN; exact zero remains zero; any exact positive
result is positive.

``exact_port_gram_exterior_geometry`` is a separate, additive artifact over
the identical mounted port evidence.  A short common-grid replay window can
structurally force the full port set below full rank (e.g. exactly rank 3 of
5 non-language senses); rather than forcing full rank or collapsing that
structure to one fabricated score, this reports the exact rank and, for
every nonempty subset of ports, the exact Gram determinant and (when
nonzero) its normalized volume -- the same identity, generalized down to
whatever lower-rank exterior geometry the ports actually span.  It never
changes ``exact_port_gram_geometry``'s or ``evaluate_event_support``'s
existing rank-5-or-fail-closed behavior.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from .commit import (
    EventSupportAuthority,
    EventSupportState,
    event_support_authority_receipt_payload,
)
from .experience_origin import (
    ExperienceOriginAuthority,
    ExperienceOriginKind,
)
from .expressions import ClosedExperienceFieldExpression
from .field import FIBER_DIMENSION, MountedFieldTopology, PortTransportEvidence
from .model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)


EVENT_SUPPORT_OPERATOR_ID = "glew.exact_full_port_gram_event_support.v1"


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "event-support fraction")
    return f"{value.numerator}/{value.denominator}"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _mounted_exact(
    registry: ReceiptRegistry,
    digest: str,
    expected: bytes,
    description: str,
) -> None:
    mounted = registry.resolve(digest, description)
    if mounted != expected or receipt_sha256(expected) != digest:
        raise ReceiptError(f"{description} differs from mounted exact bytes")


def memory_energy_authority_receipt_payload(
    *,
    authority_id: str,
    energy_unit_id: str,
    exact_memory_energy: Fraction,
    derivation_receipt_sha256: str,
    physical_profile_receipt_sha256: str,
) -> bytes:
    require_identifier(authority_id, "memory-energy authority id")
    require_identifier(energy_unit_id, "memory-energy unit id")
    require_fraction(exact_memory_energy, "exact memory energy")
    if exact_memory_energy <= 0:
        raise ReceiptError("reference memory energy must be strictly positive")
    sha256_digest(
        derivation_receipt_sha256,
        "memory-energy derivation receipt",
    )
    sha256_digest(
        physical_profile_receipt_sha256,
        "memory-energy physical-profile receipt",
    )
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "derivation_receipt_sha256": derivation_receipt_sha256,
            "energy_unit_id": energy_unit_id,
            "exact_memory_energy": _fraction_text(exact_memory_energy),
            "physical_profile_receipt_sha256": (
                physical_profile_receipt_sha256
            ),
            "schema": "glew.event_support.reference_memory_energy.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class MemoryEnergyAuthority:
    authority_id: str
    energy_unit_id: str
    exact_memory_energy: Fraction
    derivation_receipt_sha256: str
    physical_profile_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return memory_energy_authority_receipt_payload(
            authority_id=self.authority_id,
            energy_unit_id=self.energy_unit_id,
            exact_memory_energy=self.exact_memory_energy,
            derivation_receipt_sha256=self.derivation_receipt_sha256,
            physical_profile_receipt_sha256=(
                self.physical_profile_receipt_sha256
            ),
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.derivation_receipt_sha256,
            "memory-energy derivation receipt",
        )
        receipt_registry.resolve(
            self.physical_profile_receipt_sha256,
            "memory-energy physical-profile receipt",
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            self.payload(),
            "memory-energy authority receipt",
        )


def _determinant(matrix: tuple[tuple[Fraction, ...], ...]) -> Fraction:
    size = len(matrix)
    if any(len(row) != size for row in matrix):
        raise ReceiptError("event-support Gram matrix is not square")
    if size == 0:
        return Fraction(1)
    values = [list(row) for row in matrix]
    result = Fraction(1)
    sign = 1
    for column in range(size):
        pivot_row = next(
            (
                row
                for row in range(column, size)
                if values[row][column] != 0
            ),
            None,
        )
        if pivot_row is None:
            return Fraction(0)
        if pivot_row != column:
            values[column], values[pivot_row] = (
                values[pivot_row],
                values[column],
            )
            sign = -sign
        pivot = values[column][column]
        result *= pivot
        for row in range(column + 1, size):
            factor = values[row][column] / pivot
            if factor == 0:
                continue
            for index in range(column + 1, size):
                values[row][index] -= factor * values[column][index]
    return result * sign


def _inner(left: tuple[Fraction, ...], right: tuple[Fraction, ...]) -> Fraction:
    if len(left) != FIBER_DIMENSION or len(right) != FIBER_DIMENSION:
        raise ReceiptError("event-support port record is not 19-dimensional")
    return sum(
        (one * two for one, two in zip(left, right, strict=True)),
        Fraction(0),
    )


def _product(values: tuple[Fraction, ...]) -> Fraction:
    result = Fraction(1)
    for value in values:
        result *= value
    return result


def _gram_subset_geometry(
    vectors: tuple[tuple[Fraction, ...], ...],
) -> tuple[Fraction, Fraction]:
    """Return the exact (Gram determinant, normalized Gram volume) for a subset.

    This is the single shared exact-arithmetic core: the same Fraction Gram
    matrix, the same Gaussian-elimination determinant, and the same
    ``det(K) / product(diag(K))`` normalization that ``exact_port_gram_geometry``
    applies to the full port set, generalized to any nonempty subset of port
    vectors.  A zero-energy port (zero diagonal) collapses the subset to an
    exact zero, exactly as the full-set computation already does; it is never
    treated as an error, a missing dimension, or a fabricated volume.
    """

    gram = tuple(
        tuple(_inner(left, right) for right in vectors) for left in vectors
    )
    diagonal = tuple(gram[index][index] for index in range(len(gram)))
    if any(value < 0 for value in diagonal):
        raise ReceiptError("event-support Gram diagonal is negative")
    if any(value == 0 for value in diagonal):
        return Fraction(0), Fraction(0)
    denominator = _product(diagonal)
    determinant = _determinant(gram)
    if determinant < 0:
        raise ReceiptError("exact Gram determinant is negative")
    normalized = determinant / denominator
    if not 0 <= normalized <= 1:
        raise ReceiptError("exact normalized Gram geometry lies outside [0,1]")
    return determinant, normalized


def exact_port_gram_geometry(
    evidence: tuple[PortTransportEvidence, ...],
) -> Fraction:
    """Return exact native-port geometry without selecting or averaging ports."""

    if not isinstance(evidence, tuple) or not evidence:
        return Fraction(0)
    keys = tuple(value.key for value in evidence)
    if keys != tuple(sorted(set(keys))):
        raise ReceiptError("event-support port evidence is not canonical and unique")
    vectors = tuple(value.coordinates.as_tuple() for value in evidence)
    _determinant_value, normalized = _gram_subset_geometry(vectors)
    return normalized


EXTERIOR_GRAM_GEOMETRY_OPERATOR_ID = "glew.exact_port_gram_exterior_geometry.v1"


def _canonical_port_key_pair(key: tuple[str, str]) -> list[str]:
    lane_id, port_id = key
    require_identifier(lane_id, "exterior Gram port lane_id")
    require_identifier(port_id, "exterior Gram port port_id")
    return [lane_id, port_id]


def _ordered_nonempty_subsets(
    port_keys: tuple[tuple[str, str], ...],
) -> tuple[tuple[tuple[str, str], ...], ...]:
    """Every nonempty subset of ``port_keys``, canonically ordered by size then key."""

    return tuple(
        combo
        for size in range(1, len(port_keys) + 1)
        for combo in itertools.combinations(port_keys, size)
    )


def exterior_port_gram_subset_volume_payload(
    *,
    port_keys: tuple[tuple[str, str], ...],
    exact_gram_determinant: Fraction,
    nonzero: bool,
    exact_normalized_volume: Fraction,
) -> dict[str, object]:
    require_fraction(exact_gram_determinant, "exterior Gram subset determinant")
    require_fraction(exact_normalized_volume, "exterior Gram subset normalized volume")
    if not isinstance(nonzero, bool):
        raise ReceiptError("exterior Gram subset nonzero flag must be bool")
    return {
        "exact_gram_determinant": _fraction_text(exact_gram_determinant),
        "exact_normalized_volume": _fraction_text(exact_normalized_volume),
        "nonzero": nonzero,
        "port_keys": [_canonical_port_key_pair(key) for key in port_keys],
    }


@dataclass(frozen=True, slots=True)
class ExteriorPortGramSubsetVolume:
    """One principal Gram minor: an exact lower-rank exterior volume witness.

    ``exact_gram_determinant`` is the exact Gram determinant of exactly this
    port subset.  By the standard Gram identity this is the squared
    exterior/wedge-product volume that subset's port vectors genuinely span
    -- nonzero exactly when those ports are independent.  ``nonzero`` names
    that fact explicitly.  ``exact_normalized_volume`` divides the
    determinant by the product of the subset's own diagonal (squared-norm)
    entries: the identical normalization ``exact_port_gram_geometry`` already
    applies to the full five-port case, generalized to this subset alone.
    """

    port_keys: tuple[tuple[str, str], ...]
    exact_gram_determinant: Fraction
    nonzero: bool
    exact_normalized_volume: Fraction

    def __post_init__(self) -> None:
        if not isinstance(self.port_keys, tuple) or not self.port_keys:
            raise ReceiptError(
                "exterior Gram subset requires a nonempty immutable port-key tuple"
            )
        for key in self.port_keys:
            if not isinstance(key, tuple) or len(key) != 2:
                raise ReceiptError(
                    "exterior Gram subset port key is not a (lane_id, port_id) pair"
                )
            require_identifier(key[0], "exterior Gram port lane_id")
            require_identifier(key[1], "exterior Gram port port_id")
        if tuple(sorted(set(self.port_keys))) != self.port_keys:
            raise ReceiptError(
                "exterior Gram subset port keys are not canonical and unique"
            )
        require_fraction(
            self.exact_gram_determinant, "exterior Gram subset determinant"
        )
        require_fraction(
            self.exact_normalized_volume, "exterior Gram subset normalized volume"
        )
        if self.exact_gram_determinant < 0:
            raise ReceiptError("exterior Gram subset determinant is negative")
        if not 0 <= self.exact_normalized_volume <= 1:
            raise ReceiptError(
                "exterior Gram subset normalized volume lies outside [0,1]"
            )
        if not isinstance(self.nonzero, bool):
            raise ReceiptError("exterior Gram subset nonzero flag must be bool")
        if self.nonzero != (self.exact_gram_determinant != 0):
            raise ReceiptError(
                "exterior Gram subset nonzero flag differs from its exact determinant"
            )
        if (self.exact_gram_determinant == 0) != (self.exact_normalized_volume == 0):
            raise ReceiptError(
                "exterior Gram subset volume differs from its determinant's zero class"
            )

    def as_payload(self) -> dict[str, object]:
        return exterior_port_gram_subset_volume_payload(
            port_keys=self.port_keys,
            exact_gram_determinant=self.exact_gram_determinant,
            nonzero=self.nonzero,
            exact_normalized_volume=self.exact_normalized_volume,
        )


def exact_port_gram_exterior_receipt_payload(
    *,
    port_keys: tuple[tuple[str, str], ...],
    rank: int,
    subsets: tuple[ExteriorPortGramSubsetVolume, ...],
) -> bytes:
    if not isinstance(port_keys, tuple) or not port_keys:
        raise ReceiptError(
            "exterior Gram receipt requires a nonempty immutable port-key tuple"
        )
    if tuple(sorted(set(port_keys))) != port_keys:
        raise ReceiptError("exterior Gram receipt port keys are not canonical and unique")
    if isinstance(rank, bool) or not isinstance(rank, int):
        raise ReceiptError("exterior Gram receipt rank must be an integer")
    if not 0 <= rank <= len(port_keys):
        raise ReceiptError("exterior Gram receipt rank lies outside the mounted port count")
    if not isinstance(subsets, tuple) or not all(
        isinstance(value, ExteriorPortGramSubsetVolume) for value in subsets
    ):
        raise ReceiptError("exterior Gram receipt subsets must be a typed immutable tuple")
    expected_subset_keys = _ordered_nonempty_subsets(port_keys)
    if tuple(value.port_keys for value in subsets) != expected_subset_keys:
        raise ReceiptError(
            "exterior Gram receipt does not cover every principal port subset exactly once"
        )
    largest_independent = max(
        (len(value.port_keys) for value in subsets if value.nonzero),
        default=0,
    )
    if rank != largest_independent:
        raise ReceiptError(
            "exterior Gram receipt rank differs from its largest independent principal subset"
        )
    return _canonical_bytes(
        {
            "operator_id": EXTERIOR_GRAM_GEOMETRY_OPERATOR_ID,
            "port_keys": [_canonical_port_key_pair(key) for key in port_keys],
            "rank": rank,
            "schema": "glew.event_support.exterior_gram_geometry.v1",
            "subset_count": len(subsets),
            "subsets": [value.as_payload() for value in subsets],
        }
    )


@dataclass(frozen=True, slots=True)
class ExactPortGramExteriorReceipt:
    """Exact exterior-grade receipt: every principal Gram minor of one port set.

    This never replaces ``exact_port_gram_geometry``'s rank-5-or-fail-closed
    full-volume result and never changes ``evaluate_event_support``.  It is
    an additive, richer artifact reporting the exact rank plus every nonzero
    principal Gram volume so a future L5 governor may recognize viable
    lower-rank exterior structure without inventing missing dimensions or
    collapsing every subset to one support-minus-drag score.
    """

    port_keys: tuple[tuple[str, str], ...]
    rank: int
    subsets: tuple[ExteriorPortGramSubsetVolume, ...]
    receipt_sha256: str

    def payload(self) -> bytes:
        return exact_port_gram_exterior_receipt_payload(
            port_keys=self.port_keys,
            rank=self.rank,
            subsets=self.subsets,
        )

    def subset(
        self, port_keys: tuple[tuple[str, str], ...]
    ) -> ExteriorPortGramSubsetVolume:
        """Return the exact receipt entry for one principal port subset."""

        canonical = tuple(sorted(port_keys))
        for value in self.subsets:
            if value.port_keys == canonical:
                return value
        raise ReceiptError("exterior Gram receipt has no matching principal subset")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        expected_payload = self.payload()
        if receipt_sha256(expected_payload) != self.receipt_sha256:
            raise ReceiptError(
                "exterior Gram geometry receipt differs from its exact canonical bytes"
            )
        _mounted_exact(
            receipt_registry,
            self.receipt_sha256,
            expected_payload,
            "exterior Gram geometry receipt",
        )


def exact_port_gram_exterior_geometry(
    evidence: tuple[PortTransportEvidence, ...],
) -> ExactPortGramExteriorReceipt:
    """Return the exact exterior-grade receipt over every principal port subset.

    For every nonempty subset of the mounted ports this reports the exact
    Gram determinant -- by the standard Gram identity, the squared
    exterior/wedge-product volume that subset's port vectors genuinely span
    -- whether it is nonzero, and (using the identical normalization
    ``exact_port_gram_geometry`` already applies) its normalized volume.  The
    exact rank of the full port set is the size of the largest principal
    subset that is genuinely independent, which by construction equals the
    ordinary linear-algebraic rank of the mounted port vectors.

    This does not select, average, or threshold ports, and it does not
    change ``exact_port_gram_geometry``'s or ``evaluate_event_support``'s
    existing rank-5-or-fail-closed behavior; it is an additional artifact
    computed alongside them from the identical mounted evidence.
    """

    if not isinstance(evidence, tuple) or not evidence:
        raise ReceiptError("exterior Gram geometry requires at least one mounted port")
    keys = tuple(value.key for value in evidence)
    if keys != tuple(sorted(set(keys))):
        raise ReceiptError("event-support port evidence is not canonical and unique")
    by_key = {value.key: value.coordinates.as_tuple() for value in evidence}
    port_keys = tuple(sorted(by_key))

    subsets = []
    for combo in _ordered_nonempty_subsets(port_keys):
        determinant, normalized = _gram_subset_geometry(
            tuple(by_key[key] for key in combo)
        )
        subsets.append(
            ExteriorPortGramSubsetVolume(
                port_keys=combo,
                exact_gram_determinant=determinant,
                nonzero=determinant != 0,
                exact_normalized_volume=normalized,
            )
        )
    subsets = tuple(subsets)
    rank = max((len(value.port_keys) for value in subsets if value.nonzero), default=0)
    payload = exact_port_gram_exterior_receipt_payload(
        port_keys=port_keys,
        rank=rank,
        subsets=subsets,
    )
    return ExactPortGramExteriorReceipt(
        port_keys=port_keys,
        rank=rank,
        subsets=subsets,
        receipt_sha256=receipt_sha256(payload),
    )


def _interval_source_energy(
    *,
    topology: MountedFieldTopology,
    expression: ClosedExperienceFieldExpression,
    step_index: int,
) -> Fraction:
    authority = expression.steps[step_index].authority
    total = Fraction(0)
    for coefficient in authority.source:
        fiber_index = coefficient.index // FIBER_DIMENSION
        if fiber_index >= len(topology.ordered_port_fibers):
            raise ReceiptError("event source coordinate lies outside topology")
        fiber = topology.ordered_port_fibers[fiber_index]
        if fiber.lane_id == "language":
            continue
        total += (
            coefficient.value.real * coefficient.value.real
            + coefficient.value.imag * coefficient.value.imag
        )
    return total


def event_support_result_receipt_payload(
    *,
    topology_authority_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    expression_receipt_sha256: str,
    origin_authority_receipt_sha256: str,
    origin_kind: ExperienceOriginKind,
    memory_energy_authority_receipt_sha256: str | None,
    interval_receipts: tuple["EventSupportInterval", ...],
    exact_r_event: Fraction,
) -> bytes:
    for value, name in (
        (topology_authority_receipt_sha256, "event-support topology receipt"),
        (closed_experience_receipt_sha256, "event-support experience receipt"),
        (expression_receipt_sha256, "event-support expression receipt"),
        (origin_authority_receipt_sha256, "event-support origin receipt"),
    ):
        sha256_digest(value, name)
    if not isinstance(origin_kind, ExperienceOriginKind):
        raise ReceiptError("event-support origin kind is not typed")
    if memory_energy_authority_receipt_sha256 is not None:
        sha256_digest(
            memory_energy_authority_receipt_sha256,
            "event-support memory-energy receipt",
        )
    require_fraction(exact_r_event, "exact R_event")
    if exact_r_event < 0:
        raise ReceiptError("R_event cannot be negative")
    if not isinstance(interval_receipts, tuple):
        raise ReceiptError("event-support intervals must be an immutable tuple")
    recall = origin_kind is ExperienceOriginKind.SELF_GENERATED_RECALL
    if recall:
        if memory_energy_authority_receipt_sha256 is not None:
            raise ReceiptError("self-generated recall cannot cite fresh memory energy")
        if exact_r_event != 0:
            raise ReceiptError("self-generated recall fresh R_event must be exact zero")
        if any(
            value.exact_fresh_source_energy != 0
            or value.exact_p_joint != 0
            or value.exact_interval_support != 0
            for value in interval_receipts
        ):
            raise ReceiptError("recalled sensory traces were relabelled as fresh energy")
    elif memory_energy_authority_receipt_sha256 is None:
        raise ReceiptError("external/story event support requires memory energy")
    return _canonical_bytes(
        {
            "closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "exact_R_event": _fraction_text(exact_r_event),
            "expression_receipt_sha256": expression_receipt_sha256,
            "fresh_energy_rule": (
                "self_generated_recall_has_zero_fresh_source_energy"
                if recall
                else "fresh_external_or_story_source_energy"
            ),
            "intervals": [value.as_payload() for value in interval_receipts],
            "memory_energy_authority_receipt_sha256": (
                memory_energy_authority_receipt_sha256
            ),
            "native_port_rule": (
                "each_nonlanguage_port_is_one_independent_19_coordinate_Gram_vector"
            ),
            "operator_id": EVENT_SUPPORT_OPERATOR_ID,
            "origin_authority_receipt_sha256": (
                origin_authority_receipt_sha256
            ),
            "origin_kind": origin_kind.value,
            "schema": "glew.event_support.exact_closed_experience.v2",
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class EventSupportInterval:
    step_index: int
    source_time_start: Fraction
    source_time_end: Fraction
    map_injection_receipt_sha256: str
    current_port_evidence_receipt_sha256s: tuple[str, ...]
    lived_lane_ids: tuple[str, ...]
    exact_r_geometry: Fraction
    exact_source_energy: Fraction
    exact_fresh_source_energy: Fraction
    exact_p_joint: Fraction
    exact_interval_support: Fraction

    def __post_init__(self) -> None:
        if isinstance(self.step_index, bool) or not isinstance(self.step_index, int):
            raise ReceiptError("event-support step index must be an integer")
        if self.step_index < 0:
            raise ReceiptError("event-support step index cannot be negative")
        for value, name in (
            (self.source_time_start, "event-support source-time start"),
            (self.source_time_end, "event-support source-time end"),
            (self.exact_r_geometry, "event-support geometry"),
            (self.exact_source_energy, "event-support cited source energy"),
            (self.exact_fresh_source_energy, "event-support fresh source energy"),
            (self.exact_p_joint, "event-support P_joint"),
            (self.exact_interval_support, "event-support interval support"),
        ):
            require_fraction(value, name)
        if self.source_time_end <= self.source_time_start:
            raise ReceiptError("event-support interval duration must be positive")
        if any(
            value < 0
            for value in (
                self.exact_r_geometry,
                self.exact_source_energy,
                self.exact_fresh_source_energy,
                self.exact_p_joint,
                self.exact_interval_support,
            )
        ):
            raise ReceiptError("event-support interval contains negative physics")
        sha256_digest(
            self.map_injection_receipt_sha256,
            "event-support MapInject receipt",
        )
        for value in self.current_port_evidence_receipt_sha256s:
            sha256_digest(value, "event-support current-port evidence receipt")
        if tuple(sorted(set(self.lived_lane_ids))) != self.lived_lane_ids:
            raise ReceiptError("event-support lived lanes are not canonical")

    def as_payload(self) -> dict[str, object]:
        return {
            "current_port_evidence_receipt_sha256s": list(
                self.current_port_evidence_receipt_sha256s
            ),
            "exact_P_joint": _fraction_text(self.exact_p_joint),
            "exact_R_geometry": _fraction_text(self.exact_r_geometry),
            "exact_fresh_source_energy": _fraction_text(
                self.exact_fresh_source_energy
            ),
            "exact_interval_support": _fraction_text(
                self.exact_interval_support
            ),
            "exact_source_energy": _fraction_text(self.exact_source_energy),
            "lived_lane_ids": list(self.lived_lane_ids),
            "map_injection_receipt_sha256": (
                self.map_injection_receipt_sha256
            ),
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "step_index": self.step_index,
        }


class EventSupportEvaluationStatus(str, Enum):
    RESOLVED = "resolved"
    UNKNOWN = "unknown"


def _unknown_source_payload(
    *,
    topology_receipt: str,
    experience_receipt: str,
    expression_receipt: str,
    origin: ExperienceOriginAuthority,
    reason: str,
) -> bytes:
    return _canonical_bytes(
        {
            "closed_experience_receipt_sha256": experience_receipt,
            "expression_receipt_sha256": expression_receipt,
            "operator_id": EVENT_SUPPORT_OPERATOR_ID,
            "origin_authority_receipt_sha256": (
                origin.authority_receipt_sha256
            ),
            "origin_kind": origin.kind.value,
            "reason": reason,
            "schema": "glew.event_support.explicit_unknown.v2",
            "topology_authority_receipt_sha256": topology_receipt,
        }
    )


@dataclass(frozen=True, slots=True)
class EventSupportEvaluation:
    status: EventSupportEvaluationStatus
    authority: EventSupportAuthority
    origin_authority_receipt_sha256: str
    intervals: tuple[EventSupportInterval, ...]
    exact_r_event: Fraction | None
    reason: str
    source_receipt_sha256: str
    source_receipt_payload: bytes
    authority_receipt_payload: bytes

    @property
    def generated_receipt_payloads(self) -> tuple[bytes, bytes]:
        return self.source_receipt_payload, self.authority_receipt_payload

    def verify(
        self,
        *,
        origin: ExperienceOriginAuthority,
        topology: MountedFieldTopology,
        closed_experience_receipt_sha256: str,
        expression: ClosedExperienceFieldExpression,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        origin.verify(receipt_registry)
        topology.verify(receipt_registry)
        expression.verify(receipt_registry)
        if (
            self.origin_authority_receipt_sha256
            != origin.authority_receipt_sha256
            or origin.topology_authority_receipt_sha256
            != topology.authority_receipt_sha256
            or origin.closed_experience_receipt_sha256
            != closed_experience_receipt_sha256
            or expression.topology_authority_receipt_sha256
            != topology.authority_receipt_sha256
        ):
            raise ReceiptError("event-support evaluation scope or origin changed")
        if self.status is EventSupportEvaluationStatus.RESOLVED:
            if self.exact_r_event is None:
                raise ReceiptError("resolved R_event lacks an exact value")
            source = json.loads(self.source_receipt_payload)
            memory_receipt = source.get(
                "memory_energy_authority_receipt_sha256"
            )
            if memory_receipt is not None and not isinstance(memory_receipt, str):
                raise ReceiptError("event-support memory receipt is not typed")
            expected_source = event_support_result_receipt_payload(
                topology_authority_receipt_sha256=(
                    topology.authority_receipt_sha256
                ),
                closed_experience_receipt_sha256=(
                    closed_experience_receipt_sha256
                ),
                expression_receipt_sha256=expression.receipt_sha256,
                origin_authority_receipt_sha256=(
                    origin.authority_receipt_sha256
                ),
                origin_kind=origin.kind,
                memory_energy_authority_receipt_sha256=memory_receipt,
                interval_receipts=self.intervals,
                exact_r_event=self.exact_r_event,
            )
            if memory_receipt is not None:
                receipt_registry.resolve(
                    memory_receipt,
                    "event-support memory-energy authority receipt",
                )
        elif self.status is EventSupportEvaluationStatus.UNKNOWN:
            if self.exact_r_event is not None or self.intervals:
                raise ReceiptError("UNKNOWN event support carries nominal physics")
            expected_source = _unknown_source_payload(
                topology_receipt=topology.authority_receipt_sha256,
                experience_receipt=closed_experience_receipt_sha256,
                expression_receipt=expression.receipt_sha256,
                origin=origin,
                reason=self.reason,
            )
        else:
            raise ReceiptError("event-support evaluation status is not typed")
        if (
            expected_source != self.source_receipt_payload
            or receipt_sha256(expected_source) != self.source_receipt_sha256
            or self.authority.source_operator_receipt_sha256
            != self.source_receipt_sha256
            or self.authority.exact_r_event != self.exact_r_event
        ):
            raise ReceiptError("event-support evaluation differs from exact bytes")
        expected_authority = event_support_authority_receipt_payload(
            authority_id=self.authority.authority_id,
            state=self.authority.state,
            exact_r_event=self.authority.exact_r_event,
            topology_authority_receipt_sha256=(
                self.authority.topology_authority_receipt_sha256
            ),
            closed_experience_receipt_sha256=(
                self.authority.closed_experience_receipt_sha256
            ),
            source_operator_receipt_sha256=(
                self.authority.source_operator_receipt_sha256
            ),
        )
        if expected_authority != self.authority_receipt_payload:
            raise ReceiptError("event-support authority differs from exact bytes")
        _mounted_exact(
            receipt_registry,
            self.source_receipt_sha256,
            self.source_receipt_payload,
            "event-support source receipt",
        )
        _mounted_exact(
            receipt_registry,
            self.authority.authority_receipt_sha256,
            self.authority_receipt_payload,
            "event-support authority receipt",
        )
        self.authority.verify(
            topology_receipt=topology.authority_receipt_sha256,
            experience_receipt=closed_experience_receipt_sha256,
            receipt_registry=receipt_registry,
        )


def _unknown_evaluation(
    *,
    authority_id: str,
    topology_receipt: str,
    experience_receipt: str,
    expression_receipt: str,
    origin: ExperienceOriginAuthority,
    reason: str,
) -> EventSupportEvaluation:
    source_payload = _unknown_source_payload(
        topology_receipt=topology_receipt,
        experience_receipt=experience_receipt,
        expression_receipt=expression_receipt,
        origin=origin,
        reason=reason,
    )
    source_digest = receipt_sha256(source_payload)
    authority_payload = event_support_authority_receipt_payload(
        authority_id=authority_id,
        state=EventSupportState.UNKNOWN,
        exact_r_event=None,
        topology_authority_receipt_sha256=topology_receipt,
        closed_experience_receipt_sha256=experience_receipt,
        source_operator_receipt_sha256=source_digest,
    )
    authority = EventSupportAuthority(
        authority_id,
        EventSupportState.UNKNOWN,
        None,
        topology_receipt,
        experience_receipt,
        source_digest,
        receipt_sha256(authority_payload),
    )
    return EventSupportEvaluation(
        EventSupportEvaluationStatus.UNKNOWN,
        authority,
        origin.authority_receipt_sha256,
        (),
        None,
        reason,
        source_digest,
        source_payload,
        authority_payload,
    )


def evaluate_event_support(
    *,
    authority_id: str,
    origin: ExperienceOriginAuthority,
    topology: MountedFieldTopology,
    closed_experience_receipt_sha256: str,
    expression: ClosedExperienceFieldExpression,
    memory_energy: MemoryEnergyAuthority | None,
    receipt_registry: ReceiptRegistry,
) -> EventSupportEvaluation:
    """Evaluate fresh R_event while preserving every cited full-field trace."""

    require_identifier(authority_id, "R_event authority id")
    sha256_digest(
        closed_experience_receipt_sha256,
        "R_event closed-experience receipt",
    )
    if not isinstance(origin, ExperienceOriginAuthority):
        raise ReceiptError("R_event requires a typed experience origin")
    origin.verify(receipt_registry)
    topology.verify(receipt_registry)
    expression.verify(receipt_registry)
    if (
        origin.topology_authority_receipt_sha256
        != topology.authority_receipt_sha256
        or origin.closed_experience_receipt_sha256
        != closed_experience_receipt_sha256
    ):
        raise ReceiptError("R_event origin belongs to another closed field")
    if expression.topology_authority_receipt_sha256 != (
        topology.authority_receipt_sha256
    ):
        raise ReceiptError("R_event expression belongs to another topology")

    recall = origin.kind is ExperienceOriginKind.SELF_GENERATED_RECALL
    if not recall:
        if memory_energy is None or not isinstance(
            memory_energy, MemoryEnergyAuthority
        ):
            return _unknown_evaluation(
                authority_id=authority_id,
                topology_receipt=topology.authority_receipt_sha256,
                experience_receipt=closed_experience_receipt_sha256,
                expression_receipt=expression.receipt_sha256,
                origin=origin,
                reason="reference memory-energy authority is missing",
            )
        memory_energy.verify(receipt_registry)
        if any(
            step.authority.physical_profile_receipt_sha256
            != memory_energy.physical_profile_receipt_sha256
            for step in expression.steps
        ):
            raise ReceiptError("R_event field and memory energy use different profiles")

    hbars = {step.authority.hbar for step in expression.steps}
    time_units = {step.authority.source_time_unit for step in expression.steps}
    if len(hbars) != 1 or len(time_units) != 1:
        raise ReceiptError("R_event expression changes dimensional authority")
    hbar = next(iter(hbars))
    required_nonlanguage = tuple(
        fiber.key
        for fiber in topology.ordered_port_fibers
        if fiber.lane_id != "language"
    )
    current: dict[tuple[str, str], PortTransportEvidence] = {}
    intervals: list[EventSupportInterval] = []
    total = Fraction(0)
    for step_index, step in enumerate(expression.steps):
        for mapped in step.injection.mapped_fibers:
            if mapped.fiber.lane_id != "language":
                current[mapped.fiber.key] = mapped.evidence
        complete = all(key in current for key in required_nonlanguage)
        ordered_current = tuple(
            current[key] for key in required_nonlanguage if key in current
        )
        lived_lanes = tuple(sorted({value.lane_id for value in ordered_current}))
        cited_source_energy = _interval_source_energy(
            topology=topology,
            expression=expression,
            step_index=step_index,
        )
        fresh_source_energy = Fraction(0) if recall else cited_source_energy
        if complete and len(lived_lanes) >= 4:
            geometry = exact_port_gram_geometry(
                tuple(sorted(ordered_current, key=lambda value: value.key))
            )
        else:
            geometry = Fraction(0)
        if recall:
            p_joint = Fraction(0)
        else:
            assert memory_energy is not None
            p_joint = fresh_source_energy / (
                hbar * memory_energy.exact_memory_energy
            )
        interval_support = geometry * p_joint * step.authority.delta
        total += interval_support
        intervals.append(
            EventSupportInterval(
                step_index=step_index,
                source_time_start=step.authority.source_time_start,
                source_time_end=step.authority.source_time_end,
                map_injection_receipt_sha256=step.injection.receipt_sha256,
                current_port_evidence_receipt_sha256s=tuple(
                    value.evidence_receipt_sha256
                    for value in sorted(
                        ordered_current,
                        key=lambda value: value.key,
                    )
                ),
                lived_lane_ids=lived_lanes,
                exact_r_geometry=geometry,
                exact_source_energy=cited_source_energy,
                exact_fresh_source_energy=fresh_source_energy,
                exact_p_joint=p_joint,
                exact_interval_support=interval_support,
            )
        )

    state = EventSupportState.POSITIVE if total > 0 else EventSupportState.ZERO
    memory_receipt = (
        None
        if recall
        else memory_energy.authority_receipt_sha256
        if memory_energy is not None
        else None
    )
    source_payload = event_support_result_receipt_payload(
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=closed_experience_receipt_sha256,
        expression_receipt_sha256=expression.receipt_sha256,
        origin_authority_receipt_sha256=origin.authority_receipt_sha256,
        origin_kind=origin.kind,
        memory_energy_authority_receipt_sha256=memory_receipt,
        interval_receipts=tuple(intervals),
        exact_r_event=total,
    )
    source_digest = receipt_sha256(source_payload)
    authority_payload = event_support_authority_receipt_payload(
        authority_id=authority_id,
        state=state,
        exact_r_event=total,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=closed_experience_receipt_sha256,
        source_operator_receipt_sha256=source_digest,
    )
    authority = EventSupportAuthority(
        authority_id,
        state,
        total,
        topology.authority_receipt_sha256,
        closed_experience_receipt_sha256,
        source_digest,
        receipt_sha256(authority_payload),
    )
    return EventSupportEvaluation(
        EventSupportEvaluationStatus.RESOLVED,
        authority,
        origin.authority_receipt_sha256,
        tuple(intervals),
        total,
        (
            "self-generated recall preserves cited traces with zero fresh energy"
            if recall
            else "exact fresh closed-experience event support resolved"
        ),
        source_digest,
        source_payload,
        authority_payload,
    )


__all__ = (
    "EVENT_SUPPORT_OPERATOR_ID",
    "EXTERIOR_GRAM_GEOMETRY_OPERATOR_ID",
    "ExactPortGramExteriorReceipt",
    "EventSupportEvaluation",
    "EventSupportEvaluationStatus",
    "EventSupportInterval",
    "ExteriorPortGramSubsetVolume",
    "MemoryEnergyAuthority",
    "evaluate_event_support",
    "event_support_result_receipt_payload",
    "exact_port_gram_exterior_geometry",
    "exact_port_gram_exterior_receipt_payload",
    "exact_port_gram_geometry",
    "exterior_port_gram_subset_volume_payload",
    "memory_energy_authority_receipt_payload",
)
