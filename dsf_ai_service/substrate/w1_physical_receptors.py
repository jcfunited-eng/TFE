"""Authenticated bounded physical receptors for the W1 embodiment.

The world authority contains privileged control topology because it must execute
commands.  This module is the sensory firewall: topology names, object ids,
body ids, room coordinates, and command kinds never become receptor values or
receptor coordinates.

Sight is a fixed retinotopic photon field.  Heading and a finite field of view
determine which physical surfaces reach each receptor; the nearest surface in
one receptor aperture occludes farther surfaces.  Body sensation exists only
for an authenticated before/after execution and contains egocentric
displacement.  Touch contains only contact and load geometry from the signed
palmar contact or reciprocal hold relation.  The resulting native signals
enter the existing unchanged L0--L4 full-field builder.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction
import math

import numpy as np
from math import isqrt
from typing import Mapping

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    BuiltSixSenseFullField,
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
    declare_joint_source_occurrences,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.embodiment_world import (
    EXECUTION_DOMAIN,
    OBSERVATION_DOMAIN,
    ActionExecutionReceipt,
    EmbodiedBody,
    ObjectOpticalSurface,
    ObservationSnapshot,
    PhysicalPortal,
    PhysicalRegion,
    PositionMM,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.exact_lattice_rotation import (
    rotate_lattice_offset,
)


OUTCOME_OBSERVATION_SCHEMA = "guala.embodiment.physical_receptor_observation.v1"
OUTCOME_OBSERVATION_DOMAIN = b"guala-embodiment-physical-receptor-v1\0"
TRANSDUCER_PROFILE = "guala.embodiment.w1_physical_receptors.v1"

RETINA_ROWS = 3
RETINA_COLUMNS = 9
RETINA_HORIZONTAL_FOV_MILLIDEGREES = 180_000
RETINA_VERTICAL_FOV_MILLIDEGREES = 90_000
OPTICAL_BANDS = 6
RETINAL_REFERENCE_IRRADIANCE_UNIT = (
    "fraction-of-declared-retinal-reference-irradiance"
)
RETINA_RECEPTOR_COUNT = RETINA_ROWS * RETINA_COLUMNS
RETINA_FINE_ROWS = 6
RETINA_FINE_COLUMNS = 18
RETINA_FINE_RECEPTOR_COUNT = RETINA_FINE_ROWS * RETINA_FINE_COLUMNS
RETINA_TOTAL_RECEPTOR_COUNT = RETINA_RECEPTOR_COUNT + RETINA_FINE_RECEPTOR_COUNT
RETINA_FOCAL_ROWS = 60
RETINA_FOCAL_COLUMNS = 80
# Two samples per one-arcminute critical detail: acquisition calibration,
# not a claim of recognition, camera resolution or end-to-end acuity.
# The focal field spans 60 x 45 degrees across its 80 x 60 sites (750
# millidegrees per site), the same field as the whole camera frame held
# still; the earlier half-arc-minute pitch made a quarter-degree cone that saw
# a 9 mm patch of wall, and the 20-degree cone at head height saw only wall
# above the floor where every object lies (Joe, 2026-09-14).
RETINA_FOCAL_PITCH_MILLIDEGREES = Fraction(750)
RETINA_FOCAL_HORIZONTAL_FOV_MILLIDEGREES = RETINA_FOCAL_COLUMNS * RETINA_FOCAL_PITCH_MILLIDEGREES
RETINA_FOCAL_VERTICAL_FOV_MILLIDEGREES = RETINA_FOCAL_ROWS * RETINA_FOCAL_PITCH_MILLIDEGREES
RETINA_FOCAL_RECEPTOR_COUNT = RETINA_FOCAL_ROWS * RETINA_FOCAL_COLUMNS
RETINA_UPGRADED_RECEPTOR_COUNT = RETINA_TOTAL_RECEPTOR_COUNT + RETINA_FOCAL_RECEPTOR_COUNT
RETINA_SUBSTREAM_COUNT = RETINA_TOTAL_RECEPTOR_COUNT * OPTICAL_BANDS
BODY_RECEPTOR_COUNT = 4
TOUCH_RECEPTOR_COUNT = 3
MAX_AUTHORITY_KEY_BYTES = 4096
MAX_WORLD_REVISION = (1 << 63) - 1
MAX_WORLD_REGIONS = 4
MAX_WORLD_PORTALS = 6
MAX_WORLD_BODIES = 4
MAX_WORLD_OBJECTS = 64

# Integer CORDIC receptor calibration.  These are arctan(2**-i) expressed at
# the world's existing one-millidegree angular resolution.  They are sensor
# geometry, not learned categories or decision thresholds.
_CORDIC_ANGLE_MILLIDEGREES = (
    45_000,
    26_565,
    14_036,
    7_125,
    3_576,
    1_790,
    895,
    448,
    224,
    112,
    56,
    28,
    14,
    7,
    3,
    2,
    1,
)
_CORDIC_SCALE_BITS = 24


def _retinal_site_geometry() -> tuple[tuple[int, int, int, int, int], ...]:
    """Return legacy sites unchanged, followed by the finer overlapping field."""

    sites: list[tuple[int, int, int, int, int]] = []
    for rows, columns in (
        (RETINA_ROWS, RETINA_COLUMNS),
        (RETINA_FINE_ROWS, RETINA_FINE_COLUMNS),
    ):
        horizontal_half = RETINA_HORIZONTAL_FOV_MILLIDEGREES // (2 * columns)
        vertical_half = RETINA_VERTICAL_FOV_MILLIDEGREES // (2 * rows)
        for row in range(rows):
            vertical_center = (
                RETINA_VERTICAL_FOV_MILLIDEGREES // 2
                - row * (RETINA_VERTICAL_FOV_MILLIDEGREES // rows)
                - vertical_half
            )
            for column in range(columns):
                horizontal_center = (
                    -(RETINA_HORIZONTAL_FOV_MILLIDEGREES // 2)
                    + column * (RETINA_HORIZONTAL_FOV_MILLIDEGREES // columns)
                    + horizontal_half
                )
                sites.append((
                    len(sites),
                    horizontal_center,
                    vertical_center,
                    horizontal_half,
                    vertical_half,
                ))
    return tuple(sites)


RETINAL_SITE_GEOMETRY = _retinal_site_geometry()
# Preserve all legacy apertures; only the added field samples a narrow center.
# Exact rational half-apertures tile without gaps or angular rounding.
FOCAL_RETINAL_SITE_GEOMETRY = tuple(
    (
        RETINA_TOTAL_RECEPTOR_COUNT + row * RETINA_FOCAL_COLUMNS + column,
        -RETINA_FOCAL_HORIZONTAL_FOV_MILLIDEGREES / 2
        + (2 * column + 1) * RETINA_FOCAL_PITCH_MILLIDEGREES / 2,
        RETINA_FOCAL_VERTICAL_FOV_MILLIDEGREES / 2
        - (2 * row + 1) * RETINA_FOCAL_PITCH_MILLIDEGREES / 2,
        RETINA_FOCAL_PITCH_MILLIDEGREES / 2,
        RETINA_FOCAL_PITCH_MILLIDEGREES / 2,
    )
    for row in range(RETINA_FOCAL_ROWS)
    for column in range(RETINA_FOCAL_COLUMNS)
)
UPGRADED_RETINAL_SITE_GEOMETRY = RETINAL_SITE_GEOMETRY + FOCAL_RETINAL_SITE_GEOMETRY
RetinalSiteGeometry = tuple[tuple[int, int | Fraction, int | Fraction, int | Fraction, int | Fraction], ...]


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


def _sign(key: bytes, domain: bytes, value: object) -> str:
    return hmac.new(key, domain + _canonical(value), hashlib.sha256).hexdigest()


def _authority_key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, bytes):
        result = value
    else:
        raise ValueError("physical receptor authority key must be bytes or text")
    if not result or len(result) > MAX_AUTHORITY_KEY_BYTES:
        raise ValueError("physical receptor authority key must be bounded and nonempty")
    return result


def _sha256_identity(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _position_distance_squared(left: PositionMM, right: PositionMM) -> int:
    return (
        (left.x - right.x) ** 2
        + (left.y - right.y) ** 2
        + (left.z - right.z) ** 2
    )


def _region_for(
    regions: tuple[PhysicalRegion, ...],
    position: PositionMM,
    radius_mm: int,
) -> PhysicalRegion | None:
    containing = tuple(
        region
        for region in regions
        if (
            (
                region.bounds.contains_floor_disc(
                    position,
                    radius_mm,
                )
            )
            if radius_mm > 0
            else (
                region.bounds.minimum.x
                <= position.x
                <= region.bounds.maximum.x
                and region.bounds.minimum.y
                <= position.y
                <= region.bounds.maximum.y
                and region.bounds.minimum.z
                <= position.z
                <= region.bounds.maximum.z
            )
        )
    )
    return containing[0] if len(containing) == 1 else None


def _portal_between(
    portals: tuple[PhysicalPortal, ...],
    left_region_id: str,
    right_region_id: str,
) -> PhysicalPortal | None:
    pair = tuple(sorted((left_region_id, right_region_id)))
    return next((portal for portal in portals if portal.region_ids == pair), None)


def _portal_line_of_sight(
    start: PositionMM,
    finish: PositionMM,
    portal: PhysicalPortal,
) -> bool:
    if portal.axis == "x":
        start_axis, finish_axis = start.x, finish.x
        start_aperture, finish_aperture = start.y, finish.y
    else:
        start_axis, finish_axis = start.y, finish.y
        start_aperture, finish_aperture = start.x, finish.x
    delta_axis = finish_axis - start_axis
    if delta_axis == 0:
        return False
    plane_offset = portal.plane_mm - start_axis
    if not (
        0 <= plane_offset <= delta_axis
        if delta_axis > 0
        else delta_axis <= plane_offset <= 0
    ):
        return False
    aperture_numerator = (
        start_aperture * delta_axis
        + (finish_aperture - start_aperture) * plane_offset
    )
    height_numerator = start.z * delta_axis + (finish.z - start.z) * plane_offset
    if delta_axis < 0:
        delta_axis = -delta_axis
        aperture_numerator = -aperture_numerator
        height_numerator = -height_numerator
    return (
        portal.aperture_min_mm * delta_axis
        <= aperture_numerator
        <= portal.aperture_max_mm * delta_axis
        and 0 <= height_numerator <= portal.height_mm * delta_axis
    )


def _is_visible(
    observation: ObservationSnapshot,
    observer_position: PositionMM,
    target_position: PositionMM,
    target_radius_mm: int,
) -> bool:
    """Physical region/portal visibility, without identity or sensory values."""

    observer_region = _region_for(observation.regions, observer_position, 0)
    target_region = _region_for(
        observation.regions, target_position, target_radius_mm
    )
    if observer_region is None or target_region is None:
        return False
    if observer_region.region_id == target_region.region_id:
        return True
    portal = _portal_between(
        observation.portals,
        observer_region.region_id,
        target_region.region_id,
    )
    return (
        portal is not None
        and _portal_line_of_sight(observer_position, target_position, portal)
    )


def _verify_observation(key: bytes, observation: ObservationSnapshot) -> None:
    if not isinstance(observation, ObservationSnapshot):
        raise ValueError("physical receptor input must be an observation snapshot")
    if (
        isinstance(observation.revision, bool)
        or not isinstance(observation.revision, int)
        or not 0 <= observation.revision <= MAX_WORLD_REVISION
    ):
        raise ValueError("world observation revision is invalid")
    if not (
        3 <= len(observation.regions) <= MAX_WORLD_REGIONS
        and 2 <= len(observation.portals) <= MAX_WORLD_PORTALS
        and 2 <= len(observation.bodies) <= MAX_WORLD_BODIES
        and 1 <= len(observation.objects) <= MAX_WORLD_OBJECTS
    ):
        raise ValueError("world observation exceeds the physical receptor boundary")
    for region in observation.regions:
        region.verify()
    for portal in observation.portals:
        portal.verify()
    for body in observation.bodies:
        body.verify()
    for item in observation.objects:
        item.verify()
    state_record = {
        "bodies": [item.as_record() for item in observation.bodies],
        "objects": [item.as_record() for item in observation.objects],
        "portals": [item.as_record() for item in observation.portals],
        "regions": [item.as_record() for item in observation.regions],
        "revision": observation.revision,
        "room_bounds": observation.room_bounds.as_record(),
        "room_id": observation.room_id,
        "self_body_id": observation.self_body_id,
    }
    if _digest(state_record) != observation.state_sha256:
        raise ValueError("world observation state identity changed")
    unsigned = observation.unsigned_record()
    expected_hmac = _sign(key, OBSERVATION_DOMAIN, unsigned)
    if not hmac.compare_digest(expected_hmac, observation.authority_hmac_sha256):
        raise ValueError("world observation HMAC changed")
    expected_receipt = _digest(
        {"authority_hmac_sha256": expected_hmac, "payload": unsigned}
    )
    if expected_receipt != observation.authority_receipt_sha256:
        raise ValueError("world observation receipt identity changed")


def _verify_execution(
    key: bytes,
    receipt: ActionExecutionReceipt,
    observation: ObservationSnapshot,
) -> None:
    if not isinstance(receipt, ActionExecutionReceipt):
        raise ValueError("physical action outcome requires a typed execution receipt")
    _verify_observation(key, receipt.before)
    _verify_observation(key, receipt.after)
    if receipt.after != observation:
        raise ValueError("execution receipt does not end at the supplied observation")
    if receipt.disposition != "applied" or receipt.reason != "applied":
        raise ValueError("physical action outcome requires an applied execution")
    if receipt.lifecycle[-2:] not in {
        ("geometry_validated", "applied"),
        ("material_contact_geometry_validated", "applied"),
        ("physical_time_transport_validated", "applied"),
        ("vocal_commitment_validated", "applied"),
    }:
        raise ValueError("execution receipt lifecycle changed")
    if (
        receipt.expected_revision != receipt.before.revision
        or receipt.observed_revision != receipt.before.revision
        or receipt.after.revision != receipt.before.revision + 1
    ):
        raise ValueError("execution receipt revision chain changed")
    _sha256_identity(receipt.causal_intent_receipt_sha256, "causal intent receipt")
    _sha256_identity(receipt.command_sha256, "embodiment command identity")
    unsigned = receipt.unsigned_record()
    expected_hmac = _sign(key, EXECUTION_DOMAIN, unsigned)
    if not hmac.compare_digest(expected_hmac, receipt.authority_hmac_sha256):
        raise ValueError("execution receipt HMAC changed")
    expected_receipt = _digest(
        {"authority_hmac_sha256": expected_hmac, "payload": unsigned}
    )
    if expected_receipt != receipt.authority_receipt_sha256:
        raise ValueError("execution receipt identity changed")


def _bounded_fraction(value: Fraction, name: str) -> Fraction:
    den = value._denominator
    if not -den <= value._numerator <= den:
        raise ValueError(f"{name} left the physical receptor boundary")
    return value


def _native_signal(
    *,
    sense: PhysicalSense,
    sensor_id: str,
    substream_id: str,
    topology_index: int,
    coordinates: tuple[NativeAxisCoordinate, ...],
    physical_quantity: str,
    values: tuple[Fraction, ...],
    physical_unit: str = "dimensionless",
    source_time_start: Fraction = Fraction(0),
    source_time_end: Fraction = Fraction(1),
) -> NativeSensorySubstreamInput:
    if not values:
        raise ValueError("physical receptor signal cannot be empty")
    for value in values:
        _bounded_fraction(value, "physical receptor signal")
    count = len(values)
    interval = source_time_end - source_time_start
    if interval <= 0:
        raise ValueError("physical receptor interval must be positive")
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=sensor_id,
        substream_id=substream_id,
        topology_index=topology_index,
        coordinates=coordinates,
        physical_quantity=physical_quantity,
        physical_unit=physical_unit,
        source_times=tuple(
            source_time_start
            + interval * Fraction(index + 1, count + 1)
            for index in range(count)
        ),
        normalized_signal=tuple(float(value) for value in values),
        phase_turns=tuple(Fraction(index, count) for index in range(count)),
    )


def _self_body(observation: ObservationSnapshot) -> EmbodiedBody:
    matches = tuple(
        body for body in observation.bodies
        if body.body_id == observation.self_body_id
    )
    if len(matches) != 1:
        raise ValueError("world observation self-body topology changed")
    return matches[0]


def _body_fixed_receptor_position(
    body: EmbodiedBody,
    offset: PositionMM,
) -> PositionMM:
    dx, dy = rotate_lattice_offset(
        offset.x,
        offset.y,
        body.pose.heading_millidegrees,
    )
    return PositionMM(
        body.pose.position.x + dx,
        body.pose.position.y + dy,
        body.pose.position.z + offset.z,
    )


def _wrap_heading_delta(after: int, before: int) -> int:
    delta = (after - before) % 360_000
    return delta - 360_000 if delta > 180_000 else delta


def _atan2_millidegrees(y: int, x: int) -> int:
    """Quantize one physical vector to W1's native millidegree resolution."""

    if x == 0 and y == 0:
        raise ValueError("zero vector has no physical bearing")
    if x == 0:
        return 90_000 if y > 0 else -90_000
    angle = 0
    scaled_x = x << _CORDIC_SCALE_BITS
    scaled_y = y << _CORDIC_SCALE_BITS
    if scaled_x < 0:
        original_y = scaled_y
        scaled_x = -scaled_x
        scaled_y = -scaled_y
        angle = 180_000 if original_y >= 0 else -180_000
    for shift, increment in enumerate(_CORDIC_ANGLE_MILLIDEGREES):
        if scaled_y > 0:
            next_x = scaled_x + (scaled_y >> shift)
            scaled_y = scaled_y - (scaled_x >> shift)
            scaled_x = next_x
            angle += increment
        elif scaled_y < 0:
            next_x = scaled_x - (scaled_y >> shift)
            scaled_y = scaled_y + (scaled_x >> shift)
            scaled_x = next_x
            angle -= increment
        else:
            break
    if angle > 180_000:
        angle -= 360_000
    if angle <= -180_000:
        angle += 360_000
    return angle


@dataclass(frozen=True, slots=True)
class _OpticalSurface:
    position: PositionMM
    radius_mm: int
    reflectance_ppm: tuple[int, ...]
    optical_surface: ObjectOpticalSurface | None = None
    # Light the surface gives off by itself (the emitter law): added to
    # the reflected term, so a glow star or a working screen stays
    # visible when the room's light fades while ordinary matter goes
    # dark with it.
    emission_ppm: tuple[int, ...] = ()
    source_id: str | None = None


def _region_radiance(region: PhysicalRegion) -> tuple[Fraction, ...]:
    return tuple(
        Fraction(reflectance * illumination, 1_000_000_000_000)
        for reflectance, illumination in zip(
            region.reflectance_ppm,
            region.illumination_ppm,
            strict=True,
        )
    )


def _portal_aperture_background(
    observation: ObservationSnapshot,
    *,
    eye: PositionMM,
    body_heading_millidegrees: int,
    retinal_pitch_offset_millidegrees: int,
    current_region: PhysicalRegion,
    pixels: list[tuple[Fraction, ...]],
    site_geometry: RetinalSiteGeometry,
) -> None:
    """Expose adjacent-room radiance only through authored doorway geometry."""

    regions = {region.region_id: region for region in observation.regions}
    focal_count = len(site_geometry) - RETINA_TOTAL_RECEPTOR_COUNT
    has_focal = focal_count > 0
    ambient_sites = site_geometry[:RETINA_TOTAL_RECEPTOR_COUNT]

    pitch = int(RETINA_FOCAL_PITCH_MILLIDEGREES)
    half_pitch = pitch // 2
    cell_area = 4 * half_pitch * half_pitch
    focal_left = -int(RETINA_FOCAL_HORIZONTAL_FOV_MILLIDEGREES) // 2
    focal_top = int(RETINA_FOCAL_VERTICAL_FOV_MILLIDEGREES) // 2

    for portal in observation.portals:
        if current_region.region_id not in portal.region_ids:
            continue
        neighbour_id = next(
            region_id
            for region_id in portal.region_ids
            if region_id != current_region.region_id
        )
        neighbour = regions.get(neighbour_id)
        if neighbour is None:
            raise RuntimeError("physical portal references an absent region")
        if portal.axis == "x":
            endpoints = (
                (portal.plane_mm - eye.x, portal.aperture_min_mm - eye.y),
                (portal.plane_mm - eye.x, portal.aperture_max_mm - eye.y),
            )
            centre_dx = portal.plane_mm - eye.x
            centre_dy = (
                portal.aperture_min_mm + portal.aperture_max_mm
            ) // 2 - eye.y
        else:
            endpoints = (
                (portal.aperture_min_mm - eye.x, portal.plane_mm - eye.y),
                (portal.aperture_max_mm - eye.x, portal.plane_mm - eye.y),
            )
            centre_dx = (
                portal.aperture_min_mm + portal.aperture_max_mm
            ) // 2 - eye.x
            centre_dy = portal.plane_mm - eye.y
        if centre_dx == 0 and centre_dy == 0:
            continue
        horizontal_edges = tuple(
            _wrap_heading_delta(
                _atan2_millidegrees(dy, dx),
                body_heading_millidegrees,
            )
            for dx, dy in endpoints
        )
        horizontal_min = min(horizontal_edges)
        horizontal_max = max(horizontal_edges)
        if horizontal_max - horizontal_min > 180_000:
            continue
        planar_distance = max(
            isqrt(centre_dx * centre_dx + centre_dy * centre_dy),
            1,
        )
        vertical_min = _atan2_millidegrees(-eye.z, planar_distance) - retinal_pitch_offset_millidegrees
        vertical_max = _atan2_millidegrees(
            portal.height_mm - eye.z,
            planar_distance,
        ) - retinal_pitch_offset_millidegrees
        radiance = _region_radiance(neighbour)

        # Ambient apertures (135 sites)
        for (
            site_index,
            horizontal_center,
            vertical_center,
            horizontal_half,
            vertical_half,
        ) in ambient_sites:
            horizontal_overlap = max(
                0,
                min(horizontal_center + horizontal_half, horizontal_max)
                - max(horizontal_center - horizontal_half, horizontal_min),
            )
            vertical_overlap = max(
                0,
                min(vertical_center + vertical_half, vertical_max)
                - max(vertical_center - vertical_half, vertical_min),
            )
            if not horizontal_overlap or not vertical_overlap:
                continue
            coverage = Fraction(
                horizontal_overlap * vertical_overlap,
                4 * horizontal_half * vertical_half,
            )
            pixels[site_index] = tuple(
                prior * (1 - coverage) + observed * coverage
                for prior, observed in zip(
                    pixels[site_index], radiance, strict=True
                )
            )

        # Accelerated focal grid projection
        if has_focal:
            col_min = max(0, (horizontal_min - focal_left) // pitch)
            col_max = min(RETINA_FOCAL_COLUMNS - 1, (horizontal_max - focal_left) // pitch)
            row_min = max(0, (focal_top - vertical_max) // pitch)
            row_max = min(RETINA_FOCAL_ROWS - 1, (focal_top - vertical_min) // pitch)
            if col_min <= col_max and row_min <= row_max:
                for r in range(row_min, row_max + 1):
                    v_center = focal_top - (2 * r + 1) * half_pitch
                    v_overlap = max(
                        0,
                        min(v_center + half_pitch, vertical_max)
                        - max(v_center - half_pitch, vertical_min),
                    )
                    if not v_overlap:
                        continue
                    row_offset = RETINA_TOTAL_RECEPTOR_COUNT + r * RETINA_FOCAL_COLUMNS
                    for c in range(col_min, col_max + 1):
                        h_center = focal_left + (2 * c + 1) * half_pitch
                        h_overlap = max(
                            0,
                            min(h_center + half_pitch, horizontal_max)
                            - max(h_center - half_pitch, horizontal_min),
                        )
                        if not h_overlap:
                            continue
                        s_idx = row_offset + c
                        if h_overlap * v_overlap == cell_area:
                            pixels[s_idx] = radiance
                        else:
                            cov = Fraction(h_overlap * v_overlap, cell_area)
                            pixels[s_idx] = tuple(
                                prior * (1 - cov) + observed * cov
                                for prior, observed in zip(
                                    pixels[s_idx], radiance, strict=True
                                )
                            )


@dataclass(frozen=True, slots=True)
class _Light:
    """One source of direct light in a room: the sun (a direction toward it, and the
    sky's light) or a thing that emits (a lamp, a working screen: its centre, its radius
    and what it gives off per band)."""

    kind: str
    x: float
    y: float
    z: float
    radius_mm: int
    ppm: tuple[int, ...]
    source_id: str | None


def _room_lights(
    observation: ObservationSnapshot,
    current_region: PhysicalRegion,
    sun: tuple[float, float, float, int] | None,
) -> tuple[list[_Light], list[tuple[float, float, float, float, str | None]]]:
    """The room's lights and the bodies in it that can stand in their way."""

    bands = len(current_region.reflectance_ppm)
    lights: list[_Light] = []
    if sun is not None and sun[2] > 0.0 and current_region.windows:
        lights.append(_Light("sun", sun[0], sun[1], sun[2], 0, (sun[3],) * bands, None))
    occluders: list[tuple[float, float, float, float, str | None]] = []
    for item in observation.objects:
        if item.position is None or not current_region.bounds.contains_floor_disc(item.position, 0):
            continue
        occluders.append((item.position.x, item.position.y, item.position.z + item.radius_mm, item.radius_mm, item.object_id))
        emission = getattr(item, "emission_ppm", ()) or ()
        if len(emission) == bands and any(emission):
            lights.append(_Light("lamp", item.position.x, item.position.y, item.position.z + item.radius_mm, item.radius_mm, tuple(emission), item.object_id))
    for other in observation.bodies:
        occluders.append((other.pose.position.x, other.pose.position.y, other.pose.position.z + other.radius_mm, other.radius_mm, other.body_id))
    return lights, occluders


def _through_window(
    current_region: PhysicalRegion, px: float, py: float, pz: float, sx: float, sy: float, sz: float,
) -> float | None:
    """From a point, toward the sun: the distance to the wall if the line passes through
    one of the room's windows, else None."""

    bounds = current_region.bounds
    walls = {
        "x-min": (bounds.minimum.x, "x"), "x-max": (bounds.maximum.x, "x"),
        "y-min": (bounds.minimum.y, "y"), "y-max": (bounds.maximum.y, "y"),
    }
    for window in current_region.windows:
        plane, axis = walls[window.wall]
        s_axis = sx if axis == "x" else sy
        origin = px if axis == "x" else py
        if abs(s_axis) < 1e-9:
            continue
        u = (plane - origin) / s_axis
        if u <= 1e-6:
            continue
        along = (py + sy * u) if axis == "x" else (px + sx * u)
        height = pz + sz * u
        if window.from_mm <= along <= window.to_mm and window.sill_mm <= height <= window.top_mm:
            return u
    return None


def _blocked(
    px: float, py: float, pz: float, lx: float, ly: float, lz: float, reach: float,
    occluders: list[tuple[float, float, float, float, str | None]], skip: str | None,
) -> bool:
    """Whether a thing or a body stands on the line from a point toward a light."""

    for ox, oy, oz, r, oid in occluders:
        if oid is not None and oid == skip:
            continue
        vx, vy, vz = ox - px, oy - py, oz - pz
        u = vx * lx + vy * ly + vz * lz
        if 0.0 < u < reach:
            cx, cy, cz = vx - u * lx, vy - u * ly, vz - u * lz
            if cx * cx + cy * cy + cz * cz <= r * r:
                return True
    return False


def _direct_light(
    px: float, py: float, pz: float, *, normal: tuple[float, float, float] | None, toward_eye: tuple[float, float, float] | None,
    lights: list[_Light], current_region: PhysicalRegion,
    occluders: list[tuple[float, float, float, float, str | None]], skip: str | None, bands: int,
) -> list[float]:
    """Direct light per band at a point: for a surface, each light's incidence on its
    normal; for a round thing, the share of its lit half the eye can see. The sun comes
    only through a window; a lamp's light falls off with the square of the distance from
    its surface; anything standing between blocks it (a shadow)."""

    direct = [0.0] * bands
    for light in lights:
        if light.kind == "sun":
            lx, ly, lz = light.x, light.y, light.z
            reach = _through_window(current_region, px, py, pz, lx, ly, lz)
            if reach is None:
                continue
            falloff = 1.0
        else:
            vx, vy, vz = light.x - px, light.y - py, light.z - pz
            d = math.sqrt(vx * vx + vy * vy + vz * vz)
            if d <= light.radius_mm:
                continue
            lx, ly, lz = vx / d, vy / d, vz / d
            reach = d - light.radius_mm
            falloff = (light.radius_mm / d) ** 2
        if normal is not None:
            factor = normal[0] * lx + normal[1] * ly + normal[2] * lz
        else:
            factor = (1.0 + (toward_eye[0] * lx + toward_eye[1] * ly + toward_eye[2] * lz)) / 2.0
        if factor <= 0.0:
            continue
        if _blocked(px, py, pz, lx, ly, lz, reach, occluders, light.source_id if light.kind == "lamp" else skip):
            continue
        if skip is not None and light.kind == "lamp" and _blocked(px, py, pz, lx, ly, lz, reach, occluders, skip):
            continue
        for band in range(bands):
            direct[band] += light.ppm[band] * falloff * factor
    return direct


def _bounce_ppm(current_region: PhysicalRegion, lights: list[_Light]) -> tuple[int, ...]:
    """One bounce: the direct light that enters the room (the sun through its windows,
    what its lamps give off) lands on the room's surfaces and comes back once, spread
    over them: flux times the paint's reflectance over the room's surface area."""

    bounds = current_region.bounds
    lx, ly, lz = bounds.maximum.x - bounds.minimum.x, bounds.maximum.y - bounds.minimum.y, bounds.maximum.z - bounds.minimum.z
    area = 2.0 * (lx * ly + lx * lz + ly * lz)
    if area <= 0.0:
        return (0,) * len(current_region.reflectance_ppm)
    outward = {"x-min": (-1.0, 0.0), "x-max": (1.0, 0.0), "y-min": (0.0, -1.0), "y-max": (0.0, 1.0)}
    flux = [0.0] * len(current_region.reflectance_ppm)
    for light in lights:
        if light.kind == "sun":
            for window in current_region.windows:
                nx, ny = outward[window.wall]
                entering = nx * light.x + ny * light.y
                if entering <= 0.0:
                    continue
                window_area = (window.to_mm - window.from_mm) * (window.top_mm - window.sill_mm)
                for band in range(len(flux)):
                    flux[band] += light.ppm[band] * window_area * entering
        else:
            surface = 4.0 * math.pi * light.radius_mm * light.radius_mm
            for band in range(len(flux)):
                flux[band] += light.ppm[band] * surface
    return tuple(int(f * r / 1_000_000 / area) for f, r in zip(flux, current_region.reflectance_ppm))


_FOCAL_RAYS: dict[int, tuple[list[int], "np.ndarray", "np.ndarray"]] = {}
_EIGHT_BIT = tuple(Fraction(k, 255) for k in range(256))


def _focal_rays(site_geometry: RetinalSiteGeometry) -> tuple[list[int], "np.ndarray", "np.ndarray"]:
    """The focal sites' indices and their angular offsets (radians), once per geometry."""

    key = id(site_geometry)
    cached = _FOCAL_RAYS.get(key)
    if cached is None:
        focal = site_geometry[RETINA_TOTAL_RECEPTOR_COUNT:]
        indices = [site[0] for site in focal]
        h = np.radians(np.array([float(site[1]) for site in focal]) / 1000.0)
        v = np.radians(np.array([float(site[2]) for site in focal]) / 1000.0)
        cached = (indices, h, v)
        _FOCAL_RAYS.clear()
        _FOCAL_RAYS[key] = cached
    return cached


def _lit_surfaces_focal(
    observation: ObservationSnapshot,
    *,
    eye: PositionMM,
    body_heading_millidegrees: int,
    retinal_pitch_offset_millidegrees: int,
    current_region: PhysicalRegion,
    illumination_ppm: tuple[int, ...],
    pixels: list[tuple[Fraction, ...]],
    site_geometry: RetinalSiteGeometry,
    lights: list[_Light],
    occluders: list[tuple[float, float, float, float, str | None]],
) -> None:
    """The room's own surfaces through the focal sites: each site's ray meets the floor,
    a wall or the ceiling; that point carries the region's paint or a declared look's
    cell there, lit by the room's light (ambient and bounce) plus the direct light that
    reaches it: the sun through a window, a lamp; a shadow behind whatever stands in the
    way; the falloff of the angle. Geometry over every site at once; the result is
    written at the retina's own eight-bit grain."""

    if len(site_geometry) <= RETINA_TOTAL_RECEPTOR_COUNT or (not lights and not current_region.looks):
        return
    indices, h_offsets, v_offsets = _focal_rays(site_geometry)
    bounds = current_region.bounds
    bands = len(current_region.reflectance_ppm)
    h = math.radians(body_heading_millidegrees / 1000.0) + h_offsets
    v = math.radians(retinal_pitch_offset_millidegrees / 1000.0) + v_offsets
    cos_v = np.cos(v)
    d = np.stack((cos_v * np.cos(h), cos_v * np.sin(h), np.sin(v)))            # 3 x N ray directions
    origin = np.array([float(eye.x), float(eye.y), float(eye.z)])
    planes = (
        (bounds.minimum.z, 2, (0.0, 0.0, 1.0), "floor"), (bounds.maximum.z, 2, (0.0, 0.0, -1.0), "ceiling"),
        (bounds.minimum.x, 0, (1.0, 0.0, 0.0), "x-min"), (bounds.maximum.x, 0, (-1.0, 0.0, 0.0), "x-max"),
        (bounds.minimum.y, 1, (0.0, 1.0, 0.0), "y-min"), (bounds.maximum.y, 1, (0.0, -1.0, 0.0), "y-max"),
    )
    best = np.full(d.shape[1], np.inf)
    face = np.full(d.shape[1], -1, dtype=np.int64)
    for index, (plane, axis, _normal, _name) in enumerate(planes):
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(np.abs(d[axis]) < 1e-9, np.inf, (plane - origin[axis]) / d[axis])
        t = np.where(t > 1e-6, t, np.inf)
        closer = t < best
        best = np.where(closer, t, best)
        face = np.where(closer, index, face)
    hit = face >= 0
    if not hit.any():
        return
    best = np.where(hit, best, 0.0)
    point = origin[:, None] + d * best[None, :]                                   # 3 x N hit points
    normals = np.array([plane[2] for plane in planes] + [(0.0, 0.0, 0.0)])        # face -> normal (last: none)
    normal = normals[np.where(hit, face, len(planes))].T                          # 3 x N
    face_names = [plane[3] for plane in planes]

    paint = np.array(current_region.reflectance_ppm, dtype=np.float64)[:, None].repeat(d.shape[1], axis=1)   # bands x N
    has_look = np.zeros(d.shape[1], dtype=bool)
    for look in current_region.looks:
        face_index = face_names.index(look.face)
        if look.face in ("floor", "ceiling"):
            along, up = point[0], point[1]
        elif look.face.startswith("x"):
            along, up = point[1], point[2]
        else:
            along, up = point[0], point[2]
        inside = hit & (face == face_index) & ~has_look & (along >= look.from_mm) & (along <= look.to_mm) & (up >= look.low_mm) & (up <= look.high_mm)
        if not inside.any():
            continue
        surface = look.surface
        column = np.minimum(surface.columns - 1, ((along - look.from_mm) * surface.columns / (look.to_mm - look.from_mm)).astype(np.int64))
        row = np.minimum(surface.rows - 1, ((look.high_mm - up) * surface.rows / (look.high_mm - look.low_mm)).astype(np.int64))
        cells = np.array(surface.cell_palette_indices, dtype=np.int64).reshape(surface.rows, surface.columns)
        palette = np.array(surface.palette_reflectance_ppm, dtype=np.float64)     # entries x bands
        chosen = palette[cells[np.clip(row, 0, surface.rows - 1), np.clip(column, 0, surface.columns - 1)]].T   # bands x N
        paint = np.where(inside[None, :], chosen, paint)
        has_look |= inside

    direct = np.zeros((bands, d.shape[1]))
    for light in lights:
        if light.kind == "sun":
            lx = np.full(d.shape[1], light.x); ly = np.full(d.shape[1], light.y); lz = np.full(d.shape[1], light.z)
            reach = np.full(d.shape[1], np.inf)
            through = np.zeros(d.shape[1], dtype=bool)
            for window in current_region.windows:
                axis = 0 if window.wall.startswith("x") else 1
                plane = {"x-min": bounds.minimum.x, "x-max": bounds.maximum.x, "y-min": bounds.minimum.y, "y-max": bounds.maximum.y}[window.wall]
                s_axis = light.x if axis == 0 else light.y
                if abs(s_axis) < 1e-9:
                    continue
                u = (plane - point[axis]) / s_axis
                along = point[1] + light.y * u if axis == 0 else point[0] + light.x * u
                height = point[2] + light.z * u
                passes = (u > 1e-6) & (along >= window.from_mm) & (along <= window.to_mm) & (height >= window.sill_mm) & (height <= window.top_mm) & ~through
                reach = np.where(passes, u, reach)
                through |= passes
            lit = hit & through
            falloff = np.ones(d.shape[1])
            skip = None
        else:
            vx, vy, vz = light.x - point[0], light.y - point[1], light.z - point[2]
            dist = np.sqrt(vx * vx + vy * vy + vz * vz)
            lit = hit & (dist > light.radius_mm)
            safe = np.where(dist > 0, dist, 1.0)
            lx, ly, lz = vx / safe, vy / safe, vz / safe
            reach = dist - light.radius_mm
            falloff = (light.radius_mm / safe) ** 2
            skip = light.source_id
        factor = normal[0] * lx + normal[1] * ly + normal[2] * lz
        lit &= factor > 0.0
        if not lit.any():
            continue
        for ox, oy, oz, r, oid in occluders:
            if oid is not None and oid == skip:
                continue
            vx, vy, vz = ox - point[0], oy - point[1], oz - point[2]
            u = vx * lx + vy * ly + vz * lz
            cx, cy, cz = vx - u * lx, vy - u * ly, vz - u * lz
            shadow = (u > 0.0) & (u < reach) & (cx * cx + cy * cy + cz * cz <= r * r)
            lit &= ~shadow
            if not lit.any():
                break
        if not lit.any():
            continue
        gain = np.where(lit, falloff * factor, 0.0)
        for band in range(bands):
            direct[band] += light.ppm[band] * gain

    changed = hit & (has_look | (direct > 0.0).any(axis=0))
    if not changed.any():
        return
    illumination = np.array(illumination_ppm, dtype=np.float64)[:, None]
    values = np.clip(paint * (illumination + direct) / 1e12, 0.0, 1.0)
    eight_bit = np.rint(values * 255).astype(np.int64)
    for column in np.nonzero(changed)[0]:
        pixels[indices[column]] = tuple(_EIGHT_BIT[eight_bit[band, column]] for band in range(bands))

def _retinal_projection(
    observation: ObservationSnapshot,
    *,
    retinal_heading_offset_millidegrees: int = 0,
    retinal_pitch_offset_millidegrees: int = 0,
    site_geometry: RetinalSiteGeometry = RETINAL_SITE_GEOMETRY,
    sun: tuple[float, float, float, int] | None = None,
) -> tuple[tuple[Fraction, ...], ...]:
    if (
        isinstance(retinal_heading_offset_millidegrees, bool)
        or not isinstance(retinal_heading_offset_millidegrees, int)
        or not -180_000 <= retinal_heading_offset_millidegrees <= 180_000
    ):
        raise ValueError("retinal heading offset is outside physical geometry")
    if (
        isinstance(retinal_pitch_offset_millidegrees, bool)
        or not isinstance(retinal_pitch_offset_millidegrees, int)
        or not -90_000 <= retinal_pitch_offset_millidegrees <= 90_000
    ):
        raise ValueError("retinal pitch offset is outside physical geometry")
    body = _self_body(observation)
    eye = (
        _body_fixed_receptor_position(
            body,
            body.receptor_geometry.retinal_offset_mm,
        )
        if body.receptor_geometry is not None
        else body.pose.position
    )
    current_region = next(
        region for region in observation.regions
        if region.region_id == observation.room_id
    )
    lights, occluders = _room_lights(observation, current_region, sun)
    bounce = _bounce_ppm(current_region, lights)
    lit_illumination = tuple(
        i + b for i, b in zip(current_region.illumination_ppm, bounce, strict=True)
    )
    background = tuple(
        Fraction(reflectance * illumination, 1_000_000_000_000)
        for reflectance, illumination in zip(current_region.reflectance_ppm, lit_illumination, strict=True)
    )
    pixels: list[tuple[Fraction, ...]] = [
        background for _ in site_geometry
    ]
    focal_count = len(site_geometry) - RETINA_TOTAL_RECEPTOR_COUNT
    has_focal = focal_count > 0
    ambient_sites = site_geometry[:RETINA_TOTAL_RECEPTOR_COUNT]

    pitch = int(RETINA_FOCAL_PITCH_MILLIDEGREES)
    half_pitch = pitch // 2
    cell_area = 4 * half_pitch * half_pitch
    focal_left = -int(RETINA_FOCAL_HORIZONTAL_FOV_MILLIDEGREES) // 2
    focal_top = int(RETINA_FOCAL_VERTICAL_FOV_MILLIDEGREES) // 2

    _lit_surfaces_focal(
        observation,
        eye=eye,
        body_heading_millidegrees=(
            body.pose.heading_millidegrees
            + retinal_heading_offset_millidegrees
        ) % 360_000,
        retinal_pitch_offset_millidegrees=retinal_pitch_offset_millidegrees,
        current_region=current_region,
        illumination_ppm=lit_illumination,
        pixels=pixels,
        site_geometry=site_geometry,
        lights=lights,
        occluders=occluders,
    )
    _portal_aperture_background(
        observation,
        eye=eye,
        body_heading_millidegrees=(
            body.pose.heading_millidegrees
            + retinal_heading_offset_millidegrees
        ) % 360_000,
        retinal_pitch_offset_millidegrees=retinal_pitch_offset_millidegrees,
        current_region=current_region,
        pixels=pixels,
        site_geometry=site_geometry,
    )
    surfaces: list[_OpticalSurface] = []
    body_by_id = {candidate.body_id: candidate for candidate in observation.bodies}
    for other in observation.bodies:
        if other.body_id != observation.self_body_id:
            surfaces.append(
                _OpticalSurface(
                    position=other.pose.position,
                    radius_mm=other.radius_mm,
                    # The world has not specified a body material reflectance.
                    # A body can therefore only be a conservative silhouette.
                    reflectance_ppm=(0,) * OPTICAL_BANDS,
                    optical_surface=None,
                    source_id=other.body_id,
                )
            )
    for item in observation.objects:
        if item.held_by_body_id == observation.self_body_id:
            # What she holds is in her hand, at her hand's contact point (her touch
            # offset carried by her heading), where her eye can see it when she looks down.
            if body.receptor_geometry is None:
                continue
            position = _body_fixed_receptor_position(body, body.receptor_geometry.touch_offset_mm)
        else:
            position = (
                item.position
                if item.position is not None
                else body_by_id[item.held_by_body_id].pose.position
            )
        position = (
            PositionMM(
                position.x,
                position.y,
                position.z + item.radius_mm,
            )
            if item.optical_surface is not None
            else position
        )
        surfaces.append(
            _OpticalSurface(
                position=position,
                radius_mm=item.radius_mm,
                reflectance_ppm=item.reflectance_ppm,
                optical_surface=item.optical_surface,
                emission_ppm=getattr(item, "emission_ppm", ()) or (),
                source_id=item.object_id,
            )
        )

    half_horizontal = RETINA_HORIZONTAL_FOV_MILLIDEGREES // 2
    half_vertical = RETINA_VERTICAL_FOV_MILLIDEGREES // 2
    # Far-to-near compositing lets a nearer surface cover only its actual
    # receptor aperture instead of erasing the complete receptor cell.
    surfaces.sort(
        key=lambda surface: _position_distance_squared(eye, surface.position),
        reverse=True,
    )
    for surface in surfaces:
        floor_position = PositionMM(
            surface.position.x,
            surface.position.y,
            current_region.bounds.minimum.z,
        )
        if not _is_visible(
            observation,
            eye,
            floor_position,
            surface.radius_mm,
        ):
            continue
        dx = surface.position.x - eye.x
        dy = surface.position.y - eye.y
        dz = surface.position.z - eye.z
        planar_distance_squared = dx * dx + dy * dy
        if planar_distance_squared == 0:
            continue
        relative_horizontal = _wrap_heading_delta(
            _atan2_millidegrees(dy, dx),
            (
                body.pose.heading_millidegrees
                + retinal_heading_offset_millidegrees
            )
            % 360_000,
        )
        distance_squared = _position_distance_squared(eye, surface.position)
        distance = isqrt(distance_squared)
        angular_radius = abs(
            _atan2_millidegrees(surface.radius_mm, max(distance, 1))
        )
        planar_distance = max(isqrt(planar_distance_squared), 1)
        relative_vertical = _atan2_millidegrees(dz, planar_distance) - retinal_pitch_offset_millidegrees
        if (
            relative_horizontal + angular_radius < -half_horizontal
            or relative_horizontal - angular_radius > half_horizontal
            or relative_vertical + angular_radius < -half_vertical
            or relative_vertical - angular_radius > half_vertical
        ):
            continue
        # Region ownership belongs to the floor-mounted object, not its
        # raised optical center. Visibility already validated this same base.
        surface_region = _region_for(
            observation.regions,
            floor_position,
            surface.radius_mm,
        )
        if surface_region is None:
            continue
        pattern = surface.optical_surface
        if pattern is not None:
            pattern.verify()
        if surface_region.region_id == current_region.region_id:
            surface_illumination = lit_illumination
            if lights:
                # The direct light on a round thing: the share of its lit half the eye sees.
                tx, ty, tz = surface.position.x, surface.position.y, current_region.bounds.minimum.z + surface.radius_mm
                ex, ey, ez = eye.x - tx, eye.y - ty, eye.z - tz
                span = math.sqrt(ex * ex + ey * ey + ez * ez) or 1.0
                direct = _direct_light(tx, ty, tz, normal=None, toward_eye=(ex / span, ey / span, ez / span), lights=lights,
                                       current_region=current_region, occluders=occluders, skip=surface.source_id,
                                       bands=len(lit_illumination))
                if any(direct):
                    surface_illumination = tuple(int(i + d) for i, d in zip(lit_illumination, direct, strict=True))
        else:
            surface_illumination = surface_region.illumination_ppm

        if pattern is None:
            reflectance = surface.reflectance_ppm
            emission = surface.emission_ppm or ((0,) * len(reflectance))
            base_surface_light = tuple(
                min(
                    Fraction(1),
                    Fraction(value * illumination, 1_000_000_000_000)
                    + Fraction(emitted, 1_000_000),
                )
                for value, illumination, emitted in zip(
                    reflectance,
                    surface_illumination,
                    emission,
                )
            )
        else:
            base_surface_light = None

        # Ambient sites loop (135)
        for (
            site_index,
            horizontal_center,
            vertical_center,
            half_horizontal_receptor,
            half_vertical_receptor,
        ) in ambient_sites:
            if abs(vertical_center - relative_vertical) > (
                angular_radius + half_vertical_receptor
            ):
                continue
            if abs(horizontal_center - relative_horizontal) > (
                angular_radius + half_horizontal_receptor
            ):
                continue
            horizontal_overlap = max(
                0,
                min(
                    horizontal_center + half_horizontal_receptor,
                    relative_horizontal + angular_radius,
                )
                - max(
                    horizontal_center - half_horizontal_receptor,
                    relative_horizontal - angular_radius,
                ),
            )
            vertical_overlap = max(
                0,
                min(
                    vertical_center + half_vertical_receptor,
                    relative_vertical + angular_radius,
                )
                - max(
                    vertical_center - half_vertical_receptor,
                    relative_vertical - angular_radius,
                ),
            )
            # A round thing lights the sites whose centres lie within its angular
            # radius: its silhouette is a disc, not the box around it.
            if (
                (horizontal_center - relative_horizontal) ** 2
                + (vertical_center - relative_vertical) ** 2
            ) > angular_radius * angular_radius:
                continue
            coverage = Fraction(
                horizontal_overlap * vertical_overlap,
                4 * half_horizontal_receptor * half_vertical_receptor,
            )
            if coverage <= 0:
                continue
            if pattern is not None and angular_radius > 0:
                pattern_column = min(
                    pattern.columns - 1,
                    max(
                        0,
                        (
                            (
                                horizontal_center
                                - relative_horizontal
                                + angular_radius
                            )
                            * pattern.columns
                        )
                        // (2 * angular_radius),
                    ),
                )
                pattern_row = min(
                    pattern.rows - 1,
                    max(
                        0,
                        (
                            (
                                relative_vertical
                                + angular_radius
                                - vertical_center
                            )
                            * pattern.rows
                        )
                        // (2 * angular_radius),
                    ),
                )
                reflectance = pattern.reflectance_at_verified_ppm(
                    row=pattern_row,
                    column=pattern_column,
                )
                emission = surface.emission_ppm or ((0,) * len(reflectance))
                surface_light = tuple(
                    min(
                        Fraction(1),
                        Fraction(value * illumination, 1_000_000_000_000)
                        + Fraction(emitted, 1_000_000),
                    )
                    for value, illumination, emitted in zip(
                        reflectance,
                        surface_illumination,
                        emission,
                    )
                )
            else:
                surface_light = base_surface_light
            pixels[site_index] = tuple(
                prior * (1 - coverage) + observed * coverage
                for prior, observed in zip(
                    pixels[site_index], surface_light, strict=True
                )
            )

        # Accelerated focal grid projection
        if has_focal:
            H_min = relative_horizontal - angular_radius
            H_max = relative_horizontal + angular_radius
            V_min = relative_vertical - angular_radius
            V_max = relative_vertical + angular_radius
            col_min = max(0, (H_min - focal_left) // pitch)
            col_max = min(RETINA_FOCAL_COLUMNS - 1, (H_max - focal_left) // pitch)
            row_min = max(0, (focal_top - V_max) // pitch)
            row_max = min(RETINA_FOCAL_ROWS - 1, (focal_top - V_min) // pitch)
            if col_min <= col_max and row_min <= row_max:
                for r in range(row_min, row_max + 1):
                    v_center = focal_top - (2 * r + 1) * half_pitch
                    if abs(v_center - relative_vertical) > (angular_radius + half_pitch):
                        continue
                    v_overlap = max(
                        0,
                        min(v_center + half_pitch, V_max)
                        - max(v_center - half_pitch, V_min),
                    )
                    if not v_overlap:
                        continue
                    row_offset = RETINA_TOTAL_RECEPTOR_COUNT + r * RETINA_FOCAL_COLUMNS
                    for c in range(col_min, col_max + 1):
                        h_center = focal_left + (2 * c + 1) * half_pitch
                        if abs(h_center - relative_horizontal) > (angular_radius + half_pitch):
                            continue
                        h_overlap = max(
                            0,
                            min(h_center + half_pitch, H_max)
                            - max(h_center - half_pitch, H_min),
                        )
                        if not h_overlap:
                            continue
                        # A round thing lights the sites whose centres lie within its
                        # angular radius: its silhouette is a disc, not the box around it.
                        if (
                            (h_center - relative_horizontal) ** 2
                            + (v_center - relative_vertical) ** 2
                        ) > angular_radius * angular_radius:
                            continue
                        if pattern is not None and angular_radius > 0:
                            # A focal site integrates the light over its whole aperture:
                            # every pattern cell the aperture covers, averaged (a point
                            # sample flickered with sub-site shifts as she moved).
                            span = 2 * angular_radius
                            c_lo = max(0, ((h_center - half_pitch - relative_horizontal + angular_radius) * pattern.columns) // span)
                            c_hi = min(pattern.columns - 1, ((h_center + half_pitch - relative_horizontal + angular_radius) * pattern.columns) // span)
                            r_lo = max(0, ((relative_vertical + angular_radius - (v_center + half_pitch)) * pattern.rows) // span)
                            r_hi = min(pattern.rows - 1, ((relative_vertical + angular_radius - (v_center - half_pitch)) * pattern.rows) // span)
                            c_lo, c_hi = int(c_lo), max(int(c_lo), int(c_hi))
                            r_lo, r_hi = int(r_lo), max(int(r_lo), int(r_hi))
                            cells = 0
                            summed = None
                            for p_row in range(r_lo, r_hi + 1):
                                for p_col in range(c_lo, c_hi + 1):
                                    cell = pattern.reflectance_at_verified_ppm(row=p_row, column=p_col)
                                    summed = list(cell) if summed is None else [a + b for a, b in zip(summed, cell)]
                                    cells += 1
                            refl = tuple(Fraction(v, cells) for v in summed)
                            em = surface.emission_ppm or ((0,) * len(refl))
                            surface_light = tuple(
                                min(
                                    Fraction(1),
                                    Fraction(val * ill, 1_000_000_000_000)
                                    + Fraction(e, 1_000_000),
                                )
                                for val, ill, e in zip(
                                    refl,
                                    surface_illumination,
                                    em,
                                )
                            )
                        else:
                            surface_light = base_surface_light
                        s_idx = row_offset + c
                        if h_overlap * v_overlap == cell_area:
                            pixels[s_idx] = surface_light
                        else:
                            coverage = Fraction(h_overlap * v_overlap, cell_area)
                            pixels[s_idx] = tuple(
                                prior * (1 - coverage) + observed * coverage
                                for prior, observed in zip(
                                    pixels[s_idx], surface_light, strict=True
                                )
                            )
    return tuple(pixels)


def retinal_irradiance_field(
    observation: ObservationSnapshot,
    *,
    retinal_heading_offset_millidegrees: int = 0,
    retinal_pitch_offset_millidegrees: int = 0,
    include_focal: bool = False,
    sun: tuple[float, float, float, int] | None = None,
) -> tuple[tuple[Fraction, ...], ...]:
    """The bounded six-band optical field, without temporary signal objects. With the
    sun given (its direction and the sky's light), the room's surfaces carry its direct
    light through the room's windows on the focal sites."""

    if not isinstance(include_focal, bool):
        raise TypeError("retinal spatial coverage must be explicit")
    geometry = UPGRADED_RETINAL_SITE_GEOMETRY if include_focal else RETINAL_SITE_GEOMETRY
    pixels = _retinal_projection(
        observation,
        retinal_heading_offset_millidegrees=retinal_heading_offset_millidegrees,
        retinal_pitch_offset_millidegrees=retinal_pitch_offset_millidegrees,
        site_geometry=geometry,
        sun=sun,
    )
    if len(pixels) != len(geometry):
        raise RuntimeError("world retinal field changed mounted site count")
    for pixel in pixels:
        if len(pixel) != OPTICAL_BANDS:
            raise RuntimeError("world lost the six-band retinal field")
        for value in pixel:
            den = value._denominator
            if not -den <= value._numerator <= den:
                raise ValueError("physical receptor signal left the physical receptor boundary")
    return pixels


def _retinal_substreams(
    before: ObservationSnapshot,
    after: ObservationSnapshot,
    *,
    before_retinal_heading_offset_millidegrees: int = 0,
    after_retinal_heading_offset_millidegrees: int = 0,
    source_time_start: Fraction = Fraction(0),
    source_time_end: Fraction = Fraction(1),
) -> tuple[NativeSensorySubstreamInput, ...]:
    before_pixels = retinal_irradiance_field(
        before,
        retinal_heading_offset_millidegrees=(
            before_retinal_heading_offset_millidegrees
        ),
    )
    after_pixels = retinal_irradiance_field(
        after,
        retinal_heading_offset_millidegrees=(
            after_retinal_heading_offset_millidegrees
        ),
    )
    result = []
    for receptor_index in range(RETINA_TOTAL_RECEPTOR_COUNT):
        if receptor_index < RETINA_RECEPTOR_COUNT:
            row = receptor_index // RETINA_COLUMNS
            column = receptor_index % RETINA_COLUMNS
            name = f"retinal-cell-{row}-{column}"
            row_coordinate = str(row)
            column_coordinate = str(column)
        else:
            fine_index = receptor_index - RETINA_RECEPTOR_COUNT
            row = fine_index // RETINA_FINE_COLUMNS
            column = fine_index % RETINA_FINE_COLUMNS
            name = f"retinal-fine-{row}-{column}"
            row_coordinate = f"fine-{row}"
            column_coordinate = f"fine-{column}"
        for band in range(OPTICAL_BANDS):
            topology_index = receptor_index * OPTICAL_BANDS + band
            result.append(
                _native_signal(
                    sense=PhysicalSense.SIGHT,
                    sensor_id="W1-retina",
                    substream_id=f"{name}-band-{band}",
                    topology_index=topology_index,
                    coordinates=(
                        NativeAxisCoordinate("retinal-row", row_coordinate),
                        NativeAxisCoordinate("retinal-column", column_coordinate),
                        NativeAxisCoordinate("optical-band", str(band)),
                    ),
                    physical_quantity="retinal-spectral-irradiance",
                    physical_unit=RETINAL_REFERENCE_IRRADIANCE_UNIT,
                    values=(
                        before_pixels[receptor_index][band],
                        after_pixels[receptor_index][band],
                    ),
                    source_time_start=source_time_start,
                    source_time_end=source_time_end,
                )
            )
    return tuple(result)


def _body_substreams_for_snapshots(
    before_observation: ObservationSnapshot,
    after_observation: ObservationSnapshot,
    *,
    source_time_start: Fraction = Fraction(0),
    source_time_end: Fraction = Fraction(1),
) -> tuple[NativeSensorySubstreamInput, ...]:
    before = _self_body(before_observation)
    after = _self_body(after_observation)
    span_x = max(
        region.bounds.maximum.x for region in after_observation.regions
    ) - min(region.bounds.minimum.x for region in after_observation.regions)
    span_y = max(
        region.bounds.maximum.y for region in after_observation.regions
    ) - min(region.bounds.minimum.y for region in after_observation.regions)
    span_z = max(
        region.bounds.maximum.z for region in after_observation.regions
    ) - min(region.bounds.minimum.z for region in after_observation.regions)
    displacements = (
        Fraction(after.pose.position.x - before.pose.position.x, max(span_x, 1)),
        Fraction(after.pose.position.y - before.pose.position.y, max(span_y, 1)),
        Fraction(after.pose.position.z - before.pose.position.z, max(span_z, 1)),
        Fraction(
            _wrap_heading_delta(
                after.pose.heading_millidegrees,
                before.pose.heading_millidegrees,
            ),
            180_000,
        ),
    )
    axes = ("translation-x", "translation-y", "translation-z", "rotation-yaw")
    if len(axes) != BODY_RECEPTOR_COUNT:
        raise RuntimeError("W1 body receptor anatomy changed")
    return tuple(
        _native_signal(
            sense=PhysicalSense.BODY,
            sensor_id="W1-body-displacement-receptors",
            substream_id=f"body-displacement-{axis}",
            topology_index=index,
            coordinates=(
                NativeAxisCoordinate("somatic-axis", axis),
                NativeAxisCoordinate("somatic-frame", "egocentric-before-after"),
            ),
            physical_quantity="authenticated-body-displacement",
            values=(Fraction(0), displacement),
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        )
        for index, (axis, displacement) in enumerate(zip(axes, displacements))
    )


def _touch_values(observation: ObservationSnapshot) -> tuple[Fraction, ...]:
    body = _self_body(observation)
    held = tuple(
        item for item in observation.objects
        if item.held_by_body_id == observation.self_body_id
    )
    if len(held) > 1:
        raise ValueError("physical hold geometry is not reciprocal")
    contacted = tuple(
        item
        for item in observation.objects
        if body.active_contact is not None
        and item.object_id == body.active_contact.object_id
    )
    if len(contacted) > 1:
        raise ValueError("physical palmar contact identity is not unique")
    item = held[0] if held else (contacted[0] if contacted else None)
    values = (
        Fraction(1 if item is not None else 0),
        Fraction(item.radius_mm, max(body.radius_mm, item.radius_mm))
        if item is not None
        else Fraction(0),
        Fraction(item.radius_mm, max(body.reach_mm, item.radius_mm))
        if item is not None
        else Fraction(0),
    )
    return values


def _touch_substreams(
    before: ObservationSnapshot,
    after: ObservationSnapshot,
    *,
    source_time_start: Fraction = Fraction(0),
    source_time_end: Fraction = Fraction(1),
) -> tuple[NativeSensorySubstreamInput, ...]:
    before_values = _touch_values(before)
    after_values = _touch_values(after)
    axes = ("contact", "contact-radius", "normal-load")
    if len(axes) != TOUCH_RECEPTOR_COUNT:
        raise RuntimeError("W1 touch receptor anatomy changed")
    return tuple(
        _native_signal(
            sense=PhysicalSense.TOUCH,
            sensor_id="W1-body-surface-receptors",
            substream_id=f"palmar-{axis}",
            topology_index=index,
            coordinates=(
                NativeAxisCoordinate("body-surface", "palmar"),
                NativeAxisCoordinate("contact-axis", axis),
            ),
            physical_quantity="contact-and-geometric-load",
            values=(before_values[index], after_values[index]),
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        )
        for index, axis in enumerate(axes)
    )


def _physical_substreams(
    observation: ObservationSnapshot,
    execution_receipt: ActionExecutionReceipt | None,
) -> dict[PhysicalSense, tuple[NativeSensorySubstreamInput, ...]]:
    before = (
        execution_receipt.before
        if execution_receipt is not None
        else observation
    )
    observed = {
        PhysicalSense.SIGHT: _retinal_substreams(before, observation),
        PhysicalSense.TOUCH: _touch_substreams(before, observation),
    }
    if execution_receipt is not None:
        observed[PhysicalSense.BODY] = _body_substreams_for_snapshots(
            execution_receipt.before,
            execution_receipt.after,
        )
    return observed



def physical_contact_substreams(
    before: ObservationSnapshot,
    after: ObservationSnapshot,
    *,
    causal_transition: bool,
    source_time_start: Fraction,
    source_time_end: Fraction,
) -> dict[PhysicalSense, tuple[NativeSensorySubstreamInput, ...]]:
    """Shared touch/body construction; the caller owns world authentication."""

    if not isinstance(causal_transition, bool):
        raise ValueError("physical receptor causal-transition flag must be boolean")
    if source_time_end <= source_time_start:
        raise ValueError("physical receptor interval must be positive")
    observed = {
        PhysicalSense.TOUCH: _touch_substreams(
            before, after,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        ),
    }
    if causal_transition:
        observed[PhysicalSense.BODY] = _body_substreams_for_snapshots(
            before, after,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        )
    return observed

def physical_receptor_substreams(
    before: ObservationSnapshot,
    after: ObservationSnapshot,
    *,
    causal_transition: bool,
    before_retinal_heading_offset_millidegrees: int = 0,
    after_retinal_heading_offset_millidegrees: int = 0,
    source_time_start: Fraction,
    source_time_end: Fraction,
) -> dict[PhysicalSense, tuple[NativeSensorySubstreamInput, ...]]:
    """Build only physical receptor signals for one verified W1 interval.

    The caller owns world authentication.  ``causal_transition`` may only be
    true after it has verified the corresponding execution receipt.
    """

    if not isinstance(causal_transition, bool):
        raise ValueError("physical receptor causal-transition flag must be boolean")
    observed = {
        PhysicalSense.SIGHT: _retinal_substreams(
            before, after,
            before_retinal_heading_offset_millidegrees=before_retinal_heading_offset_millidegrees,
            after_retinal_heading_offset_millidegrees=after_retinal_heading_offset_millidegrees,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        ),
    }
    observed.update(physical_contact_substreams(
        before, after, causal_transition=causal_transition,
        source_time_start=source_time_start, source_time_end=source_time_end,
    ))
    return observed


def physical_receptor_joint_units(
    observed: Mapping[PhysicalSense, tuple[NativeSensorySubstreamInput, ...]],
) -> tuple[tuple[tuple[PhysicalSense, int], ...], ...]:
    """Declare this anatomy's joint-source units for one built interval.

    The declaration follows the receptor anatomy defined in this module:
    the spectral bands of one retinal cell observe one optical occurrence
    jointly; the palmar surface's contact axes observe one contact
    occurrence jointly; the body-displacement axes observe one body-motion
    occurrence jointly.  Receptor sites (retinal cells) remain separate
    occurrences, mirroring the foveal per-segment precedent.
    """

    units: list[tuple[tuple[PhysicalSense, int], ...]] = []
    for sense, ports in observed.items():
        if not ports:
            continue
        if sense is PhysicalSense.SIGHT:
            cells: dict[
                tuple[tuple[str, str], ...], list[int]
            ] = {}
            for port in ports:
                cell = tuple(
                    (coordinate.axis_id, coordinate.coordinate_id)
                    for coordinate in port.coordinates
                    if coordinate.axis_id != "optical-band"
                )
                cells.setdefault(cell, []).append(port.topology_index)
            units.extend(
                tuple((sense, index) for index in sorted(indices))
                for indices in cells.values()
            )
        else:
            units.append(
                tuple((sense, port.topology_index) for port in ports)
            )
    return tuple(units)


@dataclass(frozen=True, slots=True)
class OutcomeObservationReceipt:
    world_observation_receipt_sha256: str
    execution_receipt_sha256: str | None
    world_revision: int
    transducer_profile: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "schema": OUTCOME_OBSERVATION_SCHEMA,
            "transducer_profile": self.transducer_profile,
            "world_observation_receipt_sha256": self.world_observation_receipt_sha256,
            "world_revision": self.world_revision,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class EmbodiedSensoryOutcome:
    observation_receipt: OutcomeObservationReceipt
    built_full_field: BuiltSixSenseFullField
    causal_settlement: CausalExperienceSettlement
    physical_substreams: tuple[NativeSensorySubstreamInput, ...]


class EmbodimentSensoryOutcomeAuthority:
    """Stateless authenticated W1 control-topology/sensory firewall."""

    def __init__(self, *, authority_key: bytes | str) -> None:
        self._key = _authority_key(authority_key)

    def _observation_receipt(
        self,
        observation: ObservationSnapshot,
        execution_receipt: ActionExecutionReceipt | None,
    ) -> OutcomeObservationReceipt:
        unsigned = {
            "execution_receipt_sha256": (
                execution_receipt.authority_receipt_sha256
                if execution_receipt is not None
                else None
            ),
            "schema": OUTCOME_OBSERVATION_SCHEMA,
            "transducer_profile": TRANSDUCER_PROFILE,
            "world_observation_receipt_sha256": observation.authority_receipt_sha256,
            "world_revision": observation.revision,
        }
        signature = _sign(self._key, OUTCOME_OBSERVATION_DOMAIN, unsigned)
        return OutcomeObservationReceipt(
            world_observation_receipt_sha256=observation.authority_receipt_sha256,
            execution_receipt_sha256=unsigned["execution_receipt_sha256"],
            world_revision=observation.revision,
            transducer_profile=TRANSDUCER_PROFILE,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest(
                {"authority_hmac_sha256": signature, "payload": unsigned}
            ),
        )

    def verify_outcome_observation_receipt(
        self,
        receipt: OutcomeObservationReceipt,
    ) -> None:
        if not isinstance(receipt, OutcomeObservationReceipt):
            raise ValueError("outcome observation receipt is not typed")
        _sha256_identity(
            receipt.world_observation_receipt_sha256,
            "bound world observation receipt",
        )
        if receipt.execution_receipt_sha256 is not None:
            _sha256_identity(
                receipt.execution_receipt_sha256,
                "bound execution receipt",
            )
        if receipt.transducer_profile != TRANSDUCER_PROFILE:
            raise ValueError("physical receptor profile changed")
        if (
            isinstance(receipt.world_revision, bool)
            or not isinstance(receipt.world_revision, int)
            or not 0 <= receipt.world_revision <= MAX_WORLD_REVISION
        ):
            raise ValueError("physical receptor revision changed")
        unsigned = receipt.unsigned_record()
        expected_hmac = _sign(self._key, OUTCOME_OBSERVATION_DOMAIN, unsigned)
        if not hmac.compare_digest(expected_hmac, receipt.authority_hmac_sha256):
            raise ValueError("outcome observation HMAC changed")
        expected_receipt = _digest(
            {"authority_hmac_sha256": expected_hmac, "payload": unsigned}
        )
        if expected_receipt != receipt.authority_receipt_sha256:
            raise ValueError("outcome observation receipt identity changed")

    def transduce(
        self,
        observation: ObservationSnapshot,
        *,
        causal_owner: ExactCausalExperienceOwner,
        execution_receipt: ActionExecutionReceipt | None = None,
        commit: bool = True,
    ) -> EmbodiedSensoryOutcome:
        if not isinstance(causal_owner, ExactCausalExperienceOwner):
            raise ValueError("physical receptor outcome requires an exact causal owner")
        if not isinstance(commit, bool):
            raise ValueError("physical receptor commit flag must be boolean")
        _verify_observation(self._key, observation)
        if execution_receipt is not None:
            _verify_execution(self._key, execution_receipt, observation)
        outcome_receipt = self._observation_receipt(
            observation, execution_receipt
        )
        self.verify_outcome_observation_receipt(outcome_receipt)
        observed = _physical_substreams(observation, execution_receipt)
        states = {
            sense: (
                SenseBoundaryState.OBSERVED
                if sense in observed
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        }
        built = build_six_sense_full_field(
            assembly_id=(
                f"embodied-outcome-{outcome_receipt.authority_receipt_sha256}"
            ),
            source_time_start=Fraction(0),
            source_time_end=Fraction(1),
            observed_substreams=observed,
            states=states,
            occurrences=declare_joint_source_occurrences(
                observed_substreams=observed,
                declared_units=physical_receptor_joint_units(observed),
            ),
        )
        settlement = causal_owner.settle(
            built,
            routing_chis=(),
            source_tags=(
                f"embodiment-outcome:{outcome_receipt.authority_receipt_sha256}",
            ),
            commit=commit,
        )
        settlement.verify()
        return EmbodiedSensoryOutcome(
            observation_receipt=outcome_receipt,
            built_full_field=built,
            causal_settlement=settlement,
            physical_substreams=tuple(
                substream
                for sense in SENSE_ORDER
                for substream in observed.get(sense, ())
            ),
        )


__all__ = (
    "BODY_RECEPTOR_COUNT",
    "EmbodiedSensoryOutcome",
    "EmbodimentSensoryOutcomeAuthority",
    "OUTCOME_OBSERVATION_SCHEMA",
    "OutcomeObservationReceipt",
    "RETINA_COLUMNS",
    "RETINA_ROWS",
    "RETINA_SUBSTREAM_COUNT",
    "TOUCH_RECEPTOR_COUNT",
    "TRANSDUCER_PROFILE",
    "_is_visible",
    "physical_receptor_joint_units",
    "physical_receptor_substreams",
)
