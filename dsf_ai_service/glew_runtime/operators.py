"""Exact support-floor and certified cross-port resonance operators."""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping, Sequence

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
    EvidenceStream,
    ReceiptError,
    ReceiptRegistry,
    require_fraction,
    require_identifier,
    sha256_digest,
)


PortKey = tuple[str, str]


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


def causal_grid_receipt_payload(
    grid_id: str,
    timestamps: Sequence[Fraction],
    positive_weights: Sequence[Fraction],
) -> bytes:
    return _canonical_bytes(
        {
            "grid_id": grid_id,
            "positive_weights": [_fraction_text(value) for value in positive_weights],
            "schema": "glew.common_causal_grid.v1",
            "timestamps": [_fraction_text(value) for value in timestamps],
        }
    )


@dataclass(frozen=True, slots=True)
class CausalGrid:
    """Signed common gate grid; weights are authority inputs, never inferred."""

    grid_id: str
    timestamps: tuple[Fraction, ...]
    positive_weights: tuple[Fraction, ...]
    grid_receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.grid_id, str) or not self.grid_id:
            raise ReceiptError("causal grid requires a grid_id")
        sha256_digest(self.grid_receipt_sha256, "grid_receipt_sha256")
        if not self.timestamps or len(self.timestamps) != len(self.positive_weights):
            raise ReceiptError("causal grid requires equally sized timestamps and weights")
        previous: Fraction | None = None
        for timestamp, weight in zip(self.timestamps, self.positive_weights, strict=True):
            require_fraction(timestamp, "grid.timestamp")
            require_fraction(weight, "grid.weight")
            if weight <= 0:
                raise ReceiptError("causal-grid weights must be exactly positive")
            if previous is not None and timestamp <= previous:
                raise ReceiptError("causal-grid timestamps must increase strictly")
            previous = timestamp

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        mounted = receipt_registry.resolve(self.grid_receipt_sha256, "grid_receipt_sha256")
        expected = causal_grid_receipt_payload(
            self.grid_id, self.timestamps, self.positive_weights
        )
        if mounted != expected:
            raise ReceiptError("causal grid values do not match the mounted grid receipt")


def support_domain_receipt_payload(
    domain_id: str, required_port_keys: Sequence[PortKey]
) -> bytes:
    return _canonical_bytes(
        {
            "domain_id": domain_id,
            "required_port_keys": [list(key) for key in required_port_keys],
            "schema": "glew.mounted_support_domain.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class MountedSupportDomain:
    """Profile-mounted S_UF selection; observations never choose the subset."""

    domain_id: str
    required_port_keys: tuple[PortKey, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.domain_id, "domain_id")
        sha256_digest(self.authority_receipt_sha256, "authority_receipt_sha256")
        if not self.required_port_keys:
            raise ReceiptError("mounted support domain cannot be empty")
        if len(set(self.required_port_keys)) != len(self.required_port_keys):
            raise ReceiptError("mounted support ports must be unique")
        for lane_id, port_id in self.required_port_keys:
            require_identifier(lane_id, "required lane_id")
            require_identifier(port_id, "required port_id")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "support_domain_authority_receipt"
        )
        expected = support_domain_receipt_payload(self.domain_id, self.required_port_keys)
        if mounted != expected:
            raise ReceiptError("support domain does not match its mounted authority receipt")


@dataclass(frozen=True, slots=True)
class PortSupportFact:
    port_key: PortKey
    support_floor: Fraction
    required: bool


@dataclass(frozen=True, slots=True)
class SupportFloor:
    """S_UF meet plus every independently retained per-port floor fact."""

    value: Fraction
    port_facts: tuple[PortSupportFact, ...]
    required_port_keys: tuple[PortKey, ...]
    domain_authority_receipt_sha256: str
    grid_id: str


def _stream_map(
    streams: Sequence[EvidenceStream], receipt_registry: ReceiptRegistry
) -> dict[PortKey, EvidenceStream]:
    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("a mounted immutable receipt registry is required")
    mapped: dict[PortKey, EvidenceStream] = {}
    for stream in streams:
        if not isinstance(stream, EvidenceStream):
            raise ReceiptError("operators accept only receipted EvidenceStream values")
        if stream.key in mapped:
            raise ReceiptError(f"duplicate evidence stream for port {stream.key!r}")
        if stream.profile_binding_sha256 != receipt_registry.profile_binding_sha256:
            raise ReceiptError("evidence stream belongs to a different profile binding")
        receipt_registry.resolve(
            stream.calibration_receipt_sha256, "calibration_receipt_sha256"
        )
        receipt_registry.resolve(
            stream.relevance_receipt_sha256, "relevance_receipt_sha256"
        )
        mapped[stream.key] = stream
    return mapped


def _aligned_samples(stream: EvidenceStream, grid: CausalGrid):
    if tuple(sample.timestamp for sample in stream.samples) != grid.timestamps:
        raise ReceiptError(
            f"port {stream.key!r} does not match the common causal grid; interpolation is forbidden"
        )
    return stream.samples


def compute_support_floor(
    streams: Sequence[EvidenceStream],
    grid: CausalGrid,
    mounted_domain: MountedSupportDomain,
    receipt_registry: ReceiptRegistry,
) -> SupportFloor:
    """Compute the finite lattice infimum authorized for S_UF.

    Every supplied port gets its own exact floor.  Only the explicitly required
    port set enters the meet.  An empty required set is undefined, not zero.
    """

    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("a mounted immutable receipt registry is required")
    grid.verify(receipt_registry)
    if not isinstance(mounted_domain, MountedSupportDomain):
        raise ReceiptError("S_UF requires a mounted support domain")
    mounted_domain.verify(receipt_registry)
    mapped = _stream_map(streams, receipt_registry)
    required = mounted_domain.required_port_keys
    missing = tuple(key for key in required if key not in mapped)
    if missing:
        raise ReceiptError(f"required S_UF evidence is unavailable: {missing!r}")

    required_set = set(required)
    port_facts = tuple(
        PortSupportFact(
            port_key=key,
            support_floor=min(sample.relevance for sample in _aligned_samples(stream, grid)),
            required=key in required_set,
        )
        for key, stream in mapped.items()
    )
    facts_by_key = {fact.port_key: fact for fact in port_facts}
    value = min(facts_by_key[key].support_floor for key in required)
    return SupportFloor(
        value=value,
        port_facts=port_facts,
        required_port_keys=required,
        domain_authority_receipt_sha256=mounted_domain.authority_receipt_sha256,
        grid_id=grid.grid_id,
    )


@dataclass(frozen=True, slots=True)
class RequiredEdge:
    left_port_key: PortKey
    right_port_key: PortKey

    def __post_init__(self) -> None:
        if self.left_port_key == self.right_port_key:
            raise ReceiptError("resonance edge requires two distinct ports")


def resonance_graph_receipt_payload(
    graph_id: str, required_edges: Sequence[RequiredEdge]
) -> bytes:
    return _canonical_bytes(
        {
            "graph_id": graph_id,
            "required_edges": [
                {
                    "left_port_key": list(edge.left_port_key),
                    "right_port_key": list(edge.right_port_key),
                }
                for edge in required_edges
            ],
            "schema": "glew.mounted_resonance_graph.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class MountedResonanceGraph:
    """Profile-mounted R_UF edges; results never select favorable edges."""

    graph_id: str
    required_edges: tuple[RequiredEdge, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.graph_id, "graph_id")
        sha256_digest(self.authority_receipt_sha256, "authority_receipt_sha256")
        if not self.required_edges:
            raise ReceiptError("mounted resonance graph cannot be empty")
        if len(set(self.required_edges)) != len(self.required_edges):
            raise ReceiptError("mounted resonance edges must be unique")
        if not all(isinstance(edge, RequiredEdge) for edge in self.required_edges):
            raise ReceiptError("mounted resonance graph contains an invalid edge")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "resonance_graph_authority_receipt"
        )
        expected = resonance_graph_receipt_payload(self.graph_id, self.required_edges)
        if mounted != expected:
            raise ReceiptError("resonance graph does not match its mounted authority receipt")


def resonance_operator_receipt_payload(operator_id: str, precision_bits: int) -> bytes:
    return _canonical_bytes(
        {
            "backend": {
                "flint": FLINT_VERSION,
                "python_flint": PYTHON_FLINT_VERSION,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            },
            "formula": "gamma_squared_common_grid.v1",
            "operator_id": operator_id,
            "precision_bits": precision_bits,
            "schema": "glew.resonance_operator_authority.v1",
            "threads": 1,
        }
    )


@dataclass(frozen=True, slots=True)
class ResonanceOperatorAuthority:
    """Signed deterministic arithmetic profile for executable R_UF."""

    operator_id: str
    precision_bits: int
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.operator_id, "operator_id")
        if (
            isinstance(self.precision_bits, bool)
            or not isinstance(self.precision_bits, int)
            or self.precision_bits <= 0
        ):
            raise ReceiptError("precision_bits must be a positive integer")
        sha256_digest(self.authority_receipt_sha256, "authority_receipt_sha256")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "resonance_operator_authority_receipt"
        )
        expected = resonance_operator_receipt_payload(
            self.operator_id, self.precision_bits
        )
        if mounted != expected:
            raise ReceiptError("resonance operator does not match its mounted authority receipt")


@dataclass(frozen=True, slots=True)
class EdgeResonance:
    edge: RequiredEdge
    gamma_squared: CertifiedBall
    proved_zero_energy: bool


@dataclass(frozen=True, slots=True)
class ResonanceConfirmation:
    """R_UF meet over the mounted weave's explicit required edges."""

    value: CertifiedBall
    edge_facts: tuple[EdgeResonance, ...]
    required_edges: tuple[RequiredEdge, ...]
    graph_authority_receipt_sha256: str
    operator_authority_receipt_sha256: str
    working_precision_bits: int
    grid_id: str


def compute_resonance_confirmation(
    streams: Sequence[EvidenceStream],
    grid: CausalGrid,
    mounted_graph: MountedResonanceGraph,
    operator_authority: ResonanceOperatorAuthority,
    receipt_registry: ReceiptRegistry,
) -> ResonanceConfirmation:
    """Execute the approved coherence-squared operator with pinned Arb.

    Exact rational timestamps, weights, relevance, and phase enter Arb without
    float conversion.  The carrier phasor is evaluated by certified complex
    ball arithmetic.  Missing edges, zero required domain, or backend mismatch
    fail closed.  A proved zero-energy applicable edge is exactly zero.
    """

    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("a mounted immutable receipt registry is required")
    grid.verify(receipt_registry)
    if not isinstance(mounted_graph, MountedResonanceGraph):
        raise ReceiptError("R_UF requires a mounted resonance graph")
    if not isinstance(operator_authority, ResonanceOperatorAuthority):
        raise ReceiptError("R_UF requires a mounted operator authority")
    mounted_graph.verify(receipt_registry)
    operator_authority.verify(receipt_registry)
    precision_bits = operator_authority.precision_bits
    mapped = _stream_map(streams, receipt_registry)
    edges = mounted_graph.required_edges
    for edge in edges:
        if not isinstance(edge, RequiredEdge):
            raise ReceiptError("required edges must be RequiredEdge receipts")
        if edge.left_port_key not in mapped or edge.right_port_key not in mapped:
            raise ReceiptError(f"required resonance evidence is unavailable for {edge!r}")

    flint = load_pinned_flint()
    edge_values: list[tuple[RequiredEdge, object, bool]] = []
    with flint.ctx.workprec(precision_bits):
        two_pi_i = flint.acb(0, 2 * flint.arb.pi())
        for edge in edges:
            left = _aligned_samples(mapped[edge.left_port_key], grid)
            right = _aligned_samples(mapped[edge.right_port_key], grid)
            left_energy = sum(
                (weight * sample.relevance for weight, sample in zip(grid.positive_weights, left, strict=True)),
                Fraction(0),
            )
            right_energy = sum(
                (weight * sample.relevance for weight, sample in zip(grid.positive_weights, right, strict=True)),
                Fraction(0),
            )
            if left_energy == 0 or right_energy == 0:
                edge_values.append((edge, flint.arb(0), True))
                continue

            inner = flint.acb(0)
            for weight, left_sample, right_sample in zip(
                grid.positive_weights, left, right, strict=True
            ):
                left_z = arb_fraction(flint, left_sample.relevance).sqrt() * (
                    two_pi_i * arb_fraction(flint, left_sample.phase_turns)
                ).exp()
                right_z = arb_fraction(flint, right_sample.relevance).sqrt() * (
                    two_pi_i * arb_fraction(flint, right_sample.phase_turns)
                ).exp()
                inner += arb_fraction(flint, weight) * left_z * right_z.conjugate()

            denominator = arb_fraction(flint, left_energy * right_energy)
            gamma_squared = abs(inner) ** 2 / denominator
            edge_values.append((edge, gamma_squared, False))

        value = edge_values[0][1]
        for _, edge_value, _ in edge_values[1:]:
            value = flint.arb.min(value, edge_value)
        result_ball = canonical_ball(value, precision_bits)
        edge_facts = tuple(
            EdgeResonance(
                edge=edge,
                gamma_squared=canonical_ball(edge_value, precision_bits),
                proved_zero_energy=proved_zero,
            )
            for edge, edge_value, proved_zero in edge_values
        )

    return ResonanceConfirmation(
        value=result_ball,
        edge_facts=edge_facts,
        required_edges=edges,
        graph_authority_receipt_sha256=mounted_graph.authority_receipt_sha256,
        operator_authority_receipt_sha256=operator_authority.authority_receipt_sha256,
        working_precision_bits=precision_bits,
        grid_id=grid.grid_id,
    )
