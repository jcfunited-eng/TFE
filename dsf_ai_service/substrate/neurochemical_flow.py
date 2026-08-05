"""Sparse, conservative, event-driven neurochemical flow foundation.

This module is intentionally isolated from runtime, sensory transduction,
L0--L4, story chemistry, mood broadcast, and whole-organism custody.

The mounted program is a finite sparse graph.  Vertices are explicit
species-at-node compartments, including mounted external reservoirs and sinks.
Edges are typed physical pass-offs or first-order conversions.  Every numeric
physical fact is exact, unit-bearing, derivation-bearing, and authenticated by
the fixed manifest.  Causal transfers move quantity between mounted vertices;
they never create or delete quantity outside an explicit reservoir.

At a causal boundary the authority builds one sparse Metzler generator.  Exact
connected blocks are solved analytically with the pinned Arb matrix
exponential.  Disconnected zero-generator components are not numerically
advanced.  There is no microtick loop, polling, midpoint, float conversion,
threshold, clipping, normalization, coefficient default, semantic selector, or
global scalar output.

Temporal driver kinds authenticate which physical clock/source produced a
boundary receipt.  They do not implement oscillators, continuous modulation,
or kind-dependent chemistry; those mechanisms remain explicitly unavailable.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Sequence

from dsf_ai_service.glew_runtime.certified_backend import (
    FLINT_VERSION,
    PYTHON_FLINT_VERSION,
    PYTHON_FLINT_WHEEL_SHA256,
    CertifiedBall,
    arb_fraction,
    canonical_ball,
    load_pinned_flint,
)
from dsf_ai_service.substrate.neurochemical_upstream_receipt import (
    CausalSourceKind,
    MAX_UPSTREAM_SEQUENCE_BITS,
    PhysicalNeurochemicalReceipt,
    TemporalDriverKind,
    TemporalNeurochemicalReceipt,
    UpstreamAuthorityKind,
    UpstreamIssuerVerifierMount,
    UpstreamNeurochemicalReceipt,
    verify_upstream_receipt,
)
from dsf_ai_service.substrate.neurochemical_physical_quantity import (
    PhysicalQuantityVerifierMount,
    SignedPhysicalQuantity,
    verify_signed_physical_quantity,
)


MANIFEST_SCHEMA = "guala.neurochemical_flow.manifest.v3"
EVENT_SCHEMA = "guala.neurochemical_flow.verified_causal_event.v2"
STATE_SCHEMA = "guala.neurochemical_flow.state.v3"
TRANSITION_SCHEMA = "guala.neurochemical_flow.transition.v3"
COLD_SCHEMA = "guala.neurochemical_flow.cold_state.v3"

_MANIFEST_DOMAIN = b"guala-neurochemical-flow-manifest-v3\0"
_COLD_DOMAIN = b"guala-neurochemical-flow-cold-v3\0"
_HEX = frozenset("0123456789abcdef")

MAX_MANIFEST_BYTES = 64 * 1024 * 1024
MAX_STATE_BYTES = 256 * 1024 * 1024
MAX_COMPONENTS = 65_536
MAX_LANES = 262_144
MAX_REACTIONS = 262_144
MAX_TARGETS = 262_144
MAX_EVENTS_PER_BOUNDARY = 65_536
MAX_ACTIVE_BLOCK_COMPONENTS = 256
MAX_DERIVATION_RECEIPT_BYTES = 1_048_576
MAX_CAUSAL_RECEIPT_BYTES = 1_048_576
MAX_EVENT_BYTES = 8_388_608


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 identity")
    return value


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > 256
    ):
        raise ValueError(f"{label} is not a bounded canonical identifier")
    return value


def _key(value: bytes | str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4096:
        raise ValueError("neurochemical authority key is invalid")
    return raw


def _fraction(value: object, label: str) -> Fraction:
    if not isinstance(value, Fraction):
        raise TypeError(f"{label} must be an exact Fraction")
    return value


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _fraction_from_text(value: object, label: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{label} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{label} is not an exact fraction") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{label} is not canonical")
    return result


def _payload_receipt(payload: bytes, label: str) -> str:
    if not isinstance(payload, bytes) or not payload:
        raise ValueError(f"{label} requires nonempty exact bytes")
    return hashlib.sha256(payload).hexdigest()


def _bounded_payload(
    payload: bytes,
    label: str,
    maximum_bytes: int,
) -> bytes:
    if (
        not isinstance(payload, bytes)
        or not payload
        or len(payload) > maximum_bytes
    ):
        raise ValueError(f"{label} exceeds its authenticated byte capacity")
    return payload


def _ball_record(value: CertifiedBall) -> dict[str, object]:
    if not isinstance(value, CertifiedBall):
        raise TypeError("neurochemical enclosure is not certified")
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


def _ball_from_record(value: object) -> CertifiedBall:
    if not isinstance(value, dict) or set(value) != {
        "flint_version",
        "lower_exponent",
        "lower_mantissa",
        "python_flint_version",
        "upper_exponent",
        "upper_mantissa",
        "wheel_sha256",
        "working_precision_bits",
    }:
        raise ValueError("certified neurochemical enclosure changed shape")
    for name in (
        "lower_exponent",
        "lower_mantissa",
        "upper_exponent",
        "upper_mantissa",
        "working_precision_bits",
    ):
        if isinstance(value[name], bool) or not isinstance(value[name], int):
            raise ValueError("certified neurochemical enclosure lost integers")
    result = CertifiedBall(
        lower_mantissa=value["lower_mantissa"],
        lower_exponent=value["lower_exponent"],
        upper_mantissa=value["upper_mantissa"],
        upper_exponent=value["upper_exponent"],
        working_precision_bits=value["working_precision_bits"],
        python_flint_version=value["python_flint_version"],
        flint_version=value["flint_version"],
        wheel_sha256=value["wheel_sha256"],
    )
    _ball_bounds(result)
    return result


def _ball_bounds(value: CertifiedBall) -> tuple[Fraction, Fraction]:
    if (
        value.python_flint_version != PYTHON_FLINT_VERSION
        or value.flint_version != FLINT_VERSION
        or value.wheel_sha256 != PYTHON_FLINT_WHEEL_SHA256
    ):
        raise ValueError("neurochemical enclosure has another backend")
    return (
        Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent,
        Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent,
    )


def _dyadic_pair(value: Fraction) -> tuple[int, int]:
    denominator = value.denominator
    if denominator & (denominator - 1):
        raise ValueError("certified neurochemical endpoint is not dyadic")
    return value.numerator, -(denominator.bit_length() - 1)


def _arb_from_ball(flint, value: CertifiedBall):
    lower, upper = _ball_bounds(value)
    center = (lower + upper) / 2
    radius = (upper - lower) / 2
    return flint.arb(_dyadic_pair(center), _dyadic_pair(radius))


class QuantityDomain(str, Enum):
    STRICTLY_POSITIVE = "strictly_positive"
    NONNEGATIVE = "nonnegative"


class NodeKind(str, Enum):
    PHYSICAL = "physical"
    EXTERNAL_SOURCE_RESERVOIR = "external_source_reservoir"
    EXTERNAL_SINK_RESERVOIR = "external_sink_reservoir"


class DirectedLaneKind(str, Enum):
    SYNAPTIC = "synaptic"
    EXTRACELLULAR_DIFFUSION = "extracellular_diffusion"
    RETROGRADE = "retrograde"
    CIRCULATORY = "circulatory"
    CSF_CLEARANCE = "csf_clearance"


class LocalTargetKind(str, Enum):
    MEMBRANE_CONDUCTANCE = "membrane_conductance"
    ION_DRIVING_STATE = "ion_driving_state"
    RELEASE_PROPENSITY = "release_propensity"
    REFRACTORY_RECOVERY = "refractory_recovery"
    METABOLIC_AVAILABILITY = "metabolic_availability"
    PLASTICITY_ELIGIBILITY = "plasticity_eligibility"


class NonlinearMechanismKind(str, Enum):
    SATURATING_UPTAKE = "saturating_uptake"
    COOPERATIVE_BINDING = "cooperative_binding"
    NONLINEAR_DEGRADATION = "nonlinear_degradation"
    RECEPTOR_BINDING_ACTIVATION = "receptor_binding_activation"


class MechanismAvailability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class EvolutionStatus(str, Enum):
    EVOLVED = "evolved"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class NeurochemicalSpeciesMount:
    species_id: str
    quantity_unit: str
    conserved_mass_per_quantity: SignedPhysicalQuantity

    def verify(self, quantity_verifier) -> None:
        _identifier(self.species_id, "neurochemical species id")
        _identifier(self.quantity_unit, "neurochemical quantity unit")
        quantity_verifier(
            self.conserved_mass_per_quantity,
            expected_role=(
                f"species/{self.species_id}/conserved_mass_per_quantity"
            ),
            expected_unit=f"mass-per-{self.quantity_unit}",
            domain=QuantityDomain.STRICTLY_POSITIVE,
        )

    def record(self) -> dict[str, object]:
        return {
            "conserved_mass_per_quantity": (
                self.conserved_mass_per_quantity.record()
            ),
            "quantity_unit": self.quantity_unit,
            "species_id": self.species_id,
        }


@dataclass(frozen=True, slots=True)
class NeurochemicalNodeMount:
    node_id: str
    kind: NodeKind
    volume: SignedPhysicalQuantity

    def verify(self, quantity_verifier) -> None:
        _identifier(self.node_id, "neurochemical node id")
        if not isinstance(self.kind, NodeKind):
            raise TypeError("neurochemical node kind is not typed")
        quantity_verifier(
            self.volume,
            expected_role=f"node/{self.node_id}/volume",
            expected_unit="volume",
            domain=QuantityDomain.STRICTLY_POSITIVE,
        )

    def record(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "node_id": self.node_id,
            "volume": self.volume.record(),
        }


@dataclass(frozen=True, slots=True)
class NeurochemicalCompartmentMount:
    component_id: str
    species_id: str
    node_id: str
    initial_quantity: SignedPhysicalQuantity

    def verify(self, quantity_verifier) -> None:
        _identifier(self.component_id, "neurochemical component id")
        _identifier(self.species_id, "component species id")
        _identifier(self.node_id, "component node id")
        quantity_verifier(
            self.initial_quantity,
            expected_role=f"component/{self.component_id}/initial_quantity",
            expected_unit=None,
            domain=QuantityDomain.NONNEGATIVE,
        )

    def record(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "initial_quantity": self.initial_quantity.record(),
            "node_id": self.node_id,
            "species_id": self.species_id,
        }


@dataclass(frozen=True, slots=True)
class NeurochemicalImpulseRoute:
    lane_id: str
    kind: DirectedLaneKind
    species_id: str
    source_component_id: str
    target_component_id: str

    def verify(self) -> None:
        _identifier(self.lane_id, "neurochemical impulse route id")
        if self.kind not in {
            DirectedLaneKind.SYNAPTIC,
            DirectedLaneKind.RETROGRADE,
        }:
            raise ValueError(
                "only synaptic or retrograde routes are impulse-only"
            )
        _identifier(self.species_id, "impulse route species id")
        _identifier(self.source_component_id, "impulse route source")
        _identifier(self.target_component_id, "impulse route target")
        if self.source_component_id == self.target_component_id:
            raise ValueError("neurochemical impulse route cannot self-transfer")

    def record(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "lane_id": self.lane_id,
            "source_component_id": self.source_component_id,
            "species_id": self.species_id,
            "target_component_id": self.target_component_id,
        }


@dataclass(frozen=True, slots=True)
class NeurochemicalDriftLane:
    lane_id: str
    kind: DirectedLaneKind
    species_id: str
    source_component_id: str
    target_component_id: str
    velocity: SignedPhysicalQuantity
    interface_area: SignedPhysicalQuantity

    def verify(self, quantity_verifier) -> None:
        _identifier(self.lane_id, "neurochemical drift lane id")
        if self.kind not in {
            DirectedLaneKind.CIRCULATORY,
            DirectedLaneKind.CSF_CLEARANCE,
        }:
            raise ValueError("continuous drift requires circulatory or CSF kind")
        _identifier(self.species_id, "drift lane species id")
        _identifier(self.source_component_id, "drift lane source")
        _identifier(self.target_component_id, "drift lane target")
        if self.source_component_id == self.target_component_id:
            raise ValueError("neurochemical drift lane cannot self-transfer")
        quantity_verifier(
            self.velocity,
            expected_role=f"drift/{self.lane_id}/velocity",
            expected_unit="length-per-time",
            domain=QuantityDomain.STRICTLY_POSITIVE,
        )
        quantity_verifier(
            self.interface_area,
            expected_role=f"drift/{self.lane_id}/interface_area",
            expected_unit="area",
            domain=QuantityDomain.STRICTLY_POSITIVE,
        )

    def record(self) -> dict[str, object]:
        return {
            "interface_area": self.interface_area.record(),
            "kind": self.kind.value,
            "lane_id": self.lane_id,
            "source_component_id": self.source_component_id,
            "species_id": self.species_id,
            "target_component_id": self.target_component_id,
            "velocity": self.velocity.record(),
        }


@dataclass(frozen=True, slots=True)
class ExtracellularDiffusionInterface:
    interface_id: str
    species_id: str
    endpoint_a_component_id: str
    endpoint_b_component_id: str
    diffusion_coefficient: SignedPhysicalQuantity
    interface_area: SignedPhysicalQuantity
    path_length: SignedPhysicalQuantity

    def verify(self, quantity_verifier) -> None:
        _identifier(self.interface_id, "diffusion interface id")
        _identifier(self.species_id, "diffusion interface species id")
        _identifier(self.endpoint_a_component_id, "diffusion endpoint a")
        _identifier(self.endpoint_b_component_id, "diffusion endpoint b")
        if self.endpoint_a_component_id == self.endpoint_b_component_id:
            raise ValueError("diffusion interface requires two endpoints")
        quantity_verifier(
            self.diffusion_coefficient,
            expected_role=(
                f"diffusion/{self.interface_id}/diffusion_coefficient"
            ),
            expected_unit="area-per-time",
            domain=QuantityDomain.STRICTLY_POSITIVE,
        )
        quantity_verifier(
            self.interface_area,
            expected_role=f"diffusion/{self.interface_id}/interface_area",
            expected_unit="area",
            domain=QuantityDomain.STRICTLY_POSITIVE,
        )
        quantity_verifier(
            self.path_length,
            expected_role=f"diffusion/{self.interface_id}/path_length",
            expected_unit="length",
            domain=QuantityDomain.STRICTLY_POSITIVE,
        )

    def record(self) -> dict[str, object]:
        return {
            "diffusion_coefficient": self.diffusion_coefficient.record(),
            "endpoint_a_component_id": self.endpoint_a_component_id,
            "endpoint_b_component_id": self.endpoint_b_component_id,
            "interface_area": self.interface_area.record(),
            "interface_id": self.interface_id,
            "path_length": self.path_length.record(),
            "species_id": self.species_id,
        }


@dataclass(frozen=True, slots=True)
class FirstOrderNeurochemicalConversion:
    reaction_id: str
    node_id: str
    reactant_component_id: str
    product_component_id: str
    rate: SignedPhysicalQuantity
    product_quantity_per_reactant: SignedPhysicalQuantity

    def verify(self, quantity_verifier) -> None:
        _identifier(self.reaction_id, "neurochemical reaction id")
        _identifier(self.node_id, "reaction node id")
        _identifier(self.reactant_component_id, "reaction reactant")
        _identifier(self.product_component_id, "reaction product")
        if self.reactant_component_id == self.product_component_id:
            raise ValueError("conversion requires distinct components")
        quantity_verifier(
            self.rate,
            expected_role=f"conversion/{self.reaction_id}/rate",
            expected_unit="per-time",
            domain=QuantityDomain.STRICTLY_POSITIVE,
        )
        quantity_verifier(
            self.product_quantity_per_reactant,
            expected_role=f"conversion/{self.reaction_id}/product_ratio",
            expected_unit=None,
            domain=QuantityDomain.STRICTLY_POSITIVE,
        )

    def record(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "product_component_id": self.product_component_id,
            "product_quantity_per_reactant": (
                self.product_quantity_per_reactant.record()
            ),
            "rate": self.rate.record(),
            "reactant_component_id": self.reactant_component_id,
            "reaction_id": self.reaction_id,
        }


@dataclass(frozen=True, slots=True)
class PhysicalReceiptRoutePermission:
    route_id: str
    issuer_id: str
    source_kind: CausalSourceKind
    source_component_id: str
    lane_id: str
    destination_component_id: str
    amount_unit: str

    def verify(self) -> None:
        _identifier(self.route_id, "physical upstream route id")
        _identifier(self.issuer_id, "physical upstream issuer id")
        if not isinstance(self.source_kind, CausalSourceKind):
            raise TypeError("physical upstream source kind is not typed")
        _identifier(self.source_component_id, "physical upstream source")
        _identifier(self.lane_id, "physical upstream lane")
        _identifier(self.destination_component_id, "physical upstream destination")
        _identifier(self.amount_unit, "physical upstream amount unit")

    def record(self) -> dict[str, object]:
        return {
            "amount_unit": self.amount_unit,
            "destination_component_id": self.destination_component_id,
            "issuer_id": self.issuer_id,
            "lane_id": self.lane_id,
            "route_id": self.route_id,
            "source_component_id": self.source_component_id,
            "source_kind": self.source_kind.value,
        }


@dataclass(frozen=True, slots=True)
class TemporalReceiptRoutePermission:
    route_id: str
    issuer_id: str
    driver_kind: TemporalDriverKind
    lane_id: str
    lane_enabled: bool
    physical_parameter_path: str

    def verify(self) -> None:
        _identifier(self.route_id, "temporal upstream route id")
        _identifier(self.issuer_id, "temporal upstream issuer id")
        if not isinstance(self.driver_kind, TemporalDriverKind):
            raise TypeError("temporal upstream driver kind is not typed")
        _identifier(self.lane_id, "temporal upstream lane")
        if not isinstance(self.lane_enabled, bool):
            raise TypeError("temporal upstream lane state is not boolean")
        _identifier(
            self.physical_parameter_path,
            "temporal upstream physical parameter path",
        )

    def record(self) -> dict[str, object]:
        return {
            "driver_kind": self.driver_kind.value,
            "issuer_id": self.issuer_id,
            "lane_enabled": self.lane_enabled,
            "lane_id": self.lane_id,
            "physical_parameter_path": self.physical_parameter_path,
            "route_id": self.route_id,
        }


@dataclass(frozen=True, slots=True)
class LocalNeurochemicalTarget:
    target_id: str
    component_id: str
    kind: LocalTargetKind
    receptor_activation_availability: MechanismAvailability
    derivation_receipt_payload: bytes
    derivation_receipt_sha256: str

    def verify(self) -> None:
        _identifier(self.target_id, "local neurochemical target id")
        _identifier(self.component_id, "target component id")
        if not isinstance(self.kind, LocalTargetKind):
            raise TypeError("local neurochemical target kind is not typed")
        if not isinstance(
            self.receptor_activation_availability,
            MechanismAvailability,
        ):
            raise TypeError("local receptor availability is not typed")
        _bounded_payload(
            self.derivation_receipt_payload,
            "local target derivation",
            MAX_DERIVATION_RECEIPT_BYTES,
        )
        if _payload_receipt(
            self.derivation_receipt_payload,
            "local target derivation",
        ) != _sha(
            self.derivation_receipt_sha256,
            "local target derivation",
        ):
            raise ValueError("local target derivation was tampered")

    def record(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "derivation_receipt_payload_hex": (
                self.derivation_receipt_payload.hex()
            ),
            "derivation_receipt_sha256": self.derivation_receipt_sha256,
            "kind": self.kind.value,
            "receptor_activation_availability": (
                self.receptor_activation_availability.value
            ),
            "target_id": self.target_id,
        }


@dataclass(frozen=True, slots=True)
class UnavailableNonlinearMechanism:
    mechanism_id: str
    kind: NonlinearMechanismKind
    availability: MechanismAvailability
    reason: str
    derivation_receipt_payload: bytes
    derivation_receipt_sha256: str

    def verify(self) -> None:
        _identifier(self.mechanism_id, "nonlinear mechanism id")
        if not isinstance(self.kind, NonlinearMechanismKind):
            raise TypeError("nonlinear mechanism kind is not typed")
        if self.availability is not MechanismAvailability.UNAVAILABLE:
            raise ValueError("nonlinear mechanism cannot be approximated")
        _identifier(self.reason, "nonlinear unavailable reason")
        _bounded_payload(
            self.derivation_receipt_payload,
            "nonlinear unavailability derivation",
            MAX_DERIVATION_RECEIPT_BYTES,
        )
        if _payload_receipt(
            self.derivation_receipt_payload,
            "nonlinear unavailability derivation",
        ) != _sha(
            self.derivation_receipt_sha256,
            "nonlinear unavailability derivation",
        ):
            raise ValueError("nonlinear unavailability evidence was tampered")

    def record(self) -> dict[str, object]:
        return {
            "availability": self.availability.value,
            "derivation_receipt_payload_hex": (
                self.derivation_receipt_payload.hex()
            ),
            "derivation_receipt_sha256": self.derivation_receipt_sha256,
            "kind": self.kind.value,
            "mechanism_id": self.mechanism_id,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class NeurochemicalBackendMount:
    authority_id: str
    working_precision_bits: int
    derivation_receipt_payload: bytes
    derivation_receipt_sha256: str

    def verify(self, *, live: bool) -> None:
        _identifier(self.authority_id, "neurochemical backend authority id")
        if (
            isinstance(self.working_precision_bits, bool)
            or not isinstance(self.working_precision_bits, int)
            or self.working_precision_bits <= 0
        ):
            raise ValueError("backend precision is not a positive integer")
        _bounded_payload(
            self.derivation_receipt_payload,
            "backend derivation",
            MAX_DERIVATION_RECEIPT_BYTES,
        )
        if _payload_receipt(
            self.derivation_receipt_payload,
            "backend derivation",
        ) != _sha(
            self.derivation_receipt_sha256,
            "backend derivation",
        ):
            raise ValueError("backend derivation was tampered")
        if live:
            load_pinned_flint()

    def record(self) -> dict[str, object]:
        return {
            "authority_id": self.authority_id,
            "derivation_receipt_payload_hex": (
                self.derivation_receipt_payload.hex()
            ),
            "derivation_receipt_sha256": self.derivation_receipt_sha256,
            "flint_version": FLINT_VERSION,
            "python_flint_version": PYTHON_FLINT_VERSION,
            "threads": 1,
            "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            "working_precision_bits": self.working_precision_bits,
        }


@dataclass(frozen=True, slots=True)
class NeurochemicalCapacity:
    max_components: int
    max_lanes: int
    max_reactions: int
    max_targets: int
    max_events_per_boundary: int
    max_active_block_components: int
    max_derivation_receipt_bytes: int
    max_causal_receipt_bytes: int
    max_event_bytes: int
    max_state_bytes: int

    def verify(self) -> None:
        limits = (
            ("components", self.max_components, MAX_COMPONENTS),
            ("lanes", self.max_lanes, MAX_LANES),
            ("reactions", self.max_reactions, MAX_REACTIONS),
            ("targets", self.max_targets, MAX_TARGETS),
            (
                "events_per_boundary",
                self.max_events_per_boundary,
                MAX_EVENTS_PER_BOUNDARY,
            ),
            (
                "active_block_components",
                self.max_active_block_components,
                MAX_ACTIVE_BLOCK_COMPONENTS,
            ),
            (
                "derivation_receipt_bytes",
                self.max_derivation_receipt_bytes,
                MAX_DERIVATION_RECEIPT_BYTES,
            ),
            (
                "causal_receipt_bytes",
                self.max_causal_receipt_bytes,
                MAX_CAUSAL_RECEIPT_BYTES,
            ),
            ("event_bytes", self.max_event_bytes, MAX_EVENT_BYTES),
            ("state_bytes", self.max_state_bytes, MAX_STATE_BYTES),
        )
        for label, value, maximum in limits:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 1 <= value <= maximum
            ):
                raise ValueError(f"neurochemical {label} capacity is invalid")

    def record(self) -> dict[str, object]:
        return {
            "max_components": self.max_components,
            "max_active_block_components": self.max_active_block_components,
            "max_causal_receipt_bytes": self.max_causal_receipt_bytes,
            "max_derivation_receipt_bytes": (
                self.max_derivation_receipt_bytes
            ),
            "max_event_bytes": self.max_event_bytes,
            "max_events_per_boundary": self.max_events_per_boundary,
            "max_lanes": self.max_lanes,
            "max_reactions": self.max_reactions,
            "max_state_bytes": self.max_state_bytes,
            "max_targets": self.max_targets,
        }


def _verify_total_transport_capacity(
    *,
    impulse_routes: Sequence[object],
    drift_lanes: Sequence[object],
    diffusion_interfaces: Sequence[object],
    maximum_lanes: int,
) -> None:
    total_transport_identities = (
        len(impulse_routes)
        + len(drift_lanes)
        + len(diffusion_interfaces)
    )
    if total_transport_identities > maximum_lanes:
        raise ValueError(
            "total mounted transport identities exceed authenticated "
            "lane capacity"
        )


def _iter_signed_manifest_quantities(
    *,
    structural_time_unit: SignedPhysicalQuantity,
    species: Sequence[NeurochemicalSpeciesMount],
    nodes: Sequence[NeurochemicalNodeMount],
    components: Sequence[NeurochemicalCompartmentMount],
    drift_lanes: Sequence[NeurochemicalDriftLane],
    diffusion_interfaces: Sequence[ExtracellularDiffusionInterface],
    conversions: Sequence[FirstOrderNeurochemicalConversion],
):
    yield structural_time_unit
    for value in species:
        yield value.conserved_mass_per_quantity
    for value in nodes:
        yield value.volume
    for value in components:
        yield value.initial_quantity
    for value in drift_lanes:
        yield value.velocity
        yield value.interface_area
    for value in diffusion_interfaces:
        yield value.diffusion_coefficient
        yield value.interface_area
        yield value.path_length
    for value in conversions:
        yield value.rate
        yield value.product_quantity_per_reactant


@dataclass(frozen=True, slots=True)
class NeurochemicalFlowManifest:
    manifest_id: str
    structural_time_unit: SignedPhysicalQuantity
    backend: NeurochemicalBackendMount
    physical_quantity_issuers: tuple[PhysicalQuantityVerifierMount, ...]
    species: tuple[NeurochemicalSpeciesMount, ...]
    nodes: tuple[NeurochemicalNodeMount, ...]
    components: tuple[NeurochemicalCompartmentMount, ...]
    impulse_routes: tuple[NeurochemicalImpulseRoute, ...]
    drift_lanes: tuple[NeurochemicalDriftLane, ...]
    diffusion_interfaces: tuple[ExtracellularDiffusionInterface, ...]
    conversions: tuple[FirstOrderNeurochemicalConversion, ...]
    upstream_issuers: tuple[UpstreamIssuerVerifierMount, ...]
    physical_route_permissions: tuple[PhysicalReceiptRoutePermission, ...]
    temporal_route_permissions: tuple[TemporalReceiptRoutePermission, ...]
    local_targets: tuple[LocalNeurochemicalTarget, ...]
    unavailable_nonlinear_mechanisms: tuple[
        UnavailableNonlinearMechanism, ...
    ]
    initial_enabled_transport_ids: tuple[str, ...]
    capacity: NeurochemicalCapacity
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "backend": self.backend.record(),
            "capacity": self.capacity.record(),
            "components": [value.record() for value in self.components],
            "conversions": [value.record() for value in self.conversions],
            "diffusion_interfaces": [
                value.record() for value in self.diffusion_interfaces
            ],
            "drift_lanes": [value.record() for value in self.drift_lanes],
            "impulse_routes": [
                value.record() for value in self.impulse_routes
            ],
            "initial_enabled_transport_ids": list(
                self.initial_enabled_transport_ids
            ),
            "physical_route_permissions": [
                value.record() for value in self.physical_route_permissions
            ],
            "local_targets": [
                value.record() for value in self.local_targets
            ],
            "manifest_id": self.manifest_id,
            "nodes": [value.record() for value in self.nodes],
            "physical_quantity_issuers": [
                value.record() for value in self.physical_quantity_issuers
            ],
            "schema": MANIFEST_SCHEMA,
            "species": [value.record() for value in self.species],
            "structural_time_unit": self.structural_time_unit.record(),
            "temporal_route_permissions": [
                value.record() for value in self.temporal_route_permissions
            ],
            "unavailable_nonlinear_mechanisms": [
                value.record()
                for value in self.unavailable_nonlinear_mechanisms
            ],
            "upstream_issuers": [
                value.record() for value in self.upstream_issuers
            ],
        }

    def verify(self, authority_key: bytes | str) -> None:
        _identifier(self.manifest_id, "neurochemical manifest id")
        self.capacity.verify()
        for values in (
            self.impulse_routes,
            self.drift_lanes,
            self.diffusion_interfaces,
        ):
            if not isinstance(values, tuple):
                raise TypeError(
                    "neurochemical transport collection is not typed"
                )
        _verify_total_transport_capacity(
            impulse_routes=self.impulse_routes,
            drift_lanes=self.drift_lanes,
            diffusion_interfaces=self.diffusion_interfaces,
            maximum_lanes=self.capacity.max_lanes,
        )
        self.backend.verify(live=False)
        if (
            not isinstance(self.physical_quantity_issuers, tuple)
            or not self.physical_quantity_issuers
            or any(
                not isinstance(value, PhysicalQuantityVerifierMount)
                for value in self.physical_quantity_issuers
            )
        ):
            raise ValueError("manifest lacks physical quantity issuers")
        quantity_issuer_by_id = {
            value.issuer_id: value for value in self.physical_quantity_issuers
        }
        for value in self.physical_quantity_issuers:
            value.verify()

        def verify_quantity(
            receipt: SignedPhysicalQuantity,
            *,
            expected_role: str,
            expected_unit: str | None,
            domain: QuantityDomain,
        ) -> None:
            issuer = quantity_issuer_by_id.get(receipt.issuer_id)
            if issuer is None:
                raise ValueError("physical quantity issuer is not mounted")
            verify_signed_physical_quantity(receipt, issuer)
            if (
                receipt.quantity_role != expected_role
                or (
                    expected_unit is not None
                    and receipt.unit != expected_unit
                )
                or (
                    domain is QuantityDomain.STRICTLY_POSITIVE
                    and receipt.value <= 0
                )
                or (
                    domain is QuantityDomain.NONNEGATIVE
                    and receipt.value < 0
                )
            ):
                raise ValueError(
                    "signed physical quantity left its exact mounted role"
                )

        verify_quantity(
            self.structural_time_unit,
            expected_role="manifest/structural_time_unit",
            expected_unit="time",
            domain=QuantityDomain.STRICTLY_POSITIVE,
        )
        if self.structural_time_unit.value != 1:
            raise ValueError(
                "structural time unit must be the exact canonical unit"
            )
        collections = (
            ("species", self.species, 2),
            ("nodes", self.nodes, 2),
            ("components", self.components, 2),
            ("impulse routes", self.impulse_routes, 1),
            ("upstream issuers", self.upstream_issuers, 1),
        )
        for label, values, minimum in collections:
            if not isinstance(values, tuple) or len(values) < minimum:
                raise ValueError(
                    f"neurochemical manifest lacks mounted {label}"
                )
        typed_collections = (
            (self.species, NeurochemicalSpeciesMount),
            (self.nodes, NeurochemicalNodeMount),
            (self.components, NeurochemicalCompartmentMount),
            (self.impulse_routes, NeurochemicalImpulseRoute),
            (self.upstream_issuers, UpstreamIssuerVerifierMount),
        )
        for values, expected_type in typed_collections:
            if any(not isinstance(value, expected_type) for value in values):
                raise TypeError(
                    "neurochemical manifest member is not correctly typed"
                )
        for values in (
            self.conversions,
            self.drift_lanes,
            self.diffusion_interfaces,
            self.physical_route_permissions,
            self.temporal_route_permissions,
            self.local_targets,
            self.unavailable_nonlinear_mechanisms,
        ):
            if not isinstance(values, tuple):
                raise TypeError("neurochemical manifest collection is not typed")
        optional_typed_collections = (
            (self.conversions, FirstOrderNeurochemicalConversion),
            (self.drift_lanes, NeurochemicalDriftLane),
            (
                self.diffusion_interfaces,
                ExtracellularDiffusionInterface,
            ),
            (
                self.physical_route_permissions,
                PhysicalReceiptRoutePermission,
            ),
            (
                self.temporal_route_permissions,
                TemporalReceiptRoutePermission,
            ),
            (self.local_targets, LocalNeurochemicalTarget),
            (
                self.unavailable_nonlinear_mechanisms,
                UnavailableNonlinearMechanism,
            ),
        )
        for values, expected_type in optional_typed_collections:
            if any(not isinstance(value, expected_type) for value in values):
                raise TypeError(
                    "neurochemical manifest member is not correctly typed"
                )
        for value in self.species:
            value.verify(verify_quantity)
        for value in self.nodes:
            value.verify(verify_quantity)
        for value in self.components:
            value.verify(verify_quantity)
        for value in self.impulse_routes:
            value.verify()
        for value in self.drift_lanes:
            value.verify(verify_quantity)
        for value in self.diffusion_interfaces:
            value.verify(verify_quantity)
        for value in self.conversions:
            value.verify(verify_quantity)
        for value in self.upstream_issuers:
            value.verify()
        for value in self.physical_route_permissions:
            value.verify()
        for value in self.temporal_route_permissions:
            value.verify()
        for value in self.local_targets:
            value.verify()
        for value in self.unavailable_nonlinear_mechanisms:
            value.verify()
        derivation_payloads = (
            tuple(
                value.derivation_receipt_payload for value in self.local_targets
            ),
            tuple(
                value.derivation_receipt_payload
                for value in self.unavailable_nonlinear_mechanisms
            ),
            (self.backend.derivation_receipt_payload,),
        )
        if any(
            len(payload) > self.capacity.max_derivation_receipt_bytes
            for group in derivation_payloads
            for payload in group
        ):
            raise ValueError(
                "manifest derivation exceeds authenticated byte capacity"
            )
        signed_quantities = _iter_signed_manifest_quantities(
            structural_time_unit=self.structural_time_unit,
            species=self.species,
            nodes=self.nodes,
            components=self.components,
            drift_lanes=self.drift_lanes,
            diffusion_interfaces=self.diffusion_interfaces,
            conversions=self.conversions,
        )
        conservative_manifest_bytes = (
            sum(len(_canonical(value.record())) for value in signed_quantities)
            + sum(
                2 * len(payload)
                for group in derivation_payloads
                for payload in group
            )
            + (
                len(self.species)
                + len(self.nodes)
                + len(self.components)
                + len(self.impulse_routes)
                + len(self.drift_lanes)
                + len(self.diffusion_interfaces)
                + len(self.conversions)
                + len(self.physical_quantity_issuers)
                + len(self.upstream_issuers)
                + len(self.local_targets)
                + len(self.unavailable_nonlinear_mechanisms)
                + len(self.physical_route_permissions)
                + len(self.temporal_route_permissions)
            )
            * 4096
        )
        if conservative_manifest_bytes > MAX_MANIFEST_BYTES:
            raise ValueError(
                "neurochemical manifest exceeds pre-allocation byte capacity"
            )
        identities = (
            ("species", tuple(value.species_id for value in self.species)),
            ("nodes", tuple(value.node_id for value in self.nodes)),
            (
                "components",
                tuple(value.component_id for value in self.components),
            ),
            (
                "impulse routes",
                tuple(value.lane_id for value in self.impulse_routes),
            ),
            (
                "drift lanes",
                tuple(value.lane_id for value in self.drift_lanes),
            ),
            (
                "diffusion interfaces",
                tuple(
                    value.interface_id for value in self.diffusion_interfaces
                ),
            ),
            (
                "conversions",
                tuple(value.reaction_id for value in self.conversions),
            ),
            (
                "targets",
                tuple(value.target_id for value in self.local_targets),
            ),
            (
                "upstream issuers",
                tuple(value.issuer_id for value in self.upstream_issuers),
            ),
            (
                "physical quantity issuers",
                tuple(
                    value.issuer_id
                    for value in self.physical_quantity_issuers
                ),
            ),
            (
                "upstream routes",
                tuple(
                    value.route_id
                    for value in (
                        *self.physical_route_permissions,
                        *self.temporal_route_permissions,
                    )
                ),
            ),
            (
                "nonlinear mechanisms",
                tuple(
                    value.mechanism_id
                    for value in self.unavailable_nonlinear_mechanisms
                ),
            ),
        )
        for label, values in identities:
            if values != tuple(sorted(set(values))):
                raise ValueError(
                    f"neurochemical {label} are not unique and canonical"
                )
        issuer_public_keys = tuple(
            value.ed25519_public_key_hex for value in self.upstream_issuers
        )
        quantity_public_keys = tuple(
            value.ed25519_public_key_hex
            for value in self.physical_quantity_issuers
        )
        if len(issuer_public_keys) != len(set(issuer_public_keys)):
            raise ValueError("upstream issuer public keys are not unique")
        if len(quantity_public_keys) != len(set(quantity_public_keys)):
            raise ValueError(
                "physical quantity issuer public keys are not unique"
            )
        if set(quantity_public_keys).intersection(issuer_public_keys):
            raise ValueError(
                "physical quantity and causal issuer keys must be independent"
            )
        physical_permission_keys = tuple(
            (
                value.issuer_id,
                value.source_kind,
                value.source_component_id,
                value.lane_id,
                value.destination_component_id,
                value.amount_unit,
            )
            for value in self.physical_route_permissions
        )
        temporal_permission_keys = tuple(
            (
                value.issuer_id,
                value.driver_kind,
                value.lane_id,
                value.lane_enabled,
                value.physical_parameter_path,
            )
            for value in self.temporal_route_permissions
        )
        if (
            len(physical_permission_keys)
            != len(set(physical_permission_keys))
            or len(temporal_permission_keys)
            != len(set(temporal_permission_keys))
        ):
            raise ValueError("upstream route permission is semantically duplicated")
        species_by_id = {value.species_id: value for value in self.species}
        nodes_by_id = {value.node_id: value for value in self.nodes}
        components_by_id = {
            value.component_id: value for value in self.components
        }
        if (
            not any(
                value.kind is NodeKind.EXTERNAL_SOURCE_RESERVOIR
                for value in self.nodes
            )
            or not any(
                value.kind is NodeKind.EXTERNAL_SINK_RESERVOIR
                for value in self.nodes
            )
            or not any(
                value.kind is NodeKind.PHYSICAL for value in self.nodes
            )
        ):
            raise ValueError(
                "neurochemical topology needs physical, source, and sink nodes"
            )
        seen_pairs: set[tuple[str, str]] = set()
        for component in self.components:
            species = species_by_id.get(component.species_id)
            if species is None or component.node_id not in nodes_by_id:
                raise ValueError("component lies outside mounted topology")
            if (
                component.initial_quantity.unit != species.quantity_unit
                or (component.species_id, component.node_id) in seen_pairs
            ):
                raise ValueError(
                    "component quantity unit or sparse position changed"
                )
            seen_pairs.add((component.species_id, component.node_id))
        impulse_by_id = {
            value.lane_id: value for value in self.impulse_routes
        }
        drift_by_id = {value.lane_id: value for value in self.drift_lanes}
        interface_by_id = {
            value.interface_id: value
            for value in self.diffusion_interfaces
        }
        continuous_transport_ids = set(drift_by_id) | set(interface_by_id)
        if set(impulse_by_id).intersection(continuous_transport_ids):
            raise ValueError(
                "impulse and continuous transport identities overlap"
            )
        for lane in (*self.impulse_routes, *self.drift_lanes):
            source = components_by_id.get(lane.source_component_id)
            target = components_by_id.get(lane.target_component_id)
            if (
                source is None
                or target is None
                or source.species_id != lane.species_id
                or target.species_id != lane.species_id
            ):
                raise ValueError(
                    "neurochemical route left its typed species topology"
                )
            target_node = nodes_by_id[target.node_id]
            if (
                lane.kind is DirectedLaneKind.CSF_CLEARANCE
                and target_node.kind is not NodeKind.EXTERNAL_SINK_RESERVOIR
            ):
                raise ValueError("CSF clearance must end in a mounted sink")
        seen_diffusion_pairs: set[tuple[str, str, str]] = set()
        for interface in self.diffusion_interfaces:
            endpoint_a = components_by_id.get(
                interface.endpoint_a_component_id
            )
            endpoint_b = components_by_id.get(
                interface.endpoint_b_component_id
            )
            if (
                endpoint_a is None
                or endpoint_b is None
                or endpoint_a.species_id != interface.species_id
                or endpoint_b.species_id != interface.species_id
                or nodes_by_id[endpoint_a.node_id].kind is not NodeKind.PHYSICAL
                or nodes_by_id[endpoint_b.node_id].kind is not NodeKind.PHYSICAL
            ):
                raise ValueError(
                    "reciprocal diffusion interface left physical topology"
                )
            pair = (
                interface.species_id,
                *sorted((
                    interface.endpoint_a_component_id,
                    interface.endpoint_b_component_id,
                )),
            )
            if pair in seen_diffusion_pairs:
                raise ValueError(
                    "diffusion endpoint pair has more than one interface"
                )
            seen_diffusion_pairs.add(pair)
        issuer_by_id = {
            value.issuer_id: value for value in self.upstream_issuers
        }
        for route in self.physical_route_permissions:
            issuer = issuer_by_id.get(route.issuer_id)
            lane = impulse_by_id.get(route.lane_id)
            if (
                issuer is None
                or issuer.authority_kind.value != route.source_kind.value
                or lane is None
                or lane.source_component_id != route.source_component_id
                or lane.target_component_id != route.destination_component_id
                or species_by_id[lane.species_id].quantity_unit
                != route.amount_unit
            ):
                raise ValueError(
                    "physical upstream route left mounted issuer topology"
                )
        for route in self.temporal_route_permissions:
            issuer = issuer_by_id.get(route.issuer_id)
            if (
                issuer is None
                or issuer.authority_kind is not UpstreamAuthorityKind.CLOCK
                or route.lane_id not in continuous_transport_ids
            ):
                raise ValueError(
                    "temporal upstream route left mounted clock topology"
                )
        if (
            self.initial_enabled_transport_ids
            != tuple(sorted(set(self.initial_enabled_transport_ids)))
            or not set(self.initial_enabled_transport_ids).issubset(
                continuous_transport_ids
            )
        ):
            raise ValueError(
                "initial enabled transports changed mounted topology"
            )
        mass_weight = {
            component.component_id: species_by_id[
                component.species_id
            ].conserved_mass_per_quantity.value
            for component in self.components
        }
        for reaction in self.conversions:
            reactant = components_by_id.get(reaction.reactant_component_id)
            product = components_by_id.get(reaction.product_component_id)
            if (
                reactant is None
                or product is None
                or reactant.node_id != reaction.node_id
                or product.node_id != reaction.node_id
                or reactant.species_id == product.species_id
                or reaction.rate.unit != "per-time"
                or reaction.product_quantity_per_reactant.unit
                != (
                    f"{species_by_id[product.species_id].quantity_unit}"
                    f"-per-"
                    f"{species_by_id[reactant.species_id].quantity_unit}"
                )
                or (
                    reaction.product_quantity_per_reactant.value
                    * mass_weight[product.component_id]
                    != mass_weight[reactant.component_id]
                )
            ):
                raise ValueError(
                    "first-order conversion violates exact stoichiometry"
                )
        for target in self.local_targets:
            if target.component_id not in components_by_id:
                raise ValueError("local target names an unmounted component")
        if (
            len(self.components) > self.capacity.max_components
            or len(self.conversions) > self.capacity.max_reactions
            or len(self.upstream_issuers) > self.capacity.max_components
            or len(self.physical_route_permissions) > self.capacity.max_lanes
            or len(self.temporal_route_permissions) > self.capacity.max_lanes
            or len(self.local_targets) > self.capacity.max_targets
        ):
            raise ValueError("mounted topology exceeds declared capacity")
        quantity_ids: set[str] = set()
        for receipt in _iter_signed_manifest_quantities(
            structural_time_unit=self.structural_time_unit,
            species=self.species,
            nodes=self.nodes,
            components=self.components,
            drift_lanes=self.drift_lanes,
            diffusion_interfaces=self.diffusion_interfaces,
            conversions=self.conversions,
        ):
            if receipt.quantity_id in quantity_ids:
                raise ValueError(
                    "mounted physical quantity authority is reused"
                )
            quantity_ids.add(receipt.quantity_id)
        payload = self.payload()
        if len(_canonical(payload)) > MAX_MANIFEST_BYTES:
            raise ValueError("neurochemical manifest exceeds byte boundary")
        manifest_key = hashlib.sha256(
            _MANIFEST_DOMAIN + _key(authority_key)
        ).digest()
        expected_hmac = hmac.new(
            manifest_key,
            _MANIFEST_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            self.authority_hmac_sha256 != expected_hmac
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise ValueError("neurochemical manifest authority changed")

def create_neurochemical_flow_manifest(
    *,
    authority_key: bytes | str,
    manifest_id: str,
    structural_time_unit: SignedPhysicalQuantity,
    backend: NeurochemicalBackendMount,
    physical_quantity_issuers: Sequence[PhysicalQuantityVerifierMount],
    species: Sequence[NeurochemicalSpeciesMount],
    nodes: Sequence[NeurochemicalNodeMount],
    components: Sequence[NeurochemicalCompartmentMount],
    impulse_routes: Sequence[NeurochemicalImpulseRoute],
    drift_lanes: Sequence[NeurochemicalDriftLane],
    diffusion_interfaces: Sequence[ExtracellularDiffusionInterface],
    conversions: Sequence[FirstOrderNeurochemicalConversion],
    upstream_issuers: Sequence[UpstreamIssuerVerifierMount],
    physical_route_permissions: Sequence[PhysicalReceiptRoutePermission],
    temporal_route_permissions: Sequence[TemporalReceiptRoutePermission],
    local_targets: Sequence[LocalNeurochemicalTarget],
    unavailable_nonlinear_mechanisms: Sequence[
        UnavailableNonlinearMechanism
    ],
    initial_enabled_transport_ids: Sequence[str],
    capacity: NeurochemicalCapacity,
) -> NeurochemicalFlowManifest:
    if not isinstance(capacity, NeurochemicalCapacity):
        raise TypeError("neurochemical capacity is not typed")
    if not isinstance(structural_time_unit, SignedPhysicalQuantity):
        raise TypeError("structural time quantity is not typed")
    capacity.verify()
    for label, values in (
        ("impulse routes", impulse_routes),
        ("drift lanes", drift_lanes),
        ("diffusion interfaces", diffusion_interfaces),
    ):
        if not isinstance(values, Sequence):
            raise ValueError(
                f"neurochemical {label} exceed authenticated capacity"
            )
    _verify_total_transport_capacity(
        impulse_routes=impulse_routes,
        drift_lanes=drift_lanes,
        diffusion_interfaces=diffusion_interfaces,
        maximum_lanes=capacity.max_lanes,
    )
    admitted_lengths = (
        ("species", species, capacity.max_components),
        ("nodes", nodes, capacity.max_components),
        ("components", components, capacity.max_components),
        ("impulse routes", impulse_routes, capacity.max_lanes),
        ("drift lanes", drift_lanes, capacity.max_lanes),
        ("diffusion interfaces", diffusion_interfaces, capacity.max_lanes),
        ("conversions", conversions, capacity.max_reactions),
        (
            "physical quantity issuers",
            physical_quantity_issuers,
            capacity.max_components,
        ),
        ("upstream issuers", upstream_issuers, capacity.max_components),
        (
            "physical route permissions",
            physical_route_permissions,
            capacity.max_lanes,
        ),
        (
            "temporal route permissions",
            temporal_route_permissions,
            capacity.max_lanes,
        ),
        ("targets", local_targets, capacity.max_targets),
        (
            "nonlinear mechanisms",
            unavailable_nonlinear_mechanisms,
            capacity.max_reactions,
        ),
        (
            "initial enabled transports",
            initial_enabled_transport_ids,
            capacity.max_lanes,
        ),
    )
    for label, values, admitted in admitted_lengths:
        if not isinstance(values, Sequence) or len(values) > admitted:
            raise ValueError(
                f"neurochemical {label} exceed authenticated capacity"
            )
    species = tuple(species)
    nodes = tuple(nodes)
    components = tuple(components)
    impulse_routes = tuple(impulse_routes)
    drift_lanes = tuple(drift_lanes)
    diffusion_interfaces = tuple(diffusion_interfaces)
    conversions = tuple(conversions)
    physical_quantity_issuers = tuple(physical_quantity_issuers)
    upstream_issuers = tuple(upstream_issuers)
    physical_route_permissions = tuple(physical_route_permissions)
    temporal_route_permissions = tuple(temporal_route_permissions)
    local_targets = tuple(local_targets)
    unavailable_nonlinear_mechanisms = tuple(
        unavailable_nonlinear_mechanisms
    )
    typed_inputs = (
        (physical_quantity_issuers, PhysicalQuantityVerifierMount),
        (species, NeurochemicalSpeciesMount),
        (nodes, NeurochemicalNodeMount),
        (components, NeurochemicalCompartmentMount),
        (impulse_routes, NeurochemicalImpulseRoute),
        (drift_lanes, NeurochemicalDriftLane),
        (diffusion_interfaces, ExtracellularDiffusionInterface),
        (conversions, FirstOrderNeurochemicalConversion),
        (upstream_issuers, UpstreamIssuerVerifierMount),
        (physical_route_permissions, PhysicalReceiptRoutePermission),
        (temporal_route_permissions, TemporalReceiptRoutePermission),
        (local_targets, LocalNeurochemicalTarget),
        (
            unavailable_nonlinear_mechanisms,
            UnavailableNonlinearMechanism,
        ),
    )
    for values, expected_type in typed_inputs:
        if any(not isinstance(value, expected_type) for value in values):
            raise TypeError("neurochemical manifest input is not correctly typed")
    backend.verify(live=False)
    quantity_issuer_by_id = {
        value.issuer_id: value for value in physical_quantity_issuers
    }
    for value in physical_quantity_issuers:
        value.verify()
    signed_quantities = _iter_signed_manifest_quantities(
        structural_time_unit=structural_time_unit,
        species=species,
        nodes=nodes,
        components=components,
        drift_lanes=drift_lanes,
        diffusion_interfaces=diffusion_interfaces,
        conversions=conversions,
    )
    signed_quantity_bytes = 0
    for receipt in signed_quantities:
        issuer = quantity_issuer_by_id.get(receipt.issuer_id)
        if issuer is None:
            raise ValueError("physical quantity issuer is not mounted")
        verify_signed_physical_quantity(receipt, issuer)
        signed_quantity_bytes += len(_canonical(receipt.record()))
        if signed_quantity_bytes > MAX_MANIFEST_BYTES:
            raise ValueError(
                "physical quantity receipts exceed manifest byte capacity"
            )
    for value in impulse_routes:
        value.verify()
    for value in upstream_issuers:
        value.verify()
    for value in physical_route_permissions:
        value.verify()
    for value in temporal_route_permissions:
        value.verify()
    for value in local_targets:
        value.verify()
    for value in unavailable_nonlinear_mechanisms:
        value.verify()
    derivation_payloads = (
        backend.derivation_receipt_payload,
        *(value.derivation_receipt_payload for value in local_targets),
        *(
            value.derivation_receipt_payload
            for value in unavailable_nonlinear_mechanisms
        ),
    )
    if any(
        len(payload) > capacity.max_derivation_receipt_bytes
        for payload in derivation_payloads
    ):
        raise ValueError(
            "manifest derivation exceeds authenticated byte capacity"
        )
    conservative_manifest_bytes = (
        signed_quantity_bytes
        + sum(2 * len(payload) for payload in derivation_payloads)
        + sum(
            len(values)
            for values in (
                physical_quantity_issuers,
                species,
                nodes,
                components,
                impulse_routes,
                drift_lanes,
                diffusion_interfaces,
                conversions,
                upstream_issuers,
                physical_route_permissions,
                temporal_route_permissions,
                local_targets,
                unavailable_nonlinear_mechanisms,
            )
        )
        * 4096
    )
    if conservative_manifest_bytes > MAX_MANIFEST_BYTES:
        raise ValueError(
            "neurochemical manifest exceeds pre-allocation byte capacity"
        )
    provisional = NeurochemicalFlowManifest(
        manifest_id=manifest_id,
        structural_time_unit=structural_time_unit,
        backend=backend,
        physical_quantity_issuers=physical_quantity_issuers,
        species=species,
        nodes=nodes,
        components=components,
        impulse_routes=impulse_routes,
        drift_lanes=drift_lanes,
        diffusion_interfaces=diffusion_interfaces,
        conversions=conversions,
        upstream_issuers=upstream_issuers,
        physical_route_permissions=physical_route_permissions,
        temporal_route_permissions=temporal_route_permissions,
        local_targets=local_targets,
        unavailable_nonlinear_mechanisms=unavailable_nonlinear_mechanisms,
        initial_enabled_transport_ids=tuple(initial_enabled_transport_ids),
        capacity=capacity,
        authority_hmac_sha256="0" * 64,
        authority_receipt_sha256="0" * 64,
    )
    payload = provisional.payload()
    manifest_key = hashlib.sha256(
        _MANIFEST_DOMAIN + _key(authority_key)
    ).digest()
    signature = hmac.new(
        manifest_key,
        _MANIFEST_DOMAIN + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    result = NeurochemicalFlowManifest(
        **{
            name: getattr(provisional, name)
            for name in provisional.__dataclass_fields__
            if name not in {
                "authority_hmac_sha256",
                "authority_receipt_sha256",
            }
        },
        authority_hmac_sha256=signature,
        authority_receipt_sha256=_digest({
            "authority_hmac_sha256": signature,
            "payload": payload,
        }),
    )
    result.verify(authority_key)
    return result


@dataclass(frozen=True, slots=True)
class NeurochemicalCausalEvent:
    event_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    physical_receipts: tuple[PhysicalNeurochemicalReceipt, ...]
    temporal_receipts: tuple[TemporalNeurochemicalReceipt, ...]
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "physical_receipts": [
                value.record() for value in self.physical_receipts
            ],
            "schema": EVENT_SCHEMA,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "temporal_receipts": [
                value.record() for value in self.temporal_receipts
            ],
        }


ChemicalValue = Fraction | CertifiedBall


def _value_record(value: ChemicalValue) -> dict[str, object]:
    if isinstance(value, Fraction):
        return {"exact": _fraction_text(value)}
    if isinstance(value, CertifiedBall):
        return {"certified_interval": _ball_record(value)}
    raise TypeError("neurochemical component value is not typed")


def _value_from_record(value: object) -> ChemicalValue:
    if not isinstance(value, dict):
        raise ValueError("neurochemical component value changed shape")
    if set(value) == {"exact"}:
        return _fraction_from_text(value["exact"], "exact component quantity")
    if set(value) == {"certified_interval"}:
        return _ball_from_record(value["certified_interval"])
    raise ValueError("neurochemical component value is not typed")


def _value_bounds(value: ChemicalValue) -> tuple[Fraction, Fraction]:
    if isinstance(value, Fraction):
        return value, value
    return _ball_bounds(value)


@dataclass(frozen=True, slots=True)
class NeurochemicalFlowState:
    source_time: Fraction
    manifest_receipt_sha256: str
    component_values: tuple[tuple[str, ChemicalValue], ...]
    enabled_transport_ids: tuple[str, ...]
    last_accepted_sequence_by_issuer: tuple[tuple[str, int], ...]
    exact_conserved_mass: Fraction
    prior_state_receipt_sha256: str | None
    causal_event_receipt_sha256: str | None
    receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "causal_event_receipt_sha256": (
                self.causal_event_receipt_sha256
            ),
            "component_values": [
                {"component_id": component_id, "value": _value_record(value)}
                for component_id, value in self.component_values
            ],
            "constraint": (
                "sum(conserved_mass_per_quantity*quantity)="
                "exact_conserved_mass"
            ),
            "enabled_transport_ids": list(self.enabled_transport_ids),
            "last_accepted_sequence_by_issuer": [
                {"issuer_id": issuer_id, "sequence": sequence}
                for issuer_id, sequence in self.last_accepted_sequence_by_issuer
            ],
            "exact_conserved_mass": _fraction_text(
                self.exact_conserved_mass
            ),
            "manifest_receipt_sha256": self.manifest_receipt_sha256,
            "prior_state_receipt_sha256": (
                self.prior_state_receipt_sha256
            ),
            "schema": STATE_SCHEMA,
            "source_time": _fraction_text(self.source_time),
        }

    def record(self) -> dict[str, object]:
        return {**self.payload(), "receipt_sha256": self.receipt_sha256}


@dataclass(frozen=True, slots=True)
class SparseGeneratorEntry:
    row_component_id: str
    column_component_id: str
    value_per_time_unit: Fraction

    def record(self) -> dict[str, object]:
        return {
            "column_component_id": self.column_component_id,
            "row_component_id": self.row_component_id,
            "value_per_time_unit": _fraction_text(
                self.value_per_time_unit
            ),
        }


@dataclass(frozen=True, slots=True)
class LocalTargetExposure:
    target_id: str
    component_id: str
    target_kind: LocalTargetKind
    component_value: ChemicalValue
    receptor_activation_availability: MechanismAvailability
    component_state_receipt_sha256: str

    def record(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "component_state_receipt_sha256": (
                self.component_state_receipt_sha256
            ),
            "component_value": _value_record(self.component_value),
            "receptor_activation_availability": (
                self.receptor_activation_availability.value
            ),
            "target_id": self.target_id,
            "target_kind": self.target_kind.value,
        }


@dataclass(frozen=True, slots=True)
class NeurochemicalFlowTransition:
    event: NeurochemicalCausalEvent
    prior_state_receipt_sha256: str
    result_state_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    generator_entries: tuple[SparseGeneratorEntry, ...]
    exact_active_blocks: tuple[tuple[str, ...], ...]
    untouched_component_ids: tuple[str, ...]
    local_target_exposures: tuple[LocalTargetExposure, ...]
    backend_authority_id: str
    working_precision_bits: int
    receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "backend": {
                "authority_id": self.backend_authority_id,
                "flint_version": FLINT_VERSION,
                "python_flint_version": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
                "working_precision_bits": self.working_precision_bits,
            },
            "causal_event": {
                **self.event.payload(),
                "authority_receipt_sha256": (
                    self.event.authority_receipt_sha256
                ),
            },
            "conservation": (
                "exact_mass_weighted_zero_columns_including_external_reservoirs"
            ),
            "exact_active_blocks": [
                list(value) for value in self.exact_active_blocks
            ],
            "generator_entries": [
                value.record() for value in self.generator_entries
            ],
            "integration": (
                "analytic_certified_elapsed_time_matrix_exponential"
            ),
            "local_target_exposures": [
                value.record() for value in self.local_target_exposures
            ],
            "prior_state_receipt_sha256": self.prior_state_receipt_sha256,
            "result_state_receipt_sha256": self.result_state_receipt_sha256,
            "schema": TRANSITION_SCHEMA,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "untouched_component_ids": list(
                self.untouched_component_ids
            ),
        }

    def record(self) -> dict[str, object]:
        return {**self.payload(), "receipt_sha256": self.receipt_sha256}


@dataclass(frozen=True, slots=True)
class NeurochemicalEvolutionResult:
    status: EvolutionStatus
    state: NeurochemicalFlowState
    transition: NeurochemicalFlowTransition | None
    reason: str


class NeurochemicalFlowFieldAuthority:
    """Own one current sparse field state and evolve only at causal boundaries."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        manifest: NeurochemicalFlowManifest,
    ) -> None:
        raw_key = _key(authority_key)
        manifest.verify(raw_key)
        self._cold_key = hashlib.sha256(_COLD_DOMAIN + raw_key).digest()
        self._manifest = manifest
        self._lock = threading.RLock()
        self._component_by_id = {
            value.component_id: value for value in manifest.components
        }
        self._node_by_id = {
            value.node_id: value for value in manifest.nodes
        }
        self._impulse_route_by_id = {
            value.lane_id: value for value in manifest.impulse_routes
        }
        self._drift_by_id = {
            value.lane_id: value for value in manifest.drift_lanes
        }
        self._interface_by_id = {
            value.interface_id: value
            for value in manifest.diffusion_interfaces
        }
        self._continuous_transport_ids = (
            set(self._drift_by_id) | set(self._interface_by_id)
        )
        self._species_by_id = {
            value.species_id: value for value in manifest.species
        }
        self._issuer_by_id = {
            value.issuer_id: value for value in manifest.upstream_issuers
        }
        self._physical_permission_keys = {
            (
                value.issuer_id,
                value.source_kind,
                value.source_component_id,
                value.lane_id,
                value.destination_component_id,
                value.amount_unit,
            )
            for value in manifest.physical_route_permissions
        }
        self._temporal_permission_keys = {
            (
                value.issuer_id,
                value.driver_kind,
                value.lane_id,
                value.lane_enabled,
                value.physical_parameter_path,
            )
            for value in manifest.temporal_route_permissions
        }
        initial_values = tuple(
            (value.component_id, value.initial_quantity.value)
            for value in manifest.components
        )
        conserved = sum(
            (
                value.initial_quantity.value
                * self._species_by_id[
                    value.species_id
                ].conserved_mass_per_quantity.value
                for value in manifest.components
            ),
            Fraction(0),
        )
        provisional = NeurochemicalFlowState(
            source_time=Fraction(0),
            manifest_receipt_sha256=manifest.authority_receipt_sha256,
            component_values=initial_values,
            enabled_transport_ids=manifest.initial_enabled_transport_ids,
            last_accepted_sequence_by_issuer=tuple(
                (issuer.issuer_id, 0) for issuer in manifest.upstream_issuers
            ),
            exact_conserved_mass=conserved,
            prior_state_receipt_sha256=None,
            causal_event_receipt_sha256=None,
            receipt_sha256="0" * 64,
        )
        self._state = NeurochemicalFlowState(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name != "receipt_sha256"
            },
            receipt_sha256=_digest(provisional.payload()),
        )
        self._last_transition: NeurochemicalFlowTransition | None = None
        self._verify_state(self._state)
        self._encoded(self._state, self._last_transition)

    @property
    def manifest(self) -> NeurochemicalFlowManifest:
        return self._manifest

    @property
    def state(self) -> NeurochemicalFlowState:
        with self._lock:
            return self._state

    @property
    def last_transition(self) -> NeurochemicalFlowTransition | None:
        with self._lock:
            return self._last_transition

    def create_causal_event(
        self,
        *,
        upstream_receipts: Sequence[UpstreamNeurochemicalReceipt],
    ) -> NeurochemicalCausalEvent:
        if (
            not isinstance(upstream_receipts, Sequence)
            or not upstream_receipts
            or len(upstream_receipts)
            > self._manifest.capacity.max_events_per_boundary
        ):
            raise ValueError(
                "neurochemical event requires bounded upstream receipts"
            )
        first = upstream_receipts[0]
        if not isinstance(
            first,
            (PhysicalNeurochemicalReceipt, TemporalNeurochemicalReceipt),
        ):
            raise TypeError("upstream neurochemical receipt is not typed")
        physical_receipts = tuple(
            value
            for value in upstream_receipts
            if isinstance(value, PhysicalNeurochemicalReceipt)
        )
        temporal_receipts = tuple(
            value
            for value in upstream_receipts
            if isinstance(value, TemporalNeurochemicalReceipt)
        )
        if len(physical_receipts) + len(temporal_receipts) != len(
            upstream_receipts
        ):
            raise TypeError("upstream neurochemical receipt is not typed")
        for receipt in upstream_receipts:
            self._verify_upstream_route(receipt)
            if (
                receipt.event_id != first.event_id
                or receipt.source_time_start != first.source_time_start
                or receipt.source_time_end != first.source_time_end
            ):
                raise ValueError(
                    "upstream receipt covers another event or interval"
                )
        provisional = NeurochemicalCausalEvent(
            event_id=first.event_id,
            source_time_start=first.source_time_start,
            source_time_end=first.source_time_end,
            physical_receipts=physical_receipts,
            temporal_receipts=temporal_receipts,
            authority_receipt_sha256="0" * 64,
        )
        result = NeurochemicalCausalEvent(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name != "authority_receipt_sha256"
            },
            authority_receipt_sha256=_digest(provisional.payload()),
        )
        self._verify_event_shape(result, verify_sequence=False)
        return result

    def _verify_upstream_route(
        self,
        receipt: UpstreamNeurochemicalReceipt,
    ) -> None:
        mount = self._issuer_by_id.get(receipt.issuer_id)
        if mount is None:
            raise ValueError("upstream neurochemical issuer is not mounted")
        verify_upstream_receipt(receipt, mount)
        if isinstance(receipt, PhysicalNeurochemicalReceipt):
            key = (
                receipt.issuer_id,
                receipt.source_kind,
                receipt.source_component_id,
                receipt.lane_id,
                receipt.destination_component_id,
                receipt.amount_unit,
            )
            if key not in self._physical_permission_keys:
                raise ValueError(
                    "physical receipt route is not permitted by manifest"
                )
        else:
            key = (
                receipt.issuer_id,
                receipt.driver_kind,
                receipt.lane_id,
                receipt.lane_enabled,
                receipt.physical_parameter_path,
            )
            if key not in self._temporal_permission_keys:
                raise ValueError(
                    "temporal receipt route is not permitted by manifest"
                )

    def _verify_event_shape(
        self,
        event: NeurochemicalCausalEvent,
        *,
        verify_sequence: bool,
    ) -> None:
        if not isinstance(event, NeurochemicalCausalEvent):
            raise TypeError("neurochemical event is not typed")
        _identifier(event.event_id, "neurochemical event id")
        _fraction(event.source_time_start, "neurochemical event start")
        _fraction(event.source_time_end, "neurochemical event end")
        if event.source_time_end <= event.source_time_start:
            raise ValueError("neurochemical event requires positive elapsed time")
        if (
            not isinstance(event.physical_receipts, tuple)
            or not isinstance(event.temporal_receipts, tuple)
            or any(
                not isinstance(value, PhysicalNeurochemicalReceipt)
                for value in event.physical_receipts
            )
            or any(
                not isinstance(value, TemporalNeurochemicalReceipt)
                for value in event.temporal_receipts
            )
        ):
            raise TypeError("verified neurochemical event receipts are not typed")
        count = len(event.physical_receipts) + len(event.temporal_receipts)
        if (
            count == 0
            or count > self._manifest.capacity.max_events_per_boundary
        ):
            raise ValueError("neurochemical causal event cardinality is invalid")
        identifier_bytes = len(event.event_id.encode("utf-8")) + sum(
            len(value.issuer_id.encode("utf-8"))
            + len(value.lane_id.encode("utf-8"))
            for value in (*event.physical_receipts, *event.temporal_receipts)
        )
        conservative_encoding_bound = (
            4096
            + count * 2048
            + identifier_bytes
        )
        if conservative_encoding_bound > self._manifest.capacity.max_event_bytes:
            raise ValueError(
                "neurochemical event exceeds authenticated byte capacity"
            )
        receipts = (*event.physical_receipts, *event.temporal_receipts)
        identities = tuple(
            (value.issuer_id, value.chemistry_sequence) for value in receipts
        )
        if identities != tuple(sorted(set(identities))):
            raise ValueError("neurochemical event members are not canonical")
        for receipt in receipts:
            self._verify_upstream_route(receipt)
            if (
                len(_canonical(receipt.record()))
                > self._manifest.capacity.max_causal_receipt_bytes
            ):
                raise ValueError(
                    "upstream receipt exceeds authenticated byte capacity"
                )
            if (
                receipt.event_id != event.event_id
                or receipt.source_time_start != event.source_time_start
                or receipt.source_time_end != event.source_time_end
            ):
                raise ValueError(
                    "upstream receipt covers another event or interval"
                )
        if event.physical_receipts and event.temporal_receipts:
            raise ValueError(
                "temporal edge changes and physical transfers require "
                "separate causal boundaries"
            )
        payload = event.payload()
        if (
            len(_canonical(payload))
            > self._manifest.capacity.max_event_bytes
        ):
            raise ValueError(
                "neurochemical event exceeds authenticated byte capacity"
            )
        if event.authority_receipt_sha256 != _digest(payload):
            raise ValueError("verified neurochemical event receipt changed")
        if verify_sequence:
            accepted = dict(self._state.last_accepted_sequence_by_issuer)
            for receipt in receipts:
                expected = accepted[receipt.issuer_id] + 1
                if receipt.chemistry_sequence != expected:
                    raise ValueError(
                        "upstream chemistry sequence is replayed, duplicated, "
                        "or has a gap"
                    )
                accepted[receipt.issuer_id] = receipt.chemistry_sequence

    def _accepted_sequences_after(
        self,
        event: NeurochemicalCausalEvent,
    ) -> tuple[tuple[str, int], ...]:
        accepted = dict(self._state.last_accepted_sequence_by_issuer)
        for receipt in (*event.physical_receipts, *event.temporal_receipts):
            accepted[receipt.issuer_id] = receipt.chemistry_sequence
        return tuple(sorted(accepted.items()))

    def _mass_weight_by_component(self) -> dict[str, Fraction]:
        return {
            component.component_id: self._species_by_id[
                component.species_id
            ].conserved_mass_per_quantity.value
            for component in self._manifest.components
        }

    def _verify_state(self, state: NeurochemicalFlowState) -> None:
        if not isinstance(state, NeurochemicalFlowState):
            raise TypeError("neurochemical field state is not typed")
        _fraction(state.source_time, "neurochemical state time")
        if (
            state.manifest_receipt_sha256
            != self._manifest.authority_receipt_sha256
            or tuple(value[0] for value in state.component_values)
            != tuple(
                value.component_id for value in self._manifest.components
            )
            or state.enabled_transport_ids
            != tuple(sorted(set(state.enabled_transport_ids)))
            or len(state.enabled_transport_ids)
            > self._manifest.capacity.max_lanes
            or not set(state.enabled_transport_ids).issubset(
                self._continuous_transport_ids
            )
            or tuple(
                issuer_id
                for issuer_id, _ in state.last_accepted_sequence_by_issuer
            )
            != tuple(value.issuer_id for value in self._manifest.upstream_issuers)
        ):
            raise ValueError("neurochemical state left its mounted topology")
        for _, sequence in state.last_accepted_sequence_by_issuer:
            if (
                isinstance(sequence, bool)
                or not isinstance(sequence, int)
                or sequence < 0
                or sequence.bit_length() > MAX_UPSTREAM_SEQUENCE_BITS
            ):
                raise ValueError("upstream accepted sequence is invalid")
        weights = self._mass_weight_by_component()
        lower_mass = Fraction(0)
        upper_mass = Fraction(0)
        all_components_exact_zero = True
        for component_id, value in state.component_values:
            lower, upper = _value_bounds(value)
            if lower < 0:
                raise ValueError(
                    "neurochemical state excludes nonnegative quantity"
                )
            lower_mass += lower * weights[component_id]
            upper_mass += upper * weights[component_id]
            all_components_exact_zero = (
                all_components_exact_zero and lower == 0 and upper == 0
            )
        if (
            state.exact_conserved_mass < 0
            or (
                state.exact_conserved_mass == 0
                and not all_components_exact_zero
            )
            or lower_mass > state.exact_conserved_mass
            or upper_mass < state.exact_conserved_mass
        ):
            raise ValueError("neurochemical state lost conserved mass")
        for value in (
            state.prior_state_receipt_sha256,
            state.causal_event_receipt_sha256,
        ):
            if value is not None:
                _sha(value, "neurochemical causal state receipt")
        if state.receipt_sha256 != _digest(state.payload()):
            raise ValueError("neurochemical state receipt changed")

    def _enabled_after(
        self,
        event: NeurochemicalCausalEvent,
    ) -> tuple[str, ...]:
        enabled = set(self._state.enabled_transport_ids)
        for receipt in event.temporal_receipts:
            if receipt.lane_enabled:
                enabled.add(receipt.lane_id)
            else:
                enabled.discard(receipt.lane_id)
        result = tuple(sorted(enabled))
        if len(result) > self._manifest.capacity.max_lanes:
            raise ValueError(
                "enabled transport identities exceed authenticated "
                "lane capacity"
            )
        return result

    def _generator(
        self,
        enabled_transport_ids: tuple[str, ...],
    ) -> tuple[SparseGeneratorEntry, ...]:
        entries: dict[tuple[str, str], Fraction] = {}

        def add(row: str, column: str, value: Fraction) -> None:
            key = (row, column)
            entries[key] = entries.get(key, Fraction(0)) + value

        for transport_id in enabled_transport_ids:
            drift = self._drift_by_id.get(transport_id)
            if drift is not None:
                source_component = self._component_by_id[
                    drift.source_component_id
                ]
                source_volume = self._node_by_id[
                    source_component.node_id
                ].volume.value
                rate = (
                    drift.velocity.value
                    * drift.interface_area.value
                    / source_volume
                )
                add(
                    drift.source_component_id,
                    drift.source_component_id,
                    -rate,
                )
                add(
                    drift.target_component_id,
                    drift.source_component_id,
                    rate,
                )
                continue
            interface = self._interface_by_id[transport_id]
            component_a = self._component_by_id[
                interface.endpoint_a_component_id
            ]
            component_b = self._component_by_id[
                interface.endpoint_b_component_id
            ]
            volume_a = self._node_by_id[component_a.node_id].volume.value
            volume_b = self._node_by_id[component_b.node_id].volume.value
            common = (
                interface.diffusion_coefficient.value
                * interface.interface_area.value
                / interface.path_length.value
            )
            rate_a_to_b = common / volume_a
            rate_b_to_a = common / volume_b
            add(
                interface.endpoint_a_component_id,
                interface.endpoint_a_component_id,
                -rate_a_to_b,
            )
            add(
                interface.endpoint_b_component_id,
                interface.endpoint_a_component_id,
                rate_a_to_b,
            )
            add(
                interface.endpoint_b_component_id,
                interface.endpoint_b_component_id,
                -rate_b_to_a,
            )
            add(
                interface.endpoint_a_component_id,
                interface.endpoint_b_component_id,
                rate_b_to_a,
            )
        for reaction in self._manifest.conversions:
            rate = reaction.rate.value
            ratio = reaction.product_quantity_per_reactant.value
            add(
                reaction.reactant_component_id,
                reaction.reactant_component_id,
                -rate,
            )
            add(
                reaction.product_component_id,
                reaction.reactant_component_id,
                rate * ratio,
            )
        result = tuple(
            SparseGeneratorEntry(row, column, value)
            for (row, column), value in sorted(entries.items())
            if value != 0
        )
        weights = self._mass_weight_by_component()
        weighted_column_sums: dict[str, Fraction] = {}
        for entry in result:
            weighted_column_sums[entry.column_component_id] = (
                weighted_column_sums.get(
                    entry.column_component_id,
                    Fraction(0),
                )
                + weights[entry.row_component_id]
                * entry.value_per_time_unit
            )
            if (
                entry.row_component_id != entry.column_component_id
                and entry.value_per_time_unit < 0
            ):
                raise ValueError("neurochemical generator is not Metzler")
        for weighted_sum in weighted_column_sums.values():
            if weighted_sum != 0:
                raise ValueError(
                    "neurochemical generator lost exact stoichiometric mass"
                )
        return result

    @staticmethod
    def _active_blocks(
        entries: tuple[SparseGeneratorEntry, ...],
    ) -> tuple[tuple[str, ...], ...]:
        adjacency: dict[str, set[str]] = {}
        for entry in entries:
            if entry.row_component_id == entry.column_component_id:
                adjacency.setdefault(entry.row_component_id, set())
                continue
            adjacency.setdefault(entry.row_component_id, set()).add(
                entry.column_component_id
            )
            adjacency.setdefault(entry.column_component_id, set()).add(
                entry.row_component_id
            )
        remaining = set(adjacency)
        blocks = []
        while remaining:
            seed = min(remaining)
            stack = [seed]
            block = set()
            while stack:
                current = stack.pop()
                if current in block:
                    continue
                block.add(current)
                stack.extend(sorted(adjacency.get(current, ()), reverse=True))
            remaining.difference_update(block)
            blocks.append(tuple(sorted(block)))
        return tuple(sorted(blocks))

    def _evolved_values(
        self,
        *,
        event: NeurochemicalCausalEvent,
        entries: tuple[SparseGeneratorEntry, ...],
        blocks: tuple[tuple[str, ...], ...],
    ) -> tuple[
        tuple[tuple[str, ChemicalValue], ...],
        tuple[str, ...],
    ]:
        current = dict(self._state.component_values)
        deltas = {
            value.component_id: Fraction(0)
            for value in self._manifest.components
        }
        for transfer in event.physical_receipts:
            lane = self._impulse_route_by_id[transfer.lane_id]
            source = lane.source_component_id
            target = lane.target_component_id
            available_lower = (
                _value_bounds(current[source])[0] + deltas[source]
            )
            if available_lower < transfer.amount:
                raise ValueError(
                    "causal transfer is not certified by source quantity"
                )
            deltas[source] -= transfer.amount
            deltas[target] += transfer.amount
        if all(
            isinstance(value, Fraction)
            and value == 0
            and deltas[component_id] == 0
            for component_id, value in self._state.component_values
        ):
            return (
                self._state.component_values,
                tuple(
                    component_id
                    for component_id, _ in self._state.component_values
                ),
            )
        flint = load_pinned_flint()
        precision = self._manifest.backend.working_precision_bits
        delta_time = event.source_time_end - event.source_time_start
        evolved: dict[str, ChemicalValue] = {}
        active_ids = {value for block in blocks for value in block}
        if any(
            len(block) > self._manifest.capacity.max_active_block_components
            for block in blocks
        ):
            raise ValueError(
                "active neurochemical block exceeds authenticated capacity"
            )
        block_by_component = {
            component_id: block_index
            for block_index, block in enumerate(blocks)
            for component_id in block
        }
        entries_by_block: list[list[SparseGeneratorEntry]] = [
            [] for _ in blocks
        ]
        for entry in entries:
            block_index = block_by_component[entry.column_component_id]
            if block_by_component[entry.row_component_id] != block_index:
                raise ValueError(
                    "generator entry crosses exact connected blocks"
                )
            entries_by_block[block_index].append(entry)
        with flint.ctx.workprec(precision):
            for block_index, block in enumerate(blocks):
                index = {
                    component_id: offset
                    for offset, component_id in enumerate(block)
                }
                matrix = flint.arb_mat(len(block), len(block))
                for entry in entries_by_block[block_index]:
                    matrix[
                        index[entry.row_component_id],
                        index[entry.column_component_id],
                    ] = arb_fraction(flint, entry.value_per_time_unit)
                transition = (
                    matrix * arb_fraction(flint, delta_time)
                ).exp()
                if not all(
                    transition[row, column].is_finite()
                    for row in range(len(block))
                    for column in range(len(block))
                ):
                    raise ValueError(
                        "neurochemical block exponential is nonfinite"
                    )
                initial_values = []
                for component_id in block:
                    value = current[component_id]
                    initial = (
                        arb_fraction(flint, value)
                        if isinstance(value, Fraction)
                        else _arb_from_ball(flint, value)
                    )
                    initial_values.append(
                        initial + arb_fraction(flint, deltas[component_id])
                    )
                result = transition * flint.arb_mat(
                    len(block), 1, initial_values
                )
                for component_id, offset in index.items():
                    if not result[offset, 0].is_finite():
                        raise ValueError(
                            "neurochemical block result is nonfinite"
                        )
                    evolved[component_id] = canonical_ball(
                        result[offset, 0],
                        precision,
                    )
        for component_id, value in current.items():
            if component_id in active_ids:
                continue
            change = deltas[component_id]
            if change == 0:
                evolved[component_id] = value
            elif isinstance(value, Fraction):
                evolved[component_id] = value + change
            else:
                with flint.ctx.workprec(precision):
                    evolved[component_id] = canonical_ball(
                        _arb_from_ball(flint, value)
                        + arb_fraction(flint, change),
                        precision,
                    )
        untouched = tuple(
            component_id
            for component_id, value in self._state.component_values
            if component_id not in active_ids
            and deltas[component_id] == 0
            and evolved[component_id] is value
        )
        return (
            tuple(
                (component.component_id, evolved[component.component_id])
                for component in self._manifest.components
            ),
            untouched,
        )

    def _target_exposures(
        self,
        state: NeurochemicalFlowState,
    ) -> tuple[LocalTargetExposure, ...]:
        values = dict(state.component_values)
        return tuple(
            LocalTargetExposure(
                target_id=target.target_id,
                component_id=target.component_id,
                target_kind=target.kind,
                component_value=values[target.component_id],
                receptor_activation_availability=(
                    target.receptor_activation_availability
                ),
                component_state_receipt_sha256=_digest({
                    "component_id": target.component_id,
                    "state_receipt_sha256": state.receipt_sha256,
                    "value": _value_record(values[target.component_id]),
                }),
            )
            for target in self._manifest.local_targets
        )

    def evolve(
        self,
        event: NeurochemicalCausalEvent,
    ) -> NeurochemicalEvolutionResult:
        with self._lock:
            prior_snapshot = self.snapshot_encoded()
            try:
                self._verify_event_shape(event, verify_sequence=True)
                if event.source_time_start != self._state.source_time:
                    raise ValueError(
                        "causal event does not begin at current field time"
                    )
                enabled = self._enabled_after(event)
                entries = self._generator(enabled)
                blocks = self._active_blocks(entries)
                values, untouched = self._evolved_values(
                    event=event,
                    entries=entries,
                    blocks=blocks,
                )
                provisional = NeurochemicalFlowState(
                    source_time=event.source_time_end,
                    manifest_receipt_sha256=(
                        self._manifest.authority_receipt_sha256
                    ),
                    component_values=values,
                    enabled_transport_ids=enabled,
                    last_accepted_sequence_by_issuer=(
                        self._accepted_sequences_after(event)
                    ),
                    exact_conserved_mass=self._state.exact_conserved_mass,
                    prior_state_receipt_sha256=self._state.receipt_sha256,
                    causal_event_receipt_sha256=(
                        event.authority_receipt_sha256
                    ),
                    receipt_sha256="0" * 64,
                )
                result_state = NeurochemicalFlowState(
                    **{
                        name: getattr(provisional, name)
                        for name in provisional.__dataclass_fields__
                        if name != "receipt_sha256"
                    },
                    receipt_sha256=_digest(provisional.payload()),
                )
                self._verify_state(result_state)
                transition_provisional = NeurochemicalFlowTransition(
                    event=event,
                    prior_state_receipt_sha256=self._state.receipt_sha256,
                    result_state_receipt_sha256=result_state.receipt_sha256,
                    source_time_start=event.source_time_start,
                    source_time_end=event.source_time_end,
                    generator_entries=entries,
                    exact_active_blocks=blocks,
                    untouched_component_ids=untouched,
                    local_target_exposures=self._target_exposures(
                        result_state
                    ),
                    backend_authority_id=self._manifest.backend.authority_id,
                    working_precision_bits=(
                        self._manifest.backend.working_precision_bits
                    ),
                    receipt_sha256="0" * 64,
                )
                transition = NeurochemicalFlowTransition(
                    **{
                        name: getattr(transition_provisional, name)
                        for name in transition_provisional.__dataclass_fields__
                        if name != "receipt_sha256"
                    },
                    receipt_sha256=_digest(
                        transition_provisional.payload()
                    ),
                )
                self._verify_transition(transition, result_state)
                encoded = self._encoded(result_state, transition)
                if len(encoded) > self._manifest.capacity.max_state_bytes:
                    raise ValueError(
                        "neurochemical state capacity is full"
                    )
            except (TypeError, ValueError) as error:
                if self.snapshot_encoded() != prior_snapshot:
                    raise RuntimeError(
                        "unresolved neurochemical evolution mutated state"
                    ) from error
                return NeurochemicalEvolutionResult(
                    status=EvolutionStatus.UNRESOLVED,
                    state=self._state,
                    transition=None,
                    reason=str(error),
                )
            self._state = result_state
            self._last_transition = transition
            return NeurochemicalEvolutionResult(
                status=EvolutionStatus.EVOLVED,
                state=result_state,
                transition=transition,
                reason=(
                    "complete sparse field evolved analytically at causal boundary"
                ),
            )

    def _verify_transition(
        self,
        transition: NeurochemicalFlowTransition,
        state: NeurochemicalFlowState,
    ) -> None:
        if not isinstance(transition, NeurochemicalFlowTransition):
            raise TypeError("neurochemical transition is not typed")
        self._verify_event_shape(transition.event, verify_sequence=False)
        expected_enabled = set(state.enabled_transport_ids)
        expected_entries = self._generator(tuple(sorted(expected_enabled)))
        expected_blocks = self._active_blocks(expected_entries)
        component_ids = {
            value.component_id for value in self._manifest.components
        }
        active_component_ids = {
            component_id
            for block in expected_blocks
            for component_id in block
        }
        transfer_component_ids: set[str] = set()
        for transfer in transition.event.physical_receipts:
            lane = self._impulse_route_by_id[transfer.lane_id]
            transfer_component_ids.add(lane.source_component_id)
            transfer_component_ids.add(lane.target_component_id)
        state_is_exact_zero = (
            state.exact_conserved_mass == 0
            and not transition.event.physical_receipts
            and all(
                _value_bounds(value) == (Fraction(0), Fraction(0))
                for _, value in state.component_values
            )
        )
        expected_untouched = (
            tuple(sorted(component_ids))
            if state_is_exact_zero
            else tuple(sorted(
                component_ids
                - active_component_ids
                - transfer_component_ids
            ))
        )
        state_values = dict(state.component_values)
        accepted_sequences = dict(state.last_accepted_sequence_by_issuer)
        event_last_sequence_by_issuer: dict[str, int] = {}
        for receipt in (
            *transition.event.physical_receipts,
            *transition.event.temporal_receipts,
        ):
            event_last_sequence_by_issuer[receipt.issuer_id] = (
                receipt.chemistry_sequence
            )
        expected_exposures = self._target_exposures(state)
        if (
            transition.result_state_receipt_sha256 != state.receipt_sha256
            or transition.source_time_start
            != transition.event.source_time_start
            or transition.source_time_end
            != transition.event.source_time_end
            or transition.source_time_end != state.source_time
            or transition.generator_entries != expected_entries
            or transition.exact_active_blocks != expected_blocks
            or transition.untouched_component_ids != expected_untouched
            or transition.backend_authority_id
            != self._manifest.backend.authority_id
            or transition.working_precision_bits
            != self._manifest.backend.working_precision_bits
            or transition.local_target_exposures != expected_exposures
            or any(
                accepted_sequences[issuer_id] != sequence
                for issuer_id, sequence
                in event_last_sequence_by_issuer.items()
            )
            or any(
                exposure.component_value
                != state_values[exposure.component_id]
                for exposure in transition.local_target_exposures
            )
            or transition.receipt_sha256 != _digest(transition.payload())
        ):
            raise ValueError("neurochemical transition changed semantics")

    def _cold_payload(
        self,
        state: NeurochemicalFlowState,
        transition: NeurochemicalFlowTransition | None,
    ) -> dict[str, object]:
        return {
            "last_transition": (
                None if transition is None else transition.record()
            ),
            "manifest_receipt_sha256": (
                self._manifest.authority_receipt_sha256
            ),
            "schema": COLD_SCHEMA,
            "state": state.record(),
        }

    def _encoded(
        self,
        state: NeurochemicalFlowState,
        transition: NeurochemicalFlowTransition | None,
    ) -> bytes:
        payload = self._cold_payload(state, transition)
        signature = hmac.new(
            self._cold_key,
            _COLD_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        encoded = _canonical({
            "authority_hmac_sha256": signature,
            "payload": payload,
            "schema": COLD_SCHEMA,
        })
        if len(encoded) > self._manifest.capacity.max_state_bytes:
            raise ValueError("neurochemical state capacity is full")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._state, self._last_transition)

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        manifest: NeurochemicalFlowManifest,
        encoded: bytes,
    ) -> "NeurochemicalFlowFieldAuthority":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("neurochemical cold state is absent")
        if len(encoded) > manifest.capacity.max_state_bytes:
            raise ValueError(
                "neurochemical cold state exceeds authenticated byte capacity"
            )
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("neurochemical cold state is unreadable") from error
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {
                "authority_hmac_sha256",
                "payload",
                "schema",
            }
            or envelope.get("schema") != COLD_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("neurochemical cold envelope changed")
        owner = cls(authority_key=authority_key, manifest=manifest)
        payload = envelope.get("payload")
        if (
            not isinstance(payload, dict)
            or set(payload) != {
                "last_transition",
                "manifest_receipt_sha256",
                "schema",
                "state",
            }
            or payload.get("schema") != COLD_SCHEMA
            or payload.get("manifest_receipt_sha256")
            != manifest.authority_receipt_sha256
        ):
            raise ValueError("neurochemical cold payload changed")
        expected_hmac = hmac.new(
            owner._cold_key,
            _COLD_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if envelope.get("authority_hmac_sha256") != expected_hmac:
            raise ValueError("neurochemical cold authority changed")
        state = owner._state_from_record(payload["state"])
        owner._verify_state(state)
        raw_transition = payload["last_transition"]
        transition = (
            None
            if raw_transition is None
            else owner._transition_from_record(raw_transition)
        )
        if transition is not None:
            owner._verify_transition(transition, state)
            if (
                transition.prior_state_receipt_sha256
                != state.prior_state_receipt_sha256
                or transition.event.authority_receipt_sha256
                != state.causal_event_receipt_sha256
            ):
                raise ValueError(
                    "cold neurochemical transition left state causality"
                )
        elif state.prior_state_receipt_sha256 is not None:
            raise ValueError("cold evolved state lacks its last transition")
        owner._state = state
        owner._last_transition = transition
        if owner.snapshot_encoded() != encoded:
            raise ValueError("neurochemical cold round-trip changed bytes")
        return owner

    def _state_from_record(self, raw: object) -> NeurochemicalFlowState:
        if not isinstance(raw, dict) or set(raw) != {
            "causal_event_receipt_sha256",
            "component_values",
            "constraint",
            "enabled_transport_ids",
            "exact_conserved_mass",
            "last_accepted_sequence_by_issuer",
            "manifest_receipt_sha256",
            "prior_state_receipt_sha256",
            "receipt_sha256",
            "schema",
            "source_time",
        } or raw.get("schema") != STATE_SCHEMA:
            raise ValueError("cold neurochemical state changed shape")
        values = raw.get("component_values")
        if not isinstance(values, list):
            raise ValueError("cold component values changed shape")
        parsed_values = []
        for value in values:
            if not isinstance(value, dict) or set(value) != {
                "component_id",
                "value",
            }:
                raise ValueError("cold component entry changed shape")
            parsed_values.append((
                value["component_id"],
                _value_from_record(value["value"]),
            ))
        raw_sequences = raw.get("last_accepted_sequence_by_issuer")
        if not isinstance(raw_sequences, list):
            raise ValueError("cold upstream sequences changed shape")
        parsed_sequences = []
        for value in raw_sequences:
            if not isinstance(value, dict) or set(value) != {
                "issuer_id",
                "sequence",
            }:
                raise ValueError("cold upstream sequence entry changed shape")
            parsed_sequences.append((value["issuer_id"], value["sequence"]))
        return NeurochemicalFlowState(
            source_time=_fraction_from_text(
                raw["source_time"],
                "cold neurochemical source time",
            ),
            manifest_receipt_sha256=raw["manifest_receipt_sha256"],
            component_values=tuple(parsed_values),
            enabled_transport_ids=tuple(raw["enabled_transport_ids"]),
            last_accepted_sequence_by_issuer=tuple(parsed_sequences),
            exact_conserved_mass=_fraction_from_text(
                raw["exact_conserved_mass"],
                "cold exact conserved mass",
            ),
            prior_state_receipt_sha256=raw["prior_state_receipt_sha256"],
            causal_event_receipt_sha256=(
                raw["causal_event_receipt_sha256"]
            ),
            receipt_sha256=raw["receipt_sha256"],
        )

    def _physical_receipt_from_record(
        self,
        raw: object,
    ) -> PhysicalNeurochemicalReceipt:
        if not isinstance(raw, dict) or set(raw) != {
            "amount",
            "amount_unit",
            "chemistry_sequence",
            "destination_component_id",
            "ed25519_signature_hex",
            "event_id",
            "issuer_id",
            "lane_id",
            "schema",
            "source_component_id",
            "source_kind",
            "source_time_end",
            "source_time_start",
        }:
            raise ValueError("cold physical receipt changed shape")
        return PhysicalNeurochemicalReceipt(
            issuer_id=raw["issuer_id"],
            chemistry_sequence=raw["chemistry_sequence"],
            event_id=raw["event_id"],
            source_time_start=_fraction_from_text(
                raw["source_time_start"],
                "cold physical receipt start",
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"],
                "cold physical receipt end",
            ),
            source_kind=CausalSourceKind(raw["source_kind"]),
            source_component_id=raw["source_component_id"],
            lane_id=raw["lane_id"],
            destination_component_id=raw["destination_component_id"],
            amount=_fraction_from_text(raw["amount"], "cold transfer amount"),
            amount_unit=raw["amount_unit"],
            ed25519_signature_hex=raw["ed25519_signature_hex"],
        )

    def _temporal_receipt_from_record(
        self,
        raw: object,
    ) -> TemporalNeurochemicalReceipt:
        if not isinstance(raw, dict) or set(raw) != {
            "chemistry_sequence",
            "driver_kind",
            "ed25519_signature_hex",
            "event_id",
            "issuer_id",
            "lane_enabled",
            "lane_id",
            "physical_parameter_path",
            "schema",
            "source_time_end",
            "source_time_start",
        }:
            raise ValueError("cold temporal receipt changed shape")
        return TemporalNeurochemicalReceipt(
            issuer_id=raw["issuer_id"],
            chemistry_sequence=raw["chemistry_sequence"],
            event_id=raw["event_id"],
            source_time_start=_fraction_from_text(
                raw["source_time_start"],
                "cold temporal receipt start",
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"],
                "cold temporal receipt end",
            ),
            driver_kind=TemporalDriverKind(raw["driver_kind"]),
            lane_id=raw["lane_id"],
            lane_enabled=raw["lane_enabled"],
            physical_parameter_path=raw["physical_parameter_path"],
            ed25519_signature_hex=raw["ed25519_signature_hex"],
        )

    def _event_from_record(self, raw: object) -> NeurochemicalCausalEvent:
        if not isinstance(raw, dict) or set(raw) != {
            "authority_receipt_sha256",
            "event_id",
            "physical_receipts",
            "schema",
            "source_time_end",
            "source_time_start",
            "temporal_receipts",
        } or raw.get("schema") != EVENT_SCHEMA:
            raise ValueError("cold neurochemical event changed shape")
        return NeurochemicalCausalEvent(
            event_id=raw["event_id"],
            source_time_start=_fraction_from_text(
                raw["source_time_start"],
                "cold event start",
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"],
                "cold event end",
            ),
            physical_receipts=tuple(
                self._physical_receipt_from_record(value)
                for value in raw["physical_receipts"]
            ),
            temporal_receipts=tuple(
                self._temporal_receipt_from_record(value)
                for value in raw["temporal_receipts"]
            ),
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )

    def _transition_from_record(
        self,
        raw: object,
    ) -> NeurochemicalFlowTransition:
        if not isinstance(raw, dict) or set(raw) != {
            "backend",
            "causal_event",
            "conservation",
            "exact_active_blocks",
            "generator_entries",
            "integration",
            "local_target_exposures",
            "prior_state_receipt_sha256",
            "receipt_sha256",
            "result_state_receipt_sha256",
            "schema",
            "source_time_end",
            "source_time_start",
            "untouched_component_ids",
        } or raw.get("schema") != TRANSITION_SCHEMA:
            raise ValueError("cold neurochemical transition changed shape")
        backend = raw["backend"]
        if not isinstance(backend, dict):
            raise ValueError("cold neurochemical backend changed shape")
        return NeurochemicalFlowTransition(
            event=self._event_from_record(raw["causal_event"]),
            prior_state_receipt_sha256=raw["prior_state_receipt_sha256"],
            result_state_receipt_sha256=raw["result_state_receipt_sha256"],
            source_time_start=_fraction_from_text(
                raw["source_time_start"],
                "cold transition start",
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"],
                "cold transition end",
            ),
            generator_entries=tuple(
                SparseGeneratorEntry(
                    row_component_id=value["row_component_id"],
                    column_component_id=value["column_component_id"],
                    value_per_time_unit=_fraction_from_text(
                        value["value_per_time_unit"],
                        "cold generator entry",
                    ),
                )
                for value in raw["generator_entries"]
            ),
            exact_active_blocks=tuple(
                tuple(value) for value in raw["exact_active_blocks"]
            ),
            untouched_component_ids=tuple(raw["untouched_component_ids"]),
            local_target_exposures=tuple(
                LocalTargetExposure(
                    target_id=value["target_id"],
                    component_id=value["component_id"],
                    target_kind=LocalTargetKind(value["target_kind"]),
                    component_value=_value_from_record(
                        value["component_value"]
                    ),
                    receptor_activation_availability=MechanismAvailability(
                        value["receptor_activation_availability"]
                    ),
                    component_state_receipt_sha256=(
                        value["component_state_receipt_sha256"]
                    ),
                )
                for value in raw["local_target_exposures"]
            ),
            backend_authority_id=backend["authority_id"],
            working_precision_bits=backend["working_precision_bits"],
            receipt_sha256=raw["receipt_sha256"],
        )


__all__ = (
    "CausalSourceKind",
    "DirectedLaneKind",
    "EvolutionStatus",
    "ExtracellularDiffusionInterface",
    "FirstOrderNeurochemicalConversion",
    "LocalNeurochemicalTarget",
    "LocalTargetExposure",
    "LocalTargetKind",
    "MechanismAvailability",
    "NeurochemicalBackendMount",
    "NeurochemicalCapacity",
    "NeurochemicalCausalEvent",
    "NeurochemicalCompartmentMount",
    "NeurochemicalEvolutionResult",
    "NeurochemicalFlowFieldAuthority",
    "NeurochemicalFlowManifest",
    "NeurochemicalFlowState",
    "NeurochemicalFlowTransition",
    "NeurochemicalDriftLane",
    "NeurochemicalImpulseRoute",
    "NeurochemicalNodeMount",
    "NeurochemicalSpeciesMount",
    "NodeKind",
    "NonlinearMechanismKind",
    "PhysicalNeurochemicalReceipt",
    "PhysicalQuantityVerifierMount",
    "PhysicalReceiptRoutePermission",
    "QuantityDomain",
    "SparseGeneratorEntry",
    "SignedPhysicalQuantity",
    "TemporalDriverKind",
    "TemporalNeurochemicalReceipt",
    "TemporalReceiptRoutePermission",
    "UpstreamAuthorityKind",
    "UpstreamIssuerVerifierMount",
    "UnavailableNonlinearMechanism",
    "create_neurochemical_flow_manifest",
)
