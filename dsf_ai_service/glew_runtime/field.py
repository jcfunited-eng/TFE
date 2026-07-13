"""Topology-derived, non-flattening MapInject and certified field evolution.

The mounted topology, not a compatibility constant and not the observations in
one gate, determines the field dimension.  Each native port owns one ordered
19-coordinate fiber.  MapInject is the identity inclusion of that port's exact
rational coordinates into its fiber; it performs no projection, averaging,
normalization, hashing, or QR factorization.

One evolution call solves the piecewise-constant affine equation

    d psi / dt = (diag(growth - decay) - i H / hbar) psi + J

on an exact, positive source-time interval.  H is exact Hermitian authority,
and growth, decay, and J are explicit exact coefficients in the mounted
authority receipt.  The solve uses an augmented matrix exponential in pinned
python-flint/FLINT Arb arithmetic.  Exact generator sparsity is factored into
canonical connected components before exponentiation; this is an exact direct
sum, never a numerical approximation.
"""

from __future__ import annotations

import hashlib
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
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)


TRANSPORT_COORDINATE_ORDER = (
    "TVR_T",
    "TVR_V",
    "TVR_R",
    "w_k",
    "CV_T",
    "CV_V",
    "CV_R",
    "S_k",
    "U_k",
    "IAS_k",
    "URF_k",
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
    "N_gate",
)
FIBER_DIMENSION = len(TRANSPORT_COORDINATE_ORDER)


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


def _complex_payload(value: "ExactComplex") -> dict[str, str]:
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


@dataclass(frozen=True, slots=True)
class ExactComplex:
    """Complex coefficient with exact rational real and imaginary parts."""

    real: Fraction
    imag: Fraction = Fraction(0)

    def __post_init__(self) -> None:
        require_fraction(self.real, "complex.real")
        require_fraction(self.imag, "complex.imag")

    def conjugate(self) -> "ExactComplex":
        return ExactComplex(self.real, -self.imag)

    @property
    def is_zero(self) -> bool:
        return self.real == 0 and self.imag == 0


@dataclass(frozen=True, slots=True)
class TransportCoordinates19:
    """The complete raw numeric transport record for one port and one gate."""

    TVR_T: Fraction
    TVR_V: Fraction
    TVR_R: Fraction
    w_k: Fraction
    CV_T: Fraction
    CV_V: Fraction
    CV_R: Fraction
    S_k: Fraction
    U_k: Fraction
    IAS_k: Fraction
    URF_k: Fraction
    D_k: Fraction
    M_k: Fraction
    R_rev_k: Fraction
    U_star_k: Fraction
    C_k: Fraction
    P_k: Fraction
    B_k: Fraction
    N_gate: Fraction

    def __post_init__(self) -> None:
        for name, value in zip(
            TRANSPORT_COORDINATE_ORDER, self.as_tuple(), strict=True
        ):
            require_fraction(value, name)

    def as_tuple(self) -> tuple[Fraction, ...]:
        return tuple(getattr(self, name) for name in TRANSPORT_COORDINATE_ORDER)


class StructuralFactState(str, Enum):
    AVAILABLE = "available"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RegimeFact:
    """Categorical Reg_k retained outside numeric transport."""

    category: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.category, "Reg_k.category")
        sha256_digest(self.authority_receipt_sha256, "Reg_k authority receipt")


@dataclass(frozen=True, slots=True)
class SupportFloorFact:
    """Typed S_UF provider result retained outside numeric transport."""

    state: StructuralFactState
    value: Fraction | None
    authority_receipt_sha256: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, StructuralFactState):
            raise ReceiptError("S_UF state must be StructuralFactState")
        sha256_digest(self.authority_receipt_sha256, "S_UF authority receipt")
        if self.state is StructuralFactState.AVAILABLE:
            require_fraction(self.value, "S_UF.value")
            if self.reason is not None:
                raise ReceiptError("available S_UF cannot carry an unavailable reason")
        else:
            if self.value is not None:
                raise ReceiptError("unavailable S_UF cannot carry a numeric value")
            require_identifier(self.reason or "", "S_UF.reason")


@dataclass(frozen=True, slots=True)
class ResonanceFact:
    """Typed R_UF provider result retained outside numeric transport."""

    state: StructuralFactState
    value: CertifiedBall | None
    authority_receipt_sha256: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, StructuralFactState):
            raise ReceiptError("R_UF state must be StructuralFactState")
        sha256_digest(self.authority_receipt_sha256, "R_UF authority receipt")
        if self.state is StructuralFactState.AVAILABLE:
            if not isinstance(self.value, CertifiedBall):
                raise ReceiptError("available R_UF requires a certified ball")
            if self.reason is not None:
                raise ReceiptError("available R_UF cannot carry an unavailable reason")
        else:
            if self.value is not None:
                raise ReceiptError("unavailable R_UF cannot carry a numeric value")
            require_identifier(self.reason or "", "R_UF.reason")


class EvidenceValidityState(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class EvidenceValidity:
    """Typed validity; it never changes topology or fiber dimension."""

    state: EvidenceValidityState
    authority_receipt_sha256: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, EvidenceValidityState):
            raise ReceiptError("validity state must be EvidenceValidityState")
        sha256_digest(self.authority_receipt_sha256, "validity authority receipt")
        if self.state is EvidenceValidityState.VALID:
            if self.reason is not None:
                raise ReceiptError("valid evidence cannot carry an invalidity reason")
        else:
            require_identifier(self.reason or "", "validity.reason")


@dataclass(frozen=True, slots=True)
class EvidenceProvenance:
    provider_id: str
    source_epoch: str
    source_index: int
    source_timestamp: Fraction
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.provider_id, "provenance.provider_id")
        require_identifier(self.source_epoch, "provenance.source_epoch")
        if isinstance(self.source_index, bool) or not isinstance(self.source_index, int):
            raise ReceiptError("provenance.source_index must be an integer")
        if self.source_index < 0:
            raise ReceiptError("provenance.source_index cannot be negative")
        require_fraction(self.source_timestamp, "provenance.source_timestamp")
        sha256_digest(self.authority_receipt_sha256, "provenance authority receipt")


def transport_evidence_receipt_payload(
    *,
    lane_id: str,
    port_id: str,
    evidence_id: str,
    coordinates: TransportCoordinates19,
    regime: RegimeFact,
    support_floor: SupportFloorFact,
    resonance: ResonanceFact,
    validity: EvidenceValidity,
    provenance: EvidenceProvenance,
    raw_record_sha256: str,
) -> bytes:
    resonance_value = None if resonance.value is None else _ball_payload(resonance.value)
    return _canonical_bytes(
        {
            "coordinates": {
                name: _fraction_text(value)
                for name, value in zip(
                    TRANSPORT_COORDINATE_ORDER, coordinates.as_tuple(), strict=True
                )
            },
            "evidence_id": evidence_id,
            "lane_id": lane_id,
            "port_id": port_id,
            "provenance": {
                "authority_receipt_sha256": provenance.authority_receipt_sha256,
                "provider_id": provenance.provider_id,
                "source_epoch": provenance.source_epoch,
                "source_index": provenance.source_index,
                "source_timestamp": _fraction_text(provenance.source_timestamp),
            },
            "raw_record_sha256": raw_record_sha256,
            "Reg_k": {
                "authority_receipt_sha256": regime.authority_receipt_sha256,
                "category": regime.category,
            },
            "R_UF": {
                "authority_receipt_sha256": resonance.authority_receipt_sha256,
                "reason": resonance.reason,
                "state": resonance.state.value,
                "value": resonance_value,
            },
            "schema": "glew.field.transport_evidence.v1",
            "S_UF": {
                "authority_receipt_sha256": support_floor.authority_receipt_sha256,
                "reason": support_floor.reason,
                "state": support_floor.state.value,
                "value": (
                    None
                    if support_floor.value is None
                    else _fraction_text(support_floor.value)
                ),
            },
            "validity": {
                "authority_receipt_sha256": validity.authority_receipt_sha256,
                "reason": validity.reason,
                "state": validity.state.value,
            },
        }
    )


@dataclass(frozen=True, slots=True)
class PortTransportEvidence:
    """One full port record; raw source bytes and typed facts are preserved."""

    lane_id: str
    port_id: str
    evidence_id: str
    coordinates: TransportCoordinates19
    regime: RegimeFact
    support_floor: SupportFloorFact
    resonance: ResonanceFact
    validity: EvidenceValidity
    provenance: EvidenceProvenance
    raw_record: ReceiptRecord
    evidence_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, "lane_id")
        require_identifier(self.port_id, "port_id")
        require_identifier(self.evidence_id, "evidence_id")
        if not isinstance(self.coordinates, TransportCoordinates19):
            raise ReceiptError("transport evidence requires 19 typed coordinates")
        if not isinstance(self.raw_record, ReceiptRecord):
            raise ReceiptError("transport evidence requires preserved raw receipt bytes")
        sha256_digest(self.evidence_receipt_sha256, "evidence receipt")

    @property
    def key(self) -> tuple[str, str]:
        return (self.lane_id, self.port_id)

    def canonical_receipt_payload(self) -> bytes:
        return transport_evidence_receipt_payload(
            lane_id=self.lane_id,
            port_id=self.port_id,
            evidence_id=self.evidence_id,
            coordinates=self.coordinates,
            regime=self.regime,
            support_floor=self.support_floor,
            resonance=self.resonance,
            validity=self.validity,
            provenance=self.provenance,
            raw_record_sha256=self.raw_record.digest,
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        for name, digest in (
            ("Reg_k authority receipt", self.regime.authority_receipt_sha256),
            ("S_UF authority receipt", self.support_floor.authority_receipt_sha256),
            ("R_UF authority receipt", self.resonance.authority_receipt_sha256),
            ("validity authority receipt", self.validity.authority_receipt_sha256),
            ("provenance authority receipt", self.provenance.authority_receipt_sha256),
        ):
            receipt_registry.resolve(digest, name)
        mounted_raw = receipt_registry.resolve(self.raw_record.digest, "raw record")
        if mounted_raw != self.raw_record.payload:
            raise ReceiptError("preserved raw record differs from mounted bytes")
        mounted = receipt_registry.resolve(self.evidence_receipt_sha256, "evidence receipt")
        if mounted != self.canonical_receipt_payload():
            raise ReceiptError("transport evidence differs from its mounted receipt")


@dataclass(frozen=True, slots=True)
class PortFiber:
    lane_id: str
    port_id: str

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, "fiber.lane_id")
        require_identifier(self.port_id, "fiber.port_id")

    @property
    def key(self) -> tuple[str, str]:
        return (self.lane_id, self.port_id)


def field_topology_receipt_payload(
    topology_id: str, ordered_port_fibers: Sequence[PortFiber]
) -> bytes:
    return _canonical_bytes(
        {
            "coordinate_order": list(TRANSPORT_COORDINATE_ORDER),
            "field_dimension": FIBER_DIMENSION * len(ordered_port_fibers),
            "fiber_dimension": FIBER_DIMENSION,
            "ordered_port_fibers": [
                {"lane_id": fiber.lane_id, "port_id": fiber.port_id}
                for fiber in ordered_port_fibers
            ],
            "schema": "glew.field.topology.v1",
            "topology_id": topology_id,
        }
    )


@dataclass(frozen=True, slots=True)
class MountedFieldTopology:
    """Canonical ordered direct sum of mounted native-port fibers."""

    topology_id: str
    ordered_port_fibers: tuple[PortFiber, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.topology_id, "topology_id")
        sha256_digest(self.authority_receipt_sha256, "topology authority receipt")
        if len({fiber.key for fiber in self.ordered_port_fibers}) != len(
            self.ordered_port_fibers
        ):
            raise ReceiptError("mounted topology contains duplicate port fibers")
        if not all(isinstance(fiber, PortFiber) for fiber in self.ordered_port_fibers):
            raise ReceiptError("mounted topology contains a non-fiber value")

    @property
    def dimension(self) -> int:
        return FIBER_DIMENSION * len(self.ordered_port_fibers)

    @property
    def available(self) -> bool:
        return bool(self.ordered_port_fibers)

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "topology authority receipt"
        )
        expected = field_topology_receipt_payload(
            self.topology_id, self.ordered_port_fibers
        )
        if mounted != expected:
            raise ReceiptError("mounted field topology differs from its authority receipt")


@dataclass(frozen=True, slots=True)
class MappedPortFiber:
    fiber: PortFiber
    offset: int
    coordinates: tuple[Fraction, ...]
    evidence: PortTransportEvidence


@dataclass(frozen=True, slots=True)
class MapInjection:
    topology_id: str
    topology_authority_receipt_sha256: str
    vector: tuple[Fraction, ...]
    mapped_fibers: tuple[MappedPortFiber, ...]
    receipt_sha256: str
    receipt_payload: bytes

    @property
    def dimension(self) -> int:
        return len(self.vector)

    def verify(
        self,
        topology: MountedFieldTopology,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        topology.verify(receipt_registry)
        if self.topology_id != topology.topology_id:
            raise ReceiptError("MapInject event carries a different topology id")
        if self.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
            raise ReceiptError("MapInject event belongs to a different topology")
        if len(self.mapped_fibers) != len(topology.ordered_port_fibers):
            raise ReceiptError("MapInject event does not cover every topology fiber")
        for index, (mapped, declared) in enumerate(
            zip(self.mapped_fibers, topology.ordered_port_fibers, strict=True)
        ):
            mapped.evidence.verify(receipt_registry)
            if mapped.evidence.validity.state is not EvidenceValidityState.VALID:
                raise ReceiptError("invalid or unknown evidence has no MapInject authority")
            if mapped.fiber != declared or mapped.evidence.key != declared.key:
                raise ReceiptError("MapInject fiber order differs from mounted topology")
            if mapped.offset != index * FIBER_DIMENSION:
                raise ReceiptError("MapInject fiber offset is not the canonical direct sum offset")
            if mapped.coordinates != mapped.evidence.coordinates.as_tuple():
                raise ReceiptError("MapInject coordinates differ from exact port evidence")
        expected_vector = tuple(
            value for mapped in self.mapped_fibers for value in mapped.coordinates
        )
        if self.vector != expected_vector or len(self.vector) != topology.dimension:
            raise ReceiptError("MapInject vector is not the exact topology identity inclusion")
        expected_payload = _map_injection_payload(topology, self.mapped_fibers)
        if self.receipt_payload != expected_payload:
            raise ReceiptError("MapInject receipt payload is not canonical")
        if self.receipt_sha256 != receipt_sha256(expected_payload):
            raise ReceiptError("MapInject receipt digest does not match its canonical payload")


def _map_injection_payload(
    topology: MountedFieldTopology, mapped_fibers: Sequence[MappedPortFiber]
) -> bytes:
    return _canonical_bytes(
        {
            "field_dimension": topology.dimension,
            "map_operator": "exact_sparse_direct_identity_inclusion.v1",
            "mapped_fibers": [
                {
                    "evidence_receipt_sha256": mapped.evidence.evidence_receipt_sha256,
                    "lane_id": mapped.fiber.lane_id,
                    "offset": mapped.offset,
                    "port_id": mapped.fiber.port_id,
                    "values": [_fraction_text(value) for value in mapped.coordinates],
                    "validity": mapped.evidence.validity.state.value,
                }
                for mapped in mapped_fibers
            ],
            "schema": "glew.field.map_injection.v1",
            "topology_authority_receipt_sha256": topology.authority_receipt_sha256,
            "topology_id": topology.topology_id,
        }
    )


def map_inject(
    topology: MountedFieldTopology,
    evidence_records: Sequence[PortTransportEvidence],
    receipt_registry: ReceiptRegistry,
) -> MapInjection:
    """Apply exact identity inclusion into every declared port fiber."""

    if not isinstance(topology, MountedFieldTopology):
        raise ReceiptError("MapInject requires a mounted field topology")
    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("MapInject requires an immutable receipt registry")
    topology.verify(receipt_registry)
    if not topology.available:
        raise ReceiptError("empty genesis topology has dimension zero and unavailable MapInject")

    by_key: dict[tuple[str, str], PortTransportEvidence] = {}
    for evidence in evidence_records:
        if not isinstance(evidence, PortTransportEvidence):
            raise ReceiptError("MapInject accepts only typed port evidence")
        if evidence.key in by_key:
            raise ReceiptError(f"duplicate transport evidence for {evidence.key!r}")
        evidence.verify(receipt_registry)
        if evidence.validity.state is not EvidenceValidityState.VALID:
            raise ReceiptError(
                "invalid or unknown evidence preserves its topology fiber but has no MapInject authority"
            )
        by_key[evidence.key] = evidence

    topology_keys = tuple(fiber.key for fiber in topology.ordered_port_fibers)
    if set(by_key) != set(topology_keys):
        missing = tuple(key for key in topology_keys if key not in by_key)
        extra = tuple(key for key in by_key if key not in set(topology_keys))
        raise ReceiptError(
            f"MapInject evidence must exactly cover mounted topology; missing={missing!r}, extra={extra!r}"
        )

    mapped = tuple(
        MappedPortFiber(
            fiber=fiber,
            offset=index * FIBER_DIMENSION,
            coordinates=by_key[fiber.key].coordinates.as_tuple(),
            evidence=by_key[fiber.key],
        )
        for index, fiber in enumerate(topology.ordered_port_fibers)
    )
    vector = tuple(value for fiber in mapped for value in fiber.coordinates)
    payload = _map_injection_payload(topology, mapped)
    result = MapInjection(
        topology_id=topology.topology_id,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        vector=vector,
        mapped_fibers=mapped,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    result.verify(topology, receipt_registry)
    return result


@dataclass(frozen=True, slots=True)
class HamiltonianEntry:
    row: int
    column: int
    value: ExactComplex

    def __post_init__(self) -> None:
        for name, value in (("row", self.row), ("column", self.column)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ReceiptError(f"Hamiltonian {name} must be a nonnegative integer")
        if not isinstance(self.value, ExactComplex) or self.value.is_zero:
            raise ReceiptError("sparse Hamiltonian entries must be exact and nonzero")


@dataclass(frozen=True, slots=True)
class LocalRate:
    index: int
    growth: Fraction
    decay: Fraction

    def __post_init__(self) -> None:
        if isinstance(self.index, bool) or not isinstance(self.index, int) or self.index < 0:
            raise ReceiptError("local-rate index must be a nonnegative integer")
        require_fraction(self.growth, "local growth")
        require_fraction(self.decay, "local decay")
        if self.growth < 0 or self.decay < 0:
            raise ReceiptError("local growth and decay coefficients cannot be negative")
        if self.growth == 0 and self.decay == 0:
            raise ReceiptError("zero local rates must be omitted from sparse authority")


@dataclass(frozen=True, slots=True)
class SourceCoefficient:
    index: int
    value: ExactComplex

    def __post_init__(self) -> None:
        if isinstance(self.index, bool) or not isinstance(self.index, int) or self.index < 0:
            raise ReceiptError("source index must be a nonnegative integer")
        if not isinstance(self.value, ExactComplex) or self.value.is_zero:
            raise ReceiptError("zero source coefficients must be omitted")


def _validate_sparse_indices(
    *,
    dimension: int,
    hamiltonian: Sequence[HamiltonianEntry],
    local_rates: Sequence[LocalRate],
    source: Sequence[SourceCoefficient],
) -> None:
    h_keys = tuple((entry.row, entry.column) for entry in hamiltonian)
    rate_keys = tuple(rate.index for rate in local_rates)
    source_keys = tuple(coefficient.index for coefficient in source)
    if h_keys != tuple(sorted(h_keys)) or len(set(h_keys)) != len(h_keys):
        raise ReceiptError("Hamiltonian entries must be unique in canonical row-column order")
    if rate_keys != tuple(sorted(rate_keys)) or len(set(rate_keys)) != len(rate_keys):
        raise ReceiptError("local rates must be unique in canonical index order")
    if source_keys != tuple(sorted(source_keys)) or len(set(source_keys)) != len(source_keys):
        raise ReceiptError("source coefficients must be unique in canonical index order")
    if any(row >= dimension or column >= dimension for row, column in h_keys):
        raise ReceiptError("Hamiltonian index lies outside mounted topology")
    if any(index >= dimension for index in (*rate_keys, *source_keys)):
        raise ReceiptError("local or source index lies outside mounted topology")


def _validate_hermitian(hamiltonian: Sequence[HamiltonianEntry]) -> None:
    values = {(entry.row, entry.column): entry.value for entry in hamiltonian}
    for (row, column), value in values.items():
        if values.get((column, row), ExactComplex(Fraction(0))) != value.conjugate():
            raise ReceiptError("Hamiltonian authority is not exactly Hermitian")


def canonical_component_partition(
    dimension: int, hamiltonian: Sequence[HamiltonianEntry]
) -> tuple[tuple[int, ...], ...]:
    """Return exact generator connected components in canonical index order."""

    if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 0:
        raise ReceiptError("field dimension must be a nonnegative integer")
    neighbors = [set() for _ in range(dimension)]
    for entry in hamiltonian:
        if entry.row != entry.column:
            neighbors[entry.row].add(entry.column)
            neighbors[entry.column].add(entry.row)
    unvisited = set(range(dimension))
    components: list[tuple[int, ...]] = []
    while unvisited:
        start = min(unvisited)
        stack = [start]
        component: set[int] = set()
        while stack:
            index = stack.pop()
            if index in component:
                continue
            component.add(index)
            stack.extend(sorted(neighbors[index] - component, reverse=True))
        unvisited -= component
        components.append(tuple(sorted(component)))
    return tuple(components)


def evolution_authority_receipt_payload(
    *,
    authority_id: str,
    physical_profile_receipt_sha256: str,
    topology_authority_receipt_sha256: str,
    map_injection_receipt_sha256: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    source_time_unit: str,
    hbar: Fraction,
    hamiltonian: Sequence[HamiltonianEntry],
    local_rates: Sequence[LocalRate],
    source: Sequence[SourceCoefficient],
    component_partition: Sequence[Sequence[int]],
    max_connected_component_dimension: int,
    precision_bits: int,
) -> bytes:
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "backend": {
                "flint": FLINT_VERSION,
                "precision_bits": precision_bits,
                "python_flint": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            },
            "component_partition": [list(component) for component in component_partition],
            "equation": "dpsi_dt=(diag(growth-decay)-i*H/hbar)*psi+injection_vector/delta",
            "hamiltonian": [
                {"column": entry.column, "row": entry.row, "value": _complex_payload(entry.value)}
                for entry in hamiltonian
            ],
            "hbar": _fraction_text(hbar),
            "local_rates": [
                {
                    "decay": _fraction_text(rate.decay),
                    "growth": _fraction_text(rate.growth),
                    "index": rate.index,
                }
                for rate in local_rates
            ],
            "map_injection_receipt_sha256": map_injection_receipt_sha256,
            "max_connected_component_dimension": max_connected_component_dimension,
            "physical_profile_receipt_sha256": physical_profile_receipt_sha256,
            "schema": "glew.field.piecewise_affine_evolution_authority.v1",
            "solver": "canonical_sparse_components_augmented_acb_matrix_exponential.v1",
            "source": [
                {"index": coefficient.index, "value": _complex_payload(coefficient.value)}
                for coefficient in source
            ],
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "source_time_unit": source_time_unit,
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class FieldEvolutionAuthority:
    """Receipt-bound exact coefficients for one piecewise-constant interval."""

    authority_id: str
    physical_profile_receipt_sha256: str
    topology_authority_receipt_sha256: str
    map_injection_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    source_time_unit: str
    hbar: Fraction
    hamiltonian: tuple[HamiltonianEntry, ...]
    local_rates: tuple[LocalRate, ...]
    source: tuple[SourceCoefficient, ...]
    max_connected_component_dimension: int
    precision_bits: int
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.authority_id, "evolution authority_id")
        require_identifier(self.source_time_unit, "source_time_unit")
        sha256_digest(
            self.physical_profile_receipt_sha256,
            "evolution physical profile receipt",
        )
        sha256_digest(
            self.topology_authority_receipt_sha256,
            "evolution topology authority receipt",
        )
        sha256_digest(self.map_injection_receipt_sha256, "MapInject receipt")
        sha256_digest(self.authority_receipt_sha256, "evolution authority receipt")
        require_fraction(self.source_time_start, "source_time_start")
        require_fraction(self.source_time_end, "source_time_end")
        require_fraction(self.hbar, "hbar")
        if self.source_time_end <= self.source_time_start:
            raise ReceiptError("field evolution requires an actual positive source-time delta")
        if self.hbar <= 0:
            raise ReceiptError("hbar must be exact and strictly positive")
        if (
            isinstance(self.max_connected_component_dimension, bool)
            or not isinstance(self.max_connected_component_dimension, int)
            or self.max_connected_component_dimension <= 0
        ):
            raise ReceiptError("component resource bound must be a positive integer")
        if (
            isinstance(self.precision_bits, bool)
            or not isinstance(self.precision_bits, int)
            or self.precision_bits <= 0
        ):
            raise ReceiptError("Arb working precision must be a positive integer")

    @property
    def delta(self) -> Fraction:
        return self.source_time_end - self.source_time_start

    def verify(
        self,
        topology: MountedFieldTopology,
        injection: MapInjection,
        receipt_registry: ReceiptRegistry,
    ) -> tuple[tuple[int, ...], ...]:
        topology.verify(receipt_registry)
        injection.verify(topology, receipt_registry)
        receipt_registry.resolve(
            self.physical_profile_receipt_sha256,
            "evolution physical profile receipt",
        )
        if self.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
            raise ReceiptError("evolution authority belongs to a different topology")
        if self.map_injection_receipt_sha256 != injection.receipt_sha256:
            raise ReceiptError("evolution authority belongs to a different MapInject event")
        dimension = topology.dimension
        _validate_sparse_indices(
            dimension=dimension,
            hamiltonian=self.hamiltonian,
            local_rates=self.local_rates,
            source=self.source,
        )
        _validate_hermitian(self.hamiltonian)
        components = canonical_component_partition(dimension, self.hamiltonian)
        if any(
            len(component) > self.max_connected_component_dimension
            for component in components
        ):
            raise ReceiptError("exact connected component exceeds mounted resource authority")

        expected_source = tuple(
            SourceCoefficient(index, ExactComplex(value / self.delta))
            for index, value in enumerate(injection.vector)
            if value != 0
        )
        if self.source != expected_source:
            raise ReceiptError(
                "source coefficients are not the exact integrated MapInject charge divided by delta"
            )

        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "evolution authority receipt"
        )
        expected = evolution_authority_receipt_payload(
            authority_id=self.authority_id,
            physical_profile_receipt_sha256=self.physical_profile_receipt_sha256,
            topology_authority_receipt_sha256=self.topology_authority_receipt_sha256,
            map_injection_receipt_sha256=self.map_injection_receipt_sha256,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            source_time_unit=self.source_time_unit,
            hbar=self.hbar,
            hamiltonian=self.hamiltonian,
            local_rates=self.local_rates,
            source=self.source,
            component_partition=components,
            max_connected_component_dimension=self.max_connected_component_dimension,
            precision_bits=self.precision_bits,
        )
        if mounted != expected:
            raise ReceiptError("field evolution coefficients differ from mounted authority")
        return components


@dataclass(frozen=True, slots=True)
class CertifiedComplexBall:
    real: CertifiedBall
    imag: CertifiedBall


@dataclass(frozen=True, slots=True)
class ExactFieldState:
    topology_authority_receipt_sha256: str
    source_time: Fraction
    amplitudes: tuple[ExactComplex, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        sha256_digest(self.topology_authority_receipt_sha256, "state topology receipt")
        sha256_digest(self.authority_receipt_sha256, "exact state authority receipt")
        require_fraction(self.source_time, "state source_time")
        if not all(isinstance(value, ExactComplex) for value in self.amplitudes):
            raise ReceiptError("exact field state contains a non-exact amplitude")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "exact state authority receipt"
        )
        expected = exact_field_state_receipt_payload(
            self.topology_authority_receipt_sha256,
            self.source_time,
            self.amplitudes,
        )
        if mounted != expected:
            raise ReceiptError("exact initial state differs from its mounted authority")


@dataclass(frozen=True, slots=True)
class CertifiedFieldState:
    topology_authority_receipt_sha256: str
    source_time: Fraction
    amplitudes: tuple[CertifiedComplexBall, ...]
    receipt_sha256: str

    def __post_init__(self) -> None:
        sha256_digest(self.topology_authority_receipt_sha256, "state topology receipt")
        sha256_digest(self.receipt_sha256, "certified state receipt")
        require_fraction(self.source_time, "state source_time")

    def verify(self) -> None:
        expected = _state_payload(
            self.topology_authority_receipt_sha256,
            self.source_time,
            self.amplitudes,
        )
        if receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("certified initial state differs from its canonical receipt")


def exact_field_state_receipt_payload(
    topology_authority_receipt_sha256: str,
    source_time: Fraction,
    amplitudes: Sequence[ExactComplex],
) -> bytes:
    sha256_digest(topology_authority_receipt_sha256, "state topology receipt")
    require_fraction(source_time, "state source_time")
    if not all(isinstance(value, ExactComplex) for value in amplitudes):
        raise ReceiptError("exact state receipt contains a non-exact amplitude")
    return _canonical_bytes(
        {
            "amplitudes": [_complex_payload(value) for value in amplitudes],
            "schema": "glew.field.exact_state_authority.v1",
            "source_time": _fraction_text(source_time),
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


def _dyadic_fraction(ball: CertifiedBall, lower: bool) -> Fraction:
    mantissa = ball.lower_mantissa if lower else ball.upper_mantissa
    exponent = ball.lower_exponent if lower else ball.upper_exponent
    return Fraction(mantissa) * Fraction(2) ** exponent


def _dyadic_pair(value: Fraction) -> tuple[int, int]:
    denominator = value.denominator
    if denominator & (denominator - 1):
        raise ReceiptError("certified endpoint is not dyadic")
    exponent = -(denominator.bit_length() - 1)
    return (value.numerator, exponent)


def _arb_from_certified(flint, ball: CertifiedBall):
    lower = _dyadic_fraction(ball, True)
    upper = _dyadic_fraction(ball, False)
    midpoint = (lower + upper) / 2
    radius = (upper - lower) / 2
    return flint.arb(_dyadic_pair(midpoint), _dyadic_pair(radius))


def _acb_exact(flint, value: ExactComplex):
    return flint.acb(
        arb_fraction(flint, value.real), arb_fraction(flint, value.imag)
    )


def _acb_state_value(flint, value: ExactComplex | CertifiedComplexBall):
    if isinstance(value, ExactComplex):
        return _acb_exact(flint, value)
    if isinstance(value, CertifiedComplexBall):
        return flint.acb(
            _arb_from_certified(flint, value.real),
            _arb_from_certified(flint, value.imag),
        )
    raise ReceiptError("field state contains an unsupported amplitude type")


def _state_payload(
    topology_receipt: str,
    source_time: Fraction,
    amplitudes: Sequence[CertifiedComplexBall],
) -> bytes:
    return _canonical_bytes(
        {
            "amplitudes": [
                {"imag": _ball_payload(value.imag), "real": _ball_payload(value.real)}
                for value in amplitudes
            ],
            "schema": "glew.field.certified_state.v1",
            "source_time": _fraction_text(source_time),
            "topology_authority_receipt_sha256": topology_receipt,
        }
    )


@dataclass(frozen=True, slots=True)
class FieldEvolutionReceipt:
    authority_receipt_sha256: str
    physical_profile_receipt_sha256: str
    topology_authority_receipt_sha256: str
    map_injection_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    component_partition: tuple[tuple[int, ...], ...]
    norm_before_squared: CertifiedBall
    norm_after_squared: CertifiedBall
    result_state_receipt_sha256: str
    backend_python_flint: str
    backend_flint: str
    backend_wheel_sha256: str
    working_precision_bits: int
    receipt_sha256: str
    receipt_payload: bytes


@dataclass(frozen=True, slots=True)
class FieldEvolutionResult:
    state: CertifiedFieldState
    receipt: FieldEvolutionReceipt


def _norm_squared(flint, values: Sequence[object]):
    total = flint.arb(0)
    for value in values:
        total += value.real * value.real + value.imag * value.imag
    if not total.is_finite():
        raise ReceiptError("field norm is nonfinite or indeterminate")
    return total


def _evolution_receipt_payload(
    *,
    authority: FieldEvolutionAuthority,
    components: Sequence[Sequence[int]],
    norm_before: CertifiedBall,
    norm_after: CertifiedBall,
    state_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "authority_receipt_sha256": authority.authority_receipt_sha256,
            "backend": {
                "flint": FLINT_VERSION,
                "precision_bits": authority.precision_bits,
                "python_flint": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            },
            "component_partition": [list(component) for component in components],
            "map_injection_receipt_sha256": authority.map_injection_receipt_sha256,
            "physical_profile_receipt_sha256": authority.physical_profile_receipt_sha256,
            "norm_after_squared": _ball_payload(norm_after),
            "norm_before_squared": _ball_payload(norm_before),
            "result_state_receipt_sha256": state_receipt_sha256,
            "schema": "glew.field.certified_evolution_receipt.v1",
            "solver": "canonical_sparse_components_augmented_acb_matrix_exponential.v1",
            "source_time_end": _fraction_text(authority.source_time_end),
            "source_time_start": _fraction_text(authority.source_time_start),
            "topology_authority_receipt_sha256": authority.topology_authority_receipt_sha256,
        }
    )


def evolve_field(
    *,
    topology: MountedFieldTopology,
    injection: MapInjection,
    authority: FieldEvolutionAuthority,
    initial_state: ExactFieldState | CertifiedFieldState,
    receipt_registry: ReceiptRegistry,
) -> FieldEvolutionResult:
    """Apply one exact-time, receipt-bound, certified affine field step."""

    if not topology.available:
        raise ReceiptError("empty genesis topology has no field evolution authority")
    if injection.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
        raise ReceiptError("MapInject event belongs to a different topology")
    if initial_state.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
        raise ReceiptError("initial field state belongs to a different topology")
    if initial_state.source_time != authority.source_time_start:
        raise ReceiptError("initial field state is not at the authority source time")
    if len(initial_state.amplitudes) != topology.dimension:
        raise ReceiptError("initial field-state dimension differs from mounted topology")
    if isinstance(initial_state, ExactFieldState):
        initial_state.verify(receipt_registry)
    elif isinstance(initial_state, CertifiedFieldState):
        initial_state.verify()
    else:
        raise ReceiptError("field evolution requires a typed exact or certified state")
    components = authority.verify(topology, injection, receipt_registry)

    flint = load_pinned_flint()
    with flint.ctx.workprec(authority.precision_bits):
        before = tuple(_acb_state_value(flint, value) for value in initial_state.amplitudes)
        if not all(value.is_finite() for value in before):
            raise ReceiptError("initial field state is nonfinite or indeterminate")
        result = [None] * topology.dimension
        h_values = {
            (entry.row, entry.column): entry.value for entry in authority.hamiltonian
        }
        rates = {rate.index: rate for rate in authority.local_rates}
        source = {coefficient.index: coefficient.value for coefficient in authority.source}
        delta = arb_fraction(flint, authority.delta)
        hbar = arb_fraction(flint, authority.hbar)

        for component in components:
            local_index = {global_index: i for i, global_index in enumerate(component)}
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
                    h_value = h_values.get((global_row, global_column))
                    if h_value is not None:
                        augmented[row, local_index[global_column]] += (
                            -flint.acb(0, 1) * _acb_exact(flint, h_value) / hbar
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
                raise ReceiptError("Arb matrix exponential is nonfinite or indeterminate")
            initial_augmented = flint.acb_mat(
                size + 1,
                1,
                [*(before[index] for index in component), flint.acb(1)],
            )
            evolved = transition * initial_augmented
            for row, global_index in enumerate(component):
                value = evolved[row, 0]
                if not value.is_finite():
                    raise ReceiptError("evolved field component is nonfinite or indeterminate")
                result[global_index] = value

        if any(value is None for value in result):
            raise ReceiptError("component factorization did not cover the mounted field")
        before_norm = canonical_ball(_norm_squared(flint, before), authority.precision_bits)
        after_norm = canonical_ball(_norm_squared(flint, result), authority.precision_bits)
        certified = tuple(
            CertifiedComplexBall(
                real=canonical_ball(value.real, authority.precision_bits),
                imag=canonical_ball(value.imag, authority.precision_bits),
            )
            for value in result
        )

    state_payload = _state_payload(
        topology.authority_receipt_sha256, authority.source_time_end, certified
    )
    state_digest = hashlib.sha256(state_payload).hexdigest()
    state = CertifiedFieldState(
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        source_time=authority.source_time_end,
        amplitudes=certified,
        receipt_sha256=state_digest,
    )
    receipt_payload = _evolution_receipt_payload(
        authority=authority,
        components=components,
        norm_before=before_norm,
        norm_after=after_norm,
        state_receipt_sha256=state_digest,
    )
    receipt_digest = hashlib.sha256(receipt_payload).hexdigest()
    receipt = FieldEvolutionReceipt(
        authority_receipt_sha256=authority.authority_receipt_sha256,
        physical_profile_receipt_sha256=authority.physical_profile_receipt_sha256,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        map_injection_receipt_sha256=injection.receipt_sha256,
        source_time_start=authority.source_time_start,
        source_time_end=authority.source_time_end,
        component_partition=components,
        norm_before_squared=before_norm,
        norm_after_squared=after_norm,
        result_state_receipt_sha256=state_digest,
        backend_python_flint=PYTHON_FLINT_VERSION,
        backend_flint=FLINT_VERSION,
        backend_wheel_sha256=PYTHON_FLINT_WHEEL_SHA256,
        working_precision_bits=authority.precision_bits,
        receipt_sha256=receipt_digest,
        receipt_payload=receipt_payload,
    )
    return FieldEvolutionResult(state=state, receipt=receipt)


def _ball_contains_fraction(ball: CertifiedBall, value: Fraction) -> bool:
    lower = Fraction(ball.lower_mantissa) * Fraction(2) ** ball.lower_exponent
    upper = Fraction(ball.upper_mantissa) * Fraction(2) ** ball.upper_exponent
    return lower <= value <= upper


def field_conformance() -> dict[str, object]:
    """Execute the immutable field-operator conformance vector.

    This proves the operator bundle, not the existence of a live mounted field.
    The vector deliberately uses a two-unit event interval and integrated charge
    3/2 so it detects the incorrect ``J=e`` duration scaling.
    """

    flint = load_pinned_flint()
    if len(TRANSPORT_COORDINATE_ORDER) != 19 or len(
        set(TRANSPORT_COORDINATE_ORDER)
    ) != 19:
        raise ReceiptError("field conformance coordinate authority is not exact 19")

    profile_payload = b"glew.field.conformance.profile.v1"
    regime_payload = b"glew.field.conformance.Reg_k.v1"
    support_payload = b"glew.field.conformance.S_UF.v1"
    resonance_payload = b"glew.field.conformance.R_UF.v1"
    validity_payload = b"glew.field.conformance.validity.v1"
    provenance_payload = b"glew.field.conformance.provenance.v1"
    physical_profile_payload = b"glew.field.conformance.physical_profile.v1"
    raw_payload = b"glew.field.conformance.raw.port.v1"

    empty_topology_payload = field_topology_receipt_payload("empty-genesis", ())
    empty_topology = MountedFieldTopology(
        "empty-genesis", (), receipt_sha256(empty_topology_payload)
    )
    fiber = PortFiber("language", "typed")
    topology_payload = field_topology_receipt_payload("conformance-one-port", (fiber,))
    topology = MountedFieldTopology(
        "conformance-one-port", (fiber,), receipt_sha256(topology_payload)
    )
    coordinates = TransportCoordinates19(
        Fraction(3, 2), *(Fraction(0) for _ in range(FIBER_DIMENSION - 1))
    )
    regime = RegimeFact("conformance", receipt_sha256(regime_payload))
    support = SupportFloorFact(
        StructuralFactState.AVAILABLE,
        Fraction(1),
        receipt_sha256(support_payload),
    )
    resonance = ResonanceFact(
        StructuralFactState.AVAILABLE,
        CertifiedBall(1, 0, 1, 0, 256),
        receipt_sha256(resonance_payload),
    )
    validity = EvidenceValidity(
        EvidenceValidityState.VALID, receipt_sha256(validity_payload)
    )
    provenance = EvidenceProvenance(
        "conformance.provider",
        "conformance-epoch",
        0,
        Fraction(5),
        receipt_sha256(provenance_payload),
    )
    raw_record = ReceiptRecord(receipt_sha256(raw_payload), raw_payload)
    evidence_payload = transport_evidence_receipt_payload(
        lane_id=fiber.lane_id,
        port_id=fiber.port_id,
        evidence_id="conformance-evidence",
        coordinates=coordinates,
        regime=regime,
        support_floor=support,
        resonance=resonance,
        validity=validity,
        provenance=provenance,
        raw_record_sha256=raw_record.digest,
    )
    evidence = PortTransportEvidence(
        fiber.lane_id,
        fiber.port_id,
        "conformance-evidence",
        coordinates,
        regime,
        support,
        resonance,
        validity,
        provenance,
        raw_record,
        receipt_sha256(evidence_payload),
    )
    base_payloads = (
        empty_topology_payload,
        topology_payload,
        regime_payload,
        support_payload,
        resonance_payload,
        validity_payload,
        provenance_payload,
        physical_profile_payload,
        raw_payload,
        evidence_payload,
    )
    base_registry = ReceiptRegistry.from_payloads(
        profile_payload=profile_payload,
        receipt_payloads=base_payloads,
    )
    empty_topology.verify(base_registry)
    injection = map_inject(topology, (evidence,), base_registry)
    source_time_start = Fraction(5)
    source_time_end = Fraction(7)
    delta = source_time_end - source_time_start
    source = (SourceCoefficient(0, ExactComplex(Fraction(3, 2) / delta)),)
    components = canonical_component_partition(topology.dimension, ())
    authority_payload = evolution_authority_receipt_payload(
        authority_id="conformance-step",
        physical_profile_receipt_sha256=receipt_sha256(physical_profile_payload),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        map_injection_receipt_sha256=injection.receipt_sha256,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        source_time_unit="structural_second",
        hbar=Fraction(1),
        hamiltonian=(),
        local_rates=(),
        source=source,
        component_partition=components,
        max_connected_component_dimension=1,
        precision_bits=256,
    )
    authority = FieldEvolutionAuthority(
        "conformance-step",
        receipt_sha256(physical_profile_payload),
        topology.authority_receipt_sha256,
        injection.receipt_sha256,
        source_time_start,
        source_time_end,
        "structural_second",
        Fraction(1),
        (),
        (),
        source,
        1,
        256,
        receipt_sha256(authority_payload),
    )
    initial_amplitudes = (ExactComplex(Fraction(0)),) * topology.dimension
    initial_payload = exact_field_state_receipt_payload(
        topology.authority_receipt_sha256,
        source_time_start,
        initial_amplitudes,
    )
    initial_state = ExactFieldState(
        topology.authority_receipt_sha256,
        source_time_start,
        initial_amplitudes,
        receipt_sha256(initial_payload),
    )
    complete_registry = ReceiptRegistry.from_payloads(
        profile_payload=profile_payload,
        receipt_payloads=(*base_payloads, authority_payload, initial_payload),
    )
    result = evolve_field(
        topology=topology,
        injection=injection,
        authority=authority,
        initial_state=initial_state,
        receipt_registry=complete_registry,
    )
    if injection.vector != coordinates.as_tuple():
        raise ReceiptError("field conformance direct identity inclusion failed")
    if not _ball_contains_fraction(result.state.amplitudes[0].real, Fraction(3, 2)):
        raise ReceiptError("field conformance integrated event charge failed")
    if not _ball_contains_fraction(result.state.amplitudes[0].imag, Fraction(0)):
        raise ReceiptError("field conformance introduced an unauthorized imaginary source")

    body: dict[str, object] = {
        "backend": {
            "flint": getattr(flint, "__FLINT_VERSION__", None),
            "precision_bits": 256,
            "python_flint": getattr(flint, "__version__", None),
            "threads": getattr(flint.ctx, "threads", None),
            "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
        },
        "coordinate_order": list(TRANSPORT_COORDINATE_ORDER),
        "empty_genesis": {
            "available": empty_topology.available,
            "dimension": empty_topology.dimension,
            "topology_receipt_sha256": empty_topology.authority_receipt_sha256,
        },
        "live_mounted_topology": False,
        "one_port_vector": {
            "dimension": injection.dimension,
            "evolution_receipt_sha256": result.receipt.receipt_sha256,
            "expected_integrated_charge": "3/2",
            "map_injection_receipt_sha256": injection.receipt_sha256,
            "physical_profile_receipt_sha256": authority.physical_profile_receipt_sha256,
            "result_state_receipt_sha256": result.state.receipt_sha256,
            "topology_receipt_sha256": topology.authority_receipt_sha256,
        },
        "schema": "glew.field.operator_conformance.v1",
        "status": "operator_conformant_no_live_mounted_topology",
    }
    report = dict(body)
    report["report_sha256"] = receipt_sha256(_canonical_bytes(body))
    return report
