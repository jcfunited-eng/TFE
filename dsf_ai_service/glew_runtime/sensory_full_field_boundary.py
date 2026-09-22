"""Lossless six-sense boundary for future sensory-domain L5 interpreters.

This module is deliberately an isolated contract. It does not transduce a
sensor, run the frozen kernel, interpret a sense, associate a source, or mount
L6. Its one job is to prevent those later stages from silently replacing a
native sensory topology with one scalar, one chi address, one ternary code, or
one compatibility vector.

Every observed native substream must arrive with:

* a profile in an independently receipted complete native topology;
* its own unchanged L0--L4 ``PortKernelBasinSignature``;
* the complete ordered sequence of exact seven-field L4 tuple receipts; and
* one common causal-window receipt shared by all six physical senses.

Unavailable and unresolved senses remain explicit boundary states. They are
never fabricated from a word label and never silently omitted. Krimelack, chi,
Atlas, language, sensory L5 interpretation, and L6 are intentionally absent
from this authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from .global_uf import PortKernelBasinSignature
from .model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)


class PhysicalSense(str, Enum):
    SIGHT = "sight"
    SOUND = "sound"
    TOUCH = "touch"
    SMELL = "smell"
    TASTE = "taste"
    BODY = "body"


SENSE_ORDER: tuple[PhysicalSense, ...] = tuple(PhysicalSense)


class SenseBoundaryState(str, Enum):
    OBSERVED = "observed"
    QUIESCENT = "quiescent"
    SENSOR_UNAVAILABLE = "sensor_unavailable"
    UNKNOWN = "unknown"


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "boundary structural time")
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
    field_name: str,
) -> None:
    mounted = registry.resolve(digest, field_name)
    if mounted != expected or receipt_sha256(expected) != digest:
        raise ReceiptError(f"{field_name} differs from mounted authority bytes")


@dataclass(frozen=True, slots=True)
class NativeAxisCoordinate:
    """One provider-declared native coordinate, retained without projection."""

    axis_id: str
    coordinate_id: str

    def __post_init__(self) -> None:
        require_identifier(self.axis_id, "native sensory axis_id")
        require_identifier(self.coordinate_id, "native sensory coordinate_id")


def native_substream_profile_receipt_payload(
    *,
    sense: PhysicalSense,
    sensor_id: str,
    substream_id: str,
    topology_index: int,
    coordinates: tuple[NativeAxisCoordinate, ...],
    physical_quantity: str,
    physical_unit: str,
    physical_derivation_receipt_sha256: str,
) -> bytes:
    if not isinstance(sense, PhysicalSense):
        raise ReceiptError("native substream sense must be typed")
    require_identifier(sensor_id, "native sensory sensor_id")
    require_identifier(substream_id, "native sensory substream_id")
    if isinstance(topology_index, bool) or not isinstance(topology_index, int):
        raise ReceiptError("native sensory topology_index must be an integer")
    if topology_index < 0:
        raise ReceiptError("native sensory topology_index cannot be negative")
    if not isinstance(coordinates, tuple) or not coordinates:
        raise ReceiptError("native sensory coordinates must be nonempty and immutable")
    if not all(isinstance(value, NativeAxisCoordinate) for value in coordinates):
        raise ReceiptError("native sensory coordinates must be typed")
    axis_ids = tuple(value.axis_id for value in coordinates)
    if len(set(axis_ids)) != len(axis_ids):
        raise ReceiptError("native sensory coordinate axes must be unique")
    require_identifier(physical_quantity, "native sensory physical_quantity")
    require_identifier(physical_unit, "native sensory physical_unit")
    sha256_digest(
        physical_derivation_receipt_sha256,
        "native sensory physical derivation receipt",
    )
    return _canonical_bytes(
        {
            "coordinates": [
                {"axis_id": value.axis_id, "coordinate_id": value.coordinate_id}
                for value in coordinates
            ],
            "physical_derivation_receipt_sha256": (
                physical_derivation_receipt_sha256
            ),
            "physical_quantity": physical_quantity,
            "physical_unit": physical_unit,
            "schema": "guala.sensory.native_substream_profile.v1",
            "sense": sense.value,
            "sensor_id": sensor_id,
            "substream_id": substream_id,
            "topology_index": topology_index,
        }
    )


@dataclass(frozen=True, slots=True)
class NativeSubstreamProfile:
    """Receipt-bound identity and topology for one unprojected substream."""

    sense: PhysicalSense
    sensor_id: str
    substream_id: str
    topology_index: int
    coordinates: tuple[NativeAxisCoordinate, ...]
    physical_quantity: str
    physical_unit: str
    physical_derivation_receipt_sha256: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        native_substream_profile_receipt_payload(
            sense=self.sense,
            sensor_id=self.sensor_id,
            substream_id=self.substream_id,
            topology_index=self.topology_index,
            coordinates=self.coordinates,
            physical_quantity=self.physical_quantity,
            physical_unit=self.physical_unit,
            physical_derivation_receipt_sha256=(
                self.physical_derivation_receipt_sha256
            ),
        )
        sha256_digest(
            self.authority_receipt_sha256,
            "native sensory substream profile receipt",
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.physical_derivation_receipt_sha256,
            "native sensory physical derivation receipt",
        )
        expected = native_substream_profile_receipt_payload(
            sense=self.sense,
            sensor_id=self.sensor_id,
            substream_id=self.substream_id,
            topology_index=self.topology_index,
            coordinates=self.coordinates,
            physical_quantity=self.physical_quantity,
            physical_unit=self.physical_unit,
            physical_derivation_receipt_sha256=(
                self.physical_derivation_receipt_sha256
            ),
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "native sensory substream profile receipt",
        )


def native_sense_topology_receipt_payload(
    *,
    topology_id: str,
    sense: PhysicalSense,
    profiles: tuple[NativeSubstreamProfile, ...],
) -> bytes:
    require_identifier(topology_id, "native sensory topology_id")
    if not isinstance(sense, PhysicalSense):
        raise ReceiptError("native sensory topology sense must be typed")
    if not isinstance(profiles, tuple) or not profiles:
        raise ReceiptError("native sensory topology requires immutable profiles")
    if not all(isinstance(value, NativeSubstreamProfile) for value in profiles):
        raise ReceiptError("native sensory topology profiles must be typed")
    if any(value.sense is not sense for value in profiles):
        raise ReceiptError("native sensory topology crosses sense domains")
    if tuple(value.topology_index for value in profiles) != tuple(range(len(profiles))):
        raise ReceiptError("native sensory topology profiles are not complete and ordered")
    keys = tuple((value.sensor_id, value.substream_id) for value in profiles)
    if len(set(keys)) != len(keys):
        raise ReceiptError("native sensory topology repeats a substream")
    substream_ids = tuple(value.substream_id for value in profiles)
    if len(set(substream_ids)) != len(substream_ids):
        raise ReceiptError("native sensory topology substream_id values must be unique")
    return _canonical_bytes(
        {
            "profile_receipt_sha256s": [
                value.authority_receipt_sha256 for value in profiles
            ],
            "schema": "guala.sensory.native_sense_topology.v1",
            "sense": sense.value,
            "topology_id": topology_id,
        }
    )


@dataclass(frozen=True, slots=True)
class NativeSenseTopology:
    """Independent authority for the complete ordered ports of one sense."""

    topology_id: str
    sense: PhysicalSense
    profiles: tuple[NativeSubstreamProfile, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        native_sense_topology_receipt_payload(
            topology_id=self.topology_id,
            sense=self.sense,
            profiles=self.profiles,
        )
        sha256_digest(
            self.authority_receipt_sha256,
            "native sensory topology receipt",
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        for value in self.profiles:
            value.verify(receipt_registry)
        expected = native_sense_topology_receipt_payload(
            topology_id=self.topology_id,
            sense=self.sense,
            profiles=self.profiles,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "native sensory topology receipt",
        )


@dataclass(frozen=True, slots=True)
class SensorySubstreamFullField:
    """One native substream and its unchanged, ordered L0--L4 field."""

    profile: NativeSubstreamProfile
    kernel_basin: PortKernelBasinSignature

    def __post_init__(self) -> None:
        if not isinstance(self.profile, NativeSubstreamProfile):
            raise ReceiptError("sensory substream requires a typed native profile")
        if not isinstance(self.kernel_basin, PortKernelBasinSignature):
            raise ReceiptError("sensory substream requires a full kernel basin")
        if self.kernel_basin.key != (
            self.profile.sense.value,
            self.profile.substream_id,
        ):
            raise ReceiptError(
                "sensory substream kernel basin belongs to another native substream"
            )

    @property
    def l0_l4_trace_receipt_sha256(self) -> str:
        return self.kernel_basin.exact_dsf_field_tuples[
            0
        ].source_l0_l4_trace_receipt_sha256

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        self.profile.verify(receipt_registry)
        self.kernel_basin.verify(
            expected_l0_l4_trace_receipt_sha256=(
                self.l0_l4_trace_receipt_sha256
            ),
            receipt_registry=receipt_registry,
        )


def sensory_full_field_boundary_receipt_payload(
    *,
    boundary_id: str,
    sense: PhysicalSense,
    state: SenseBoundaryState,
    source_time_start: Fraction,
    source_time_end: Fraction,
    causal_window_receipt_sha256: str,
    state_evidence_receipt_sha256: str,
    topology: NativeSenseTopology | None,
    substreams: tuple[SensorySubstreamFullField, ...],
) -> bytes:
    require_identifier(boundary_id, "sensory boundary_id")
    if not isinstance(sense, PhysicalSense):
        raise ReceiptError("sensory boundary sense must be typed")
    if not isinstance(state, SenseBoundaryState):
        raise ReceiptError("sensory boundary state must be typed")
    require_fraction(source_time_start, "sensory boundary source_time_start")
    require_fraction(source_time_end, "sensory boundary source_time_end")
    if source_time_end <= source_time_start:
        raise ReceiptError("sensory boundary requires a positive causal interval")
    sha256_digest(causal_window_receipt_sha256, "causal window receipt")
    sha256_digest(state_evidence_receipt_sha256, "sense state evidence receipt")
    if topology is not None and not isinstance(topology, NativeSenseTopology):
        raise ReceiptError("sensory boundary topology must be typed when present")
    if topology is not None and topology.sense is not sense:
        raise ReceiptError("sensory boundary topology belongs to another sense")
    if not isinstance(substreams, tuple):
        raise ReceiptError("sensory boundary substreams must be immutable")
    if not all(isinstance(value, SensorySubstreamFullField) for value in substreams):
        raise ReceiptError("sensory boundary substreams must be typed")
    if state is SenseBoundaryState.OBSERVED:
        if topology is None:
            raise ReceiptError("an observed sense requires an authoritative topology")
        if not substreams:
            raise ReceiptError("an observed sense requires native full-field substreams")
        profiles = tuple(value.profile for value in substreams)
        if profiles != topology.profiles:
            raise ReceiptError("observed substreams do not exactly cover native topology")
    elif substreams:
        raise ReceiptError("an unavailable or unknown sense cannot carry observations")
    return _canonical_bytes(
        {
            "boundary_id": boundary_id,
            "causal_window_receipt_sha256": causal_window_receipt_sha256,
            "native_topology_receipt_sha256": (
                topology.authority_receipt_sha256 if topology is not None else None
            ),
            "schema": "guala.sensory.full_field_boundary.v2",
            "sense": sense.value,
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "state": state.value,
            "state_evidence_receipt_sha256": state_evidence_receipt_sha256,
            "substreams": [
                {
                    "exact_l4_tuple_receipt_sha256s": [
                        item.authority_receipt_sha256
                        for item in value.kernel_basin.exact_dsf_field_tuples
                    ],
                    "kernel_basin_receipt_sha256": (
                        value.kernel_basin.authority_receipt_sha256
                    ),
                    "l0_l4_trace_receipt_sha256": (
                        value.l0_l4_trace_receipt_sha256
                    ),
                    "profile_receipt_sha256": value.profile.authority_receipt_sha256,
                    "substream_id": value.profile.substream_id,
                    "topology_index": value.profile.topology_index,
                }
                for value in substreams
            ],
        }
    )


@dataclass(frozen=True, slots=True)
class SensoryFullFieldBoundary:
    """Complete L4 input boundary for exactly one physical sense."""

    boundary_id: str
    sense: PhysicalSense
    state: SenseBoundaryState
    source_time_start: Fraction
    source_time_end: Fraction
    causal_window_receipt_sha256: str
    state_evidence_receipt_sha256: str
    topology: NativeSenseTopology | None
    substreams: tuple[SensorySubstreamFullField, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        sensory_full_field_boundary_receipt_payload(
            boundary_id=self.boundary_id,
            sense=self.sense,
            state=self.state,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            causal_window_receipt_sha256=self.causal_window_receipt_sha256,
            state_evidence_receipt_sha256=self.state_evidence_receipt_sha256,
            topology=self.topology,
            substreams=self.substreams,
        )
        sha256_digest(self.authority_receipt_sha256, "sensory boundary receipt")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.causal_window_receipt_sha256,
            "sensory boundary causal-window receipt",
        )
        receipt_registry.resolve(
            self.state_evidence_receipt_sha256,
            "sensory boundary state evidence receipt",
        )
        if self.topology is not None:
            self.topology.verify(receipt_registry)
        for value in self.substreams:
            value.verify(receipt_registry)
        expected = sensory_full_field_boundary_receipt_payload(
            boundary_id=self.boundary_id,
            sense=self.sense,
            state=self.state,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            causal_window_receipt_sha256=self.causal_window_receipt_sha256,
            state_evidence_receipt_sha256=self.state_evidence_receipt_sha256,
            topology=self.topology,
            substreams=self.substreams,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "sensory full-field boundary receipt",
        )


def six_sense_full_field_boundary_receipt_payload(
    *,
    assembly_id: str,
    boundaries: tuple[SensoryFullFieldBoundary, ...],
) -> bytes:
    require_identifier(assembly_id, "six-sense assembly_id")
    if not isinstance(boundaries, tuple) or not all(
        isinstance(value, SensoryFullFieldBoundary) for value in boundaries
    ):
        raise ReceiptError("six-sense boundaries must be typed and immutable")
    if tuple(value.sense for value in boundaries) != SENSE_ORDER:
        raise ReceiptError("six-sense assembly must cover all senses in canonical order")
    window_receipts = {value.causal_window_receipt_sha256 for value in boundaries}
    intervals = {
        (value.source_time_start, value.source_time_end) for value in boundaries
    }
    if len(window_receipts) != 1 or len(intervals) != 1:
        raise ReceiptError("six sensory boundaries do not share one causal window")
    return _canonical_bytes(
        {
            "assembly_id": assembly_id,
            "boundary_receipt_sha256s": [
                value.authority_receipt_sha256 for value in boundaries
            ],
            "causal_window_receipt_sha256": boundaries[
                0
            ].causal_window_receipt_sha256,
            "schema": "guala.sensory.six_sense_full_field_boundary.v1",
            "senses": [value.sense.value for value in boundaries],
            "source_time_end": _fraction_text(boundaries[0].source_time_end),
            "source_time_start": _fraction_text(boundaries[0].source_time_start),
        }
    )


@dataclass(frozen=True, slots=True)
class SixSenseFullFieldBoundary:
    """One causal interval covering six explicit physical-sense boundaries."""

    assembly_id: str
    boundaries: tuple[SensoryFullFieldBoundary, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        six_sense_full_field_boundary_receipt_payload(
            assembly_id=self.assembly_id,
            boundaries=self.boundaries,
        )
        sha256_digest(
            self.authority_receipt_sha256,
            "six-sense full-field assembly receipt",
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        for value in self.boundaries:
            value.verify(receipt_registry)
        expected = six_sense_full_field_boundary_receipt_payload(
            assembly_id=self.assembly_id,
            boundaries=self.boundaries,
        )
        _mounted_exact(
            receipt_registry,
            self.authority_receipt_sha256,
            expected,
            "six-sense full-field assembly receipt",
        )


__all__ = (
    "NativeAxisCoordinate",
    "NativeSenseTopology",
    "NativeSubstreamProfile",
    "PhysicalSense",
    "SENSE_ORDER",
    "SenseBoundaryState",
    "SensoryFullFieldBoundary",
    "SensorySubstreamFullField",
    "SixSenseFullFieldBoundary",
    "native_sense_topology_receipt_payload",
    "native_substream_profile_receipt_payload",
    "sensory_full_field_boundary_receipt_payload",
    "six_sense_full_field_boundary_receipt_payload",
)
