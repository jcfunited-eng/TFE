"""Authenticated bounded physical receptors for the W1 embodiment.

The world authority contains privileged control topology because it must execute
commands.  This module is the sensory firewall: topology names, object ids,
body ids, room coordinates, and command kinds never become receptor values or
receptor coordinates.

Sight is a fixed retinotopic photon field.  Heading and a finite field of view
determine which physical surfaces reach each receptor; the nearest surface in
one receptor aperture occludes farther surfaces.  Body sensation exists only
for an authenticated before/after execution and contains egocentric
displacement.  Touch contains only contact and load geometry from the
reciprocal hold relation.  The resulting native signals enter the existing
unchanged L0--L4 full-field builder.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction
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
RETINA_SUBSTREAM_COUNT = RETINA_RECEPTOR_COUNT * OPTICAL_BANDS
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
    if not -1 <= value <= 1:
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
    if body.pose.heading_millidegrees % 90_000:
        if offset.x != 0 or offset.y != 0:
            raise ValueError(
                "signed receptor offset requires exact heading geometry"
            )
        dx, dy = 0, 0
    else:
        quarter_turns = (body.pose.heading_millidegrees // 90_000) % 4
        if quarter_turns == 0:
            dx, dy = offset.x, offset.y
        elif quarter_turns == 1:
            dx, dy = -offset.y, offset.x
        elif quarter_turns == 2:
            dx, dy = -offset.x, -offset.y
        else:
            dx, dy = offset.y, -offset.x
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


def _retinal_projection(
    observation: ObservationSnapshot,
) -> tuple[tuple[Fraction, ...], ...]:
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
    background = tuple(
        Fraction(reflectance * illumination, 1_000_000_000_000)
        for reflectance, illumination in zip(
            current_region.reflectance_ppm,
            current_region.illumination_ppm,
        )
    )
    pixels: list[tuple[Fraction, ...]] = [
        background for _ in range(RETINA_RECEPTOR_COUNT)
    ]
    depths: list[int | None] = [None] * RETINA_RECEPTOR_COUNT
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
                )
            )
    for item in observation.objects:
        if item.held_by_body_id == observation.self_body_id:
            continue
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
            )
        )

    half_horizontal = RETINA_HORIZONTAL_FOV_MILLIDEGREES // 2
    half_horizontal_receptor = RETINA_HORIZONTAL_FOV_MILLIDEGREES // (
        2 * RETINA_COLUMNS
    )
    half_vertical = RETINA_VERTICAL_FOV_MILLIDEGREES // 2
    half_vertical_receptor = RETINA_VERTICAL_FOV_MILLIDEGREES // (
        2 * RETINA_ROWS
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
            body.pose.heading_millidegrees,
        )
        distance_squared = _position_distance_squared(eye, surface.position)
        distance = isqrt(distance_squared)
        angular_radius = abs(
            _atan2_millidegrees(surface.radius_mm, max(distance, 1))
        )
        planar_distance = max(isqrt(planar_distance_squared), 1)
        relative_vertical = _atan2_millidegrees(dz, planar_distance)
        if (
            relative_horizontal + angular_radius < -half_horizontal
            or relative_horizontal - angular_radius > half_horizontal
            or relative_vertical + angular_radius < -half_vertical
            or relative_vertical - angular_radius > half_vertical
        ):
            continue
        attenuation = Fraction(
            surface.radius_mm * surface.radius_mm,
            surface.radius_mm * surface.radius_mm + max(distance_squared, 1),
        )
        pattern = surface.optical_surface
        if pattern is not None:
            pattern.verify()
        for row in range(RETINA_ROWS):
            vertical_center = (
                half_vertical
                - row
                * (RETINA_VERTICAL_FOV_MILLIDEGREES // RETINA_ROWS)
                - half_vertical_receptor
            )
            if abs(vertical_center - relative_vertical) > (
                angular_radius + half_vertical_receptor
            ):
                continue
            for column in range(RETINA_COLUMNS):
                horizontal_center = (
                    -half_horizontal
                    + column
                    * (RETINA_HORIZONTAL_FOV_MILLIDEGREES // RETINA_COLUMNS)
                    + half_horizontal_receptor
                )
                if abs(horizontal_center - relative_horizontal) > (
                    angular_radius + half_horizontal_receptor
                ):
                    continue
                reflectance = surface.reflectance_ppm
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
                light = tuple(
                    Fraction(value * illumination, 1_000_000_000_000)
                    * attenuation
                    for value, illumination in zip(
                        reflectance,
                        current_region.illumination_ppm,
                    )
                )
                index = row * RETINA_COLUMNS + column
                if depths[index] is None or distance_squared < depths[index]:
                    depths[index] = distance_squared
                    pixels[index] = light
    return tuple(pixels)


def _retinal_substreams(
    before: ObservationSnapshot,
    after: ObservationSnapshot,
    *,
    source_time_start: Fraction = Fraction(0),
    source_time_end: Fraction = Fraction(1),
) -> tuple[NativeSensorySubstreamInput, ...]:
    before_pixels = _retinal_projection(before)
    after_pixels = _retinal_projection(after)
    result = []
    for row in range(RETINA_ROWS):
        for column in range(RETINA_COLUMNS):
            receptor_index = row * RETINA_COLUMNS + column
            for band in range(OPTICAL_BANDS):
                topology_index = receptor_index * OPTICAL_BANDS + band
                result.append(
                    _native_signal(
                        sense=PhysicalSense.SIGHT,
                        sensor_id="W1-retina",
                        substream_id=f"retinal-cell-{row}-{column}-band-{band}",
                        topology_index=topology_index,
                        coordinates=(
                            NativeAxisCoordinate("retinal-row", str(row)),
                            NativeAxisCoordinate("retinal-column", str(column)),
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
    item = held[0] if held else None
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


def physical_receptor_substreams(
    before: ObservationSnapshot,
    after: ObservationSnapshot,
    *,
    causal_transition: bool,
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
            before,
            after,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        ),
        PhysicalSense.TOUCH: _touch_substreams(
            before,
            after,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        ),
    }
    if causal_transition:
        observed[PhysicalSense.BODY] = _body_substreams_for_snapshots(
            before,
            after,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        )
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
