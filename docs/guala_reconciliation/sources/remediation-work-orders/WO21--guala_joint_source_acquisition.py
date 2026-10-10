"""Exact acquisition packing for the complete functional64 owner.

This module acquires no history and owns no organism state. Every returned
record must be published with the caller's ordinary atomic successor. World
photons remain six-band Fractions; no pupil, RGB or display quantization enters.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import json
import math
import struct
from typing import Any
from .guala_world_sensorium import retinal_carriage
from .substrate.w1_physical_receptors import (
    UPGRADED_RETINAL_SITE_GEOMETRY, retinal_irradiance_field,
)
from .substrate.body_surface_contact import (
    ExactVector3, ReciprocalBodySurfaceContact,
)
from .substrate.embodiment_world import MountedBodySurfaceSite, PreparedBodySurfaceContact


@dataclass(frozen=True, slots=True)
class AcquisitionBounds:
    record_bytes: int
    integer_bytes: int
    events: int

    def __post_init__(self) -> None:
        for value in (self.record_bytes, self.integer_bytes, self.events):
            if type(value) is not int or value <= 0:
                raise ValueError("source acquisition bounds must be explicit positive integers")


class _Writer:
    __slots__ = ("body", "bounds")

    def __init__(self, bounds: AcquisitionBounds):
        self.body = bytearray()
        self.bounds = bounds

    def put(self, value: bytes) -> None:
        if len(self.body) + len(value) > self.bounds.record_bytes:
            raise ValueError("physical source record exceeds admission")
        self.body.extend(value)

    def integer(self, value: int, form: str) -> None:
        if type(value) is not int:
            raise TypeError("physical source integer cannot be coerced")
        self.put(struct.pack(form, value))

    def blob(self, value: bytes) -> None:
        self.integer(len(value), "<Q")
        self.put(value)

    def text(self, value: str) -> None:
        if type(value) is not str or not value:
            raise TypeError("physical identity is absent")
        self.blob(value.encode("utf-8"))

    def natural(self, value: int) -> None:
        if type(value) is not int or value < 0:
            raise TypeError("source magnitude must be an unsigned integer")
        size = max(1, (value.bit_length() + 7) // 8)
        if size > self.bounds.integer_bytes:
            raise ValueError("source exact integer exceeds admission")
        self.blob(value.to_bytes(size, "little"))

    def ratio(self, value: Fraction) -> None:
        if type(value) is not Fraction or value < 0:
            raise TypeError("source ratio must be an actual nonnegative Fraction")
        self.natural(value.numerator)
        self.natural(value.denominator)

    def signed_ratio(self, value: Fraction) -> None:
        if type(value) is not Fraction:
            raise TypeError("physical evidence lost its original Fraction")
        self.put(bytes((int(value < 0),)))
        self.ratio(abs(value))

    def vector(self, value: ExactVector3) -> None:
        if type(value) is not ExactVector3:
            raise TypeError("body surface vector lost its physical type")
        for component in (value.x, value.y, value.z):
            self.signed_ratio(component)


def _double_millidegrees(value: int | Fraction) -> int:
    if type(value) not in (int, Fraction):
        raise TypeError("retinal geometry must remain exact")
    doubled = 2 * Fraction(value)
    if doubled.denominator != 1:
        raise ValueError("actual retinal geometry left the declared half-millidegree lattice")
    return doubled.numerator


def _geometry() -> tuple[tuple[int, int, int, int, int, int, int], ...]:
    if len(UPGRADED_RETINAL_SITE_GEOMETRY) != 19_335:
        raise ValueError("actual world retinal roster changed")
    rows = []
    for index, site in enumerate(UPGRADED_RETINAL_SITE_GEOMETRY):
        identity, h, v, hh, vh = site
        if type(identity) is not int or identity != index:
            raise ValueError("retinal site identity changed")
        h2, v2, hh2, vh2 = map(_double_millidegrees, (h, v, hh, vh))
        column = (8 * (h2 + 180_000)) // 360_000
        row = (10 * (90_000 - v2)) // 180_000
        if not 0 <= column < 8 or not 0 <= row < 10 or hh2 <= 0 or vh2 <= 0:
            raise ValueError("retinal site is outside the fixed receiver geometry")
        rows.append((identity, h2, v2, hh2, vh2, column, row))
    return tuple(rows)

# Fixed declared source anatomy, derived once from the actual mounted geometry.
# No observation, attention choice or learned state enters this receiver map.
_MOUNTED_GEOMETRY = _geometry()


def acquire_world_optical_and_retina(
    physical_state: Any, body_axes: tuple[Any, ...], *, acquired_millisecond: int,
    available_millisecond: int, sun: tuple[float, float, float, int] | None,
    acquisition_provenance: bytes, bounds: AcquisitionBounds,
) -> tuple[bytes, tuple[int, ...]]:
    """One real private-state acquisition, returning both the packed record and retinal projection."""
    if type(acquired_millisecond) is not int or type(available_millisecond) is not int:
        raise TypeError("actual source clocks must be explicit integers")
    if available_millisecond < acquired_millisecond:
        raise ValueError("optical availability cannot precede acquisition")
    if type(acquisition_provenance) is not bytes or not acquisition_provenance:
        raise ValueError("actual optical acquisition provenance is required")
    if bounds.record_bytes < 48 + (116_010 + 480) * 18:
        raise ValueError("physical source record cannot fit its minimum admission")
    heading, pitch, _actual_transmission = retinal_carriage(body_axes)
    pixels = retinal_irradiance_field(
        physical_state, retinal_heading_offset_millidegrees=heading,
        retinal_pitch_offset_millidegrees=pitch, include_focal=True, sun=sun,
    )
    geometry = _MOUNTED_GEOMETRY
    if len(pixels) != len(geometry):
        raise ValueError("world acquisition lost a retinal site")
    identity = _Writer(bounds)
    identity.put(b"GL64OI01")
    identity.integer(acquired_millisecond, "<q")
    identity.integer(heading, "<i")
    identity.integer(pitch, "<i")
    identity.blob(acquisition_provenance)
    if sun is None:
        identity.put(b"\x00")
    else:
        if type(sun) is not tuple or len(sun) != 4:
            raise TypeError("actual sun source must retain its physical tuple")
        identity.put(b"\x01")
        for direction in sun[:3]:
            if type(direction) is not float or not math.isfinite(direction):
                raise TypeError("actual solar direction must be finite binary64")
            identity.put(struct.pack("<d", direction))
        identity.integer(sun[3], "<q")
    # Geometry area is 4*hh*vh == hh2*vh2 exactly. Overlapping fields share
    # the one aperture; observed brightness never sets these coefficients.
    areas = [0] * 80
    weighted = [Fraction(0) for _ in range(480)]
    out = _Writer(bounds)
    out.put(b"GL64OP01")
    out.integer(acquired_millisecond, "<q")
    out.integer(available_millisecond, "<q")
    out.blob(bytes(identity.body))
    out.integer(116_010, "<Q")
    retinal_u8_list: list[int] = []
    for physical, bands in zip(geometry, pixels, strict=True):
        if len(bands) != 6:
            raise ValueError("actual acquisition lost an original optical band")
        _, _, _, hh2, vh2, column, row = physical
        cell = 10 * column + row
        area = hh2 * vh2
        areas[cell] += area
        band_sum = Fraction(0)
        for band, value in enumerate(bands):
            if type(value) is not Fraction or not 0 <= value <= 1:
                raise ValueError("raw world irradiance is outside the admitted source profile")
            out.ratio(value)
            weighted[6 * cell + band] += area * value
            band_sum += value
        brightness = min(255, max(0, round(float(band_sum / 6) * 255)))
        retinal_u8_list.append(brightness)
    out.integer(480, "<Q")
    for port, value in enumerate(weighted):
        area = areas[port // 6]
        # Exact absence of incidence is distinct from a missing observation.
        power = Fraction(0) if area == 0 else 100 * value / area
        if area == 0 and value != 0:
            raise ValueError("disconnected optical receiver acquired fictitious work")
        out.ratio(power)
    return bytes(out.body), tuple(retinal_u8_list)


def acquire_world_optical(
    physical_state: Any, body_axes: tuple[Any, ...], *, acquired_millisecond: int,
    available_millisecond: int, sun: tuple[float, float, float, int] | None,
    acquisition_provenance: bytes, bounds: AcquisitionBounds,
) -> bytes:
    """One real private-state acquisition, using the boundary's own sampled sun."""
    record, _ = acquire_world_optical_and_retina(
        physical_state, body_axes, acquired_millisecond=acquired_millisecond,
        available_millisecond=available_millisecond, sun=sun,
        acquisition_provenance=acquisition_provenance, bounds=bounds,
    )
    return record


def _site_record(site: MountedBodySurfaceSite, bounds: AcquisitionBounds) -> bytes:
    if type(site) is not MountedBodySurfaceSite:
        raise TypeError("source requires the actual mounted surface site")
    site.verify()
    out = _Writer(bounds)
    out.text(site.body_id)
    out.text(site.site_id)
    for vector in (site.local_centre_micrometres, site.outward_normal, site.tangent_u, site.tangent_v):
        out.vector(vector)
    out.ratio(site.half_extent_u_micrometres)
    out.ratio(site.half_extent_v_micrometres)
    for value in (
        site.material.normal_stiffness_millinewtons_per_micrometre_per_square_micrometre,
        site.material.tangential_damping_millinewton_microseconds_per_micrometre_per_square_micrometre,
        site.material.thermal_conductance_nanowatts_per_square_micrometre_millikelvin,
    ):
        out.ratio(value)
    out.integer(site.reference_temperature_millikelvin, "<q")
    if site.cutaneous_topology_index is None:
        out.put(b"\x00")
    else:
        out.put(b"\x01")
        out.integer(site.cutaneous_topology_index, "<Q")
    return bytes(out.body)


def pack_source_geometry(world: Any, self_body_id: str, bounds: AcquisitionBounds) -> tuple[bytes, tuple[MountedBodySurfaceSite, ...]]:
    sites = world.body_surface_sites_for(self_body_id)
    if type(sites) is not tuple or len(sites) > 32:
        raise ValueError("actual source surface roster exceeded its anatomy")
    if any(site.body_id != self_body_id for site in sites):
        raise ValueError("source surface roster has another body")
    if len({site.site_id for site in sites}) != len(sites):
        raise ValueError("duplicate source surface identity")
    out = _Writer(bounds)
    out.put(b"GL64SG01")
    out.integer(19_335, "<Q")
    for identity, h2, v2, hh2, vh2, _column, _row in _MOUNTED_GEOMETRY:
        out.integer(identity, "<Q")
        for value in (h2, v2, hh2, vh2):
            out.integer(value, "<i")
    out.integer(len(sites), "<Q")
    for site in sites:
        out.blob(_site_record(site, bounds))
    return bytes(out.body), sites


@dataclass(frozen=True, slots=True)
class CapturedSurfaceEvent:
    identity: bytes
    start_microsecond: int
    end_microsecond: int
    actor_body_id: str
    contacts: tuple[PreparedBodySurfaceContact, ...]


def capture_surface_event(
    world: Any, prepared: Any, *, identity: bytes, start_microsecond: int,
    end_microsecond: int, actor_body_id: str, bounds: AcquisitionBounds,
) -> CapturedSurfaceEvent:
    """Call once on the authentic prepared event before atomic publication."""
    if type(identity) is not bytes or not identity or len(identity) > bounds.record_bytes:
        raise ValueError("surface event requires its authentic bounded identity")
    if type(start_microsecond) is not int or type(end_microsecond) is not int:
        raise TypeError("surface event needs exact owner clocks")
    if end_microsecond - start_microsecond < 3_000:
        raise ValueError("body-surface command cannot be replayed as a1ms event")
    contacts = world.body_surface_contacts_for_prepared_action(prepared)
    if type(contacts) is not tuple or len(contacts) > 4:
        raise ValueError("surface event exceeded actual command anatomy")
    for contact in contacts:
        if type(contact) is not PreparedBodySurfaceContact or len(contact.physical_phases) != 3:
            raise TypeError("surface event lacks all original physical phases")
        if any(phase.body_a_id != actor_body_id for phase in contact.physical_phases):
            raise ValueError("surface event actor does not match its physical receipt")
        duration = sum((phase.duration_microseconds for phase in contact.physical_phases), Fraction(0))
        if duration != end_microsecond - start_microsecond:
            raise ValueError("surface event phases do not span the actual admitted command")
    return CapturedSurfaceEvent(identity, start_microsecond, end_microsecond, actor_body_id, contacts)


def _phase(out: _Writer, phase: ReciprocalBodySurfaceContact) -> None:
    if type(phase) is not ReciprocalBodySurfaceContact:
        raise TypeError("surface phase is not authentic physical evidence")
    out.text(phase.disposition.value)
    for value in (phase.body_a_id, phase.site_a_id, phase.body_b_id, phase.site_b_id):
        out.text(value)
    for value in (
        phase.duration_microseconds, phase.predecessor_signed_gap_micrometres,
        phase.successor_signed_gap_micrometres, phase.contact_area_square_micrometres,
        phase.predecessor_compression_micrometres, phase.successor_compression_micrometres,
        phase.predecessor_normal_load_millinewtons, phase.successor_normal_load_millinewtons,
        phase.predecessor_normal_elastic_energy_nanojoules, phase.successor_normal_elastic_energy_nanojoules,
        phase.normal_work_into_interface_nanojoules, phase.tangential_relative_displacement_u_micrometres,
        phase.tangential_relative_displacement_v_micrometres,
    ):
        out.signed_ratio(value)
    if type(phase.tangential_slip_occurred) is not bool:
        raise TypeError("surface slip evidence is not Boolean")
    out.put(bytes((int(phase.tangential_slip_occurred),)))
    for value in (
        phase.successor_normal_force_on_a_millinewtons, phase.successor_normal_force_on_b_millinewtons,
        phase.constant_tangential_force_on_a_millinewtons, phase.constant_tangential_force_on_b_millinewtons,
    ):
        out.vector(value)
    for value in (
        phase.tangential_dissipated_work_nanojoules, phase.conductive_heat_to_a_nanojoules,
        phase.conductive_heat_to_b_nanojoules, phase.separating_motion_a_micrometres,
        phase.separating_motion_b_micrometres,
    ):
        out.signed_ratio(value)


def pack_surface_observation(
    *, self_body_id: str, sites: tuple[MountedBodySurfaceSite, ...],
    start_millisecond: int, end_millisecond: int, received_covered: bool,
    own_covered: bool, events: tuple[CapturedSurfaceEvent, ...],
    skin_millikelvin: Fraction, bounds: AcquisitionBounds,
) -> tuple[bytes, bytes, bytes]:
    """Return exact normalized event areas, original full receipts and raw skin."""
    if type(received_covered) is not bool or type(own_covered) is not bool or not (received_covered and own_covered):
        raise ValueError("body-surface-command event coverage is unavailable")
    if type(start_millisecond) is not int or type(end_millisecond) is not int or end_millisecond - start_millisecond != 10:
        raise ValueError("surface source interval must be the actual10ms")
    if type(events) is not tuple or len(events) > bounds.events:
        raise ValueError("surface source event admission")
    index = {site.site_id: i for i, site in enumerate(sites)}
    if len(index) != len(sites) or len(sites) > 32 or any(site.body_id != self_body_id for site in sites):
        raise ValueError("surface source roster changed")
    areas = [Fraction(0) for _ in range(2 * len(sites))]
    seen: set[bytes] = set()
    evidence = _Writer(bounds)
    evidence.put(b"GL64SE01")
    evidence.integer(start_millisecond, "<q")
    evidence.integer(end_millisecond, "<q")
    evidence.text(self_body_id)
    evidence.integer(len(events), "<Q")
    for event in events:
        if type(event) is not CapturedSurfaceEvent or event.identity in seen:
            raise ValueError("surface source repeats an admitted event")
        if not start_millisecond * 1000 < event.end_microsecond <= end_millisecond * 1000:
            raise ValueError("surface event is unavailable in this completion interval")
        seen.add(event.identity)
        evidence.blob(event.identity)
        evidence.integer(event.start_microsecond, "<q")
        evidence.integer(event.end_microsecond, "<q")
        evidence.text(event.actor_body_id)
        evidence.integer(len(event.contacts), "<Q")
        for contact in event.contacts:
            peak = contact.physical
            if event.actor_body_id == self_body_id:
                site_id, lane = peak.site_a_id, 1
            elif peak.body_b_id == self_body_id:
                site_id, lane = peak.site_b_id, 0
            else:
                raise ValueError("surface receipt does not contact the source body")
            if site_id not in index:
                raise ValueError("surface receipt names an unmounted source site")
            areas[2 * index[site_id] + lane] += peak.contact_area_square_micrometres
            evidence.integer(len(contact.physical_phases), "<Q")
            for phase in contact.physical_phases:
                _phase(evidence, phase)
            if contact.recipient_cutaneous_topology_index is None:
                evidence.put(b"\x00")
            else:
                evidence.put(b"\x01")
                evidence.integer(contact.recipient_cutaneous_topology_index, "<Q")
            evidence.ratio(contact.recipient_site_area_square_micrometres)
    ratios = _Writer(bounds)
    for i, site in enumerate(sites):
        site_area = 4 * site.half_extent_u_micrometres * site.half_extent_v_micrometres
        if site_area <= 0:
            raise ValueError("source site has no mounted area")
        ratios.ratio(areas[2 * i] / site_area)
        ratios.ratio(areas[2 * i + 1] / site_area)
    thermal = _Writer(bounds)
    if type(skin_millikelvin) is not Fraction or skin_millikelvin <= 0:
        raise ValueError("actual private-prefix skin temperature unavailable")
    thermal.ratio(skin_millikelvin)
    return bytes(ratios.body), bytes(evidence.body), bytes(thermal.body)


def pack_root_interval(sample: Any, *, source_millisecond: int, bounds: AcquisitionBounds) -> bytes:
    """Pack an ACTUAL compound-world row, never the requested MotorSample."""
    from .substrate.compound_motor_material import MotorSampleConsequence
    if type(sample) is not MotorSampleConsequence:
        raise TypeError("root source requires the actual compound consequence")
    record = sample.as_record()
    out = _Writer(bounds)
    out.put(b"GL64RI01")
    out.integer(source_millisecond, "<q")
    for displacement in sample.root_delta:
        out.integer(displacement, "<q")
    out.blob(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    return bytes(out.body)


def pack_root_window(samples: tuple[Any, ...], *, source_millisecond: int, bounds: AcquisitionBounds) -> bytes:
    if type(samples) is not tuple or len(samples) != 10:
        raise ValueError("root source needs ten actual consecutive1ms consequences")
    out = _Writer(bounds)
    out.put(b"GL64RW01")
    out.integer(source_millisecond + 10, "<q")
    for offset, sample in enumerate(samples):
        out.blob(pack_root_interval(sample, source_millisecond=source_millisecond + offset, bounds=bounds))
    return bytes(out.body)
