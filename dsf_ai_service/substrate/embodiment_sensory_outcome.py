"""Authenticated W1 geometry to native full-field causal experience.

This authority is deliberately narrow and stateless.  It authenticates one
``EmbodimentWorldAuthority`` observation (and, for an action outcome, the
applied execution receipt whose ``after`` observation it is), derives native
dimensionless spatial signals only from the exact integer world geometry,
passes those signals through the unchanged canonical L0--L4 adapter, and asks
the existing exact causal owner to settle the resulting six-sense boundary.

No object name, word, chi, table, score, learned model, or compatibility vector
determines a signal.  Object identifiers occur only as topology coordinates so
independent physical objects are not flattened into one channel.  Sound,
smell, and taste remain explicitly unavailable because W1 has no such physical
sources yet.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    BuiltSixSenseFullField,
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
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
    EmbodiedObject,
    ObservationSnapshot,
    PhysicalPortal,
    PhysicalRegion,
    PositionMM,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    ExactCausalExperienceOwner,
)


OUTCOME_OBSERVATION_SCHEMA = "guala.embodiment.sensory_outcome_observation.v2"
OUTCOME_OBSERVATION_DOMAIN = b"guala-embodiment-sensory-outcome-observation-v2\0"
TRANSDUCER_PROFILE = "guala.embodiment.exact_geometry_transducer.v3"

MAX_AUTHORITY_KEY_BYTES = 4096
MAX_WORLD_OBJECTS = 16
MAX_WORLD_BODIES = 4
MAX_WORLD_REGIONS = 4
MAX_WORLD_PORTALS = 6
MAX_WORLD_REVISION = (1 << 63) - 1


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
        raise ValueError("embodiment sensory authority key must be bytes or text")
    if not result or len(result) > MAX_AUTHORITY_KEY_BYTES:
        raise ValueError("embodiment sensory authority key must be bounded and nonempty")
    return result


def _sha256_identity(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _floor_discs_overlap(
    left: PositionMM,
    left_radius: int,
    right: PositionMM,
    right_radius: int,
) -> bool:
    return (
        (left.x - right.x) ** 2 + (left.y - right.y) ** 2
        < (left_radius + right_radius) ** 2
    )


def _region_for(
    regions: tuple[PhysicalRegion, ...],
    position: PositionMM,
    radius_mm: int,
) -> PhysicalRegion | None:
    containing = tuple(
        item
        for item in regions
        if item.bounds.contains_floor_disc(position, radius_mm)
    )
    return containing[0] if len(containing) == 1 else None


def _portal_between(
    portals: tuple[PhysicalPortal, ...],
    left_region_id: str,
    right_region_id: str,
) -> PhysicalPortal | None:
    pair = tuple(sorted((left_region_id, right_region_id)))
    return next((item for item in portals if item.region_ids == pair), None)


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
        (0 <= plane_offset <= delta_axis)
        if delta_axis > 0
        else (delta_axis <= plane_offset <= 0)
    ):
        return False
    aperture_numerator = (
        start_aperture * delta_axis
        + (finish_aperture - start_aperture) * plane_offset
    )
    height_numerator = (
        start.z * delta_axis + (finish.z - start.z) * plane_offset
    )
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


def _verify_world_geometry(observation: ObservationSnapshot) -> None:
    if (
        isinstance(observation.revision, bool)
        or not isinstance(observation.revision, int)
        or not 0 <= observation.revision <= MAX_WORLD_REVISION
    ):
        raise ValueError("world observation revision is invalid")
    if (
        not 3 <= len(observation.regions) <= MAX_WORLD_REGIONS
        or observation.regions
        != tuple(sorted(observation.regions, key=lambda item: item.region_id))
        or len({item.region_id for item in observation.regions})
        != len(observation.regions)
    ):
        raise ValueError("world observation region topology changed")
    for region in observation.regions:
        region.verify()
    if (
        not 2 <= len(observation.portals) <= MAX_WORLD_PORTALS
        or observation.portals
        != tuple(sorted(observation.portals, key=lambda item: item.portal_id))
        or len({item.portal_id for item in observation.portals})
        != len(observation.portals)
    ):
        raise ValueError("world observation portal topology changed")
    region_ids = {item.region_id for item in observation.regions}
    region_by_id = {item.region_id: item for item in observation.regions}
    portal_pairs: set[tuple[str, str]] = set()
    for portal in observation.portals:
        portal.verify()
        if (
            any(item not in region_ids for item in portal.region_ids)
            or portal.region_ids in portal_pairs
        ):
            raise ValueError("world observation portal edge changed")
        portal_pairs.add(portal.region_ids)
        left, right = (region_by_id[item] for item in portal.region_ids)
        if portal.axis == "x":
            shared = {
                left.bounds.minimum.x, left.bounds.maximum.x
            }.intersection(
                {right.bounds.minimum.x, right.bounds.maximum.x}
            )
            overlap_min = max(
                left.bounds.minimum.y, right.bounds.minimum.y
            )
            overlap_max = min(
                left.bounds.maximum.y, right.bounds.maximum.y
            )
        else:
            shared = {
                left.bounds.minimum.y, left.bounds.maximum.y
            }.intersection(
                {right.bounds.minimum.y, right.bounds.maximum.y}
            )
            overlap_min = max(
                left.bounds.minimum.x, right.bounds.minimum.x
            )
            overlap_max = min(
                left.bounds.maximum.x, right.bounds.maximum.x
            )
        if (
            shared != {portal.plane_mm}
            or not overlap_min <= portal.aperture_min_mm
            < portal.aperture_max_mm <= overlap_max
            or portal.height_mm > min(
                left.bounds.maximum.z, right.bounds.maximum.z
            )
        ):
            raise ValueError("world observation portal aperture changed")
    if not 2 <= len(observation.bodies) <= MAX_WORLD_BODIES:
        raise ValueError("world observation body inventory exceeds W1 capacity")
    if tuple(sorted(observation.bodies, key=lambda item: item.body_id)) != observation.bodies:
        raise ValueError("world observation bodies are not in canonical identity order")
    body_by_id = {item.body_id: item for item in observation.bodies}
    if (
        len(body_by_id) != len(observation.bodies)
        or observation.self_body_id not in body_by_id
    ):
        raise ValueError("world observation self-body topology changed")
    for body in observation.bodies:
        body.verify()
    if not 1 <= len(observation.objects) <= MAX_WORLD_OBJECTS:
        raise ValueError("world observation object inventory exceeds W1 capacity")
    if tuple(sorted(observation.objects, key=lambda item: item.object_id)) != observation.objects:
        raise ValueError("world observation objects are not in canonical identity order")
    if len({item.object_id for item in observation.objects}) != len(observation.objects):
        raise ValueError("world observation object identities are not unique")

    held_by_body: dict[str, list[EmbodiedObject]] = {
        item.body_id: [] for item in observation.bodies
    }
    placed: list[EmbodiedObject] = []
    for item in observation.objects:
        item.verify()
        if item.held_by_body_id is None:
            if item.position is None or _region_for(
                observation.regions, item.position, item.radius_mm
            ) is None:
                raise ValueError("world observation object is outside region geometry")
            placed.append(item)
        else:
            if item.held_by_body_id not in held_by_body:
                raise ValueError("world observation object belongs to another body")
            held_by_body[item.held_by_body_id].append(item)
    occupied: list[tuple[EmbodiedBody, int]] = []
    for body in observation.bodies:
        held = held_by_body[body.body_id]
        expected_held = held[0].object_id if len(held) == 1 else None
        if len(held) > 1 or body.held_object_id != expected_held:
            raise ValueError("world observation holding relation is not reciprocal")
        carried_radius = max(
            (body.radius_mm, *(item.radius_mm for item in held))
        )
        if _region_for(
            observation.regions, body.pose.position, carried_radius
        ) is None:
            raise ValueError("world observation body is outside region geometry")
        occupied.append((body, carried_radius))
    for index, (left, left_radius) in enumerate(occupied):
        for right, right_radius in occupied[index + 1 :]:
            if (
                _region_for(
                    observation.regions, left.pose.position, left_radius
                )
                == _region_for(
                    observation.regions, right.pose.position, right_radius
                )
                and _floor_discs_overlap(
                left.pose.position,
                left_radius,
                right.pose.position,
                right_radius,
                )
            ):
                raise ValueError("world observation bodies intersect")
    for body, carried_radius in occupied:
        for item in placed:
            if (
                _region_for(
                    observation.regions, body.pose.position, carried_radius
                )
                == _region_for(
                    observation.regions, item.position, item.radius_mm
                )
                and _floor_discs_overlap(
                body.pose.position,
                carried_radius,
                item.position,
                item.radius_mm,
                )
            ):
                raise ValueError("world observation body intersects a placed object")
    for index, left in enumerate(placed):
        for right in placed[index + 1 :]:
            if (
                _region_for(
                    observation.regions, left.position, left.radius_mm
                )
                == _region_for(
                    observation.regions, right.position, right.radius_mm
                )
                and _floor_discs_overlap(
                left.position, left.radius_mm, right.position, right.radius_mm
                )
            ):
                raise ValueError("world observation placed objects intersect")
    self_body = body_by_id[observation.self_body_id]
    self_region = _region_for(
        observation.regions,
        self_body.pose.position,
        self_body.radius_mm,
    )
    if (
        self_region is None
        or observation.room_id != self_region.region_id
        or observation.room_bounds != self_region.bounds
    ):
        raise ValueError("world observation current-region projection changed")


def _verify_observation(key: bytes, observation: ObservationSnapshot) -> None:
    if not isinstance(observation, ObservationSnapshot):
        raise ValueError("embodiment sensory input must be an observation snapshot")
    _verify_world_geometry(observation)
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
        raise ValueError("action outcome requires a typed execution receipt")
    _verify_observation(key, receipt.before)
    _verify_observation(key, receipt.after)
    if receipt.after != observation:
        raise ValueError("execution receipt does not end at the supplied observation")
    if receipt.actor_body_id not in {
        item.body_id for item in observation.bodies
    }:
        raise ValueError("execution receipt belongs to another embodiment actor")
    if receipt.disposition != "applied" or receipt.reason != "applied":
        raise ValueError("action outcome requires an applied execution")
    if receipt.lifecycle[-2:] != ("geometry_validated", "applied"):
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


def _bounded_ratio(numerator: int, denominator: int, name: str) -> Fraction:
    if denominator <= 0:
        raise ValueError(f"{name} denominator is not positive")
    result = Fraction(numerator, denominator)
    if not -1 <= result <= 1:
        raise ValueError(f"{name} left its physical normalization boundary")
    return result


def _unit_interval(value: int, minimum: int, maximum: int, name: str) -> Fraction:
    return _bounded_ratio(value - minimum, maximum - minimum, name)


def _signed_interval(value: int, minimum: int, maximum: int, name: str) -> Fraction:
    return 2 * _unit_interval(value, minimum, maximum, name) - 1


def _native_signal(
    *,
    sense: PhysicalSense,
    sensor_id: str,
    substream_id: str,
    topology_index: int,
    coordinates: tuple[NativeAxisCoordinate, ...],
    values: tuple[Fraction, ...],
    source_time_start: Fraction,
    source_time_end: Fraction,
) -> NativeSensorySubstreamInput:
    if not values:
        raise ValueError("virtual sensory geometry cannot be empty")
    if any(not -1 <= value <= 1 for value in values):
        raise ValueError("virtual sensory geometry left [-1,1]")
    interval = source_time_end - source_time_start
    count = len(values)
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=sensor_id,
        substream_id=substream_id,
        topology_index=topology_index,
        coordinates=coordinates,
        physical_quantity="normalized-exact-spatial-geometry",
        physical_unit="dimensionless",
        source_times=tuple(
            source_time_start + interval * Fraction(index + 1, count + 1)
            for index in range(count)
        ),
        normalized_signal=tuple(float(value) for value in values),
        phase_turns=tuple(Fraction(index, count) for index in range(count)),
    )


def _spatial_substreams(
    observation: ObservationSnapshot,
    *,
    source_time_start: Fraction,
    source_time_end: Fraction,
) -> dict[PhysicalSense, tuple[NativeSensorySubstreamInput, ...]]:
    bounds = observation.room_bounds
    global_min_x = min(item.bounds.minimum.x for item in observation.regions)
    global_max_x = max(item.bounds.maximum.x for item in observation.regions)
    global_min_y = min(item.bounds.minimum.y for item in observation.regions)
    global_max_y = max(item.bounds.maximum.y for item in observation.regions)
    global_min_z = min(item.bounds.minimum.z for item in observation.regions)
    global_max_z = max(item.bounds.maximum.z for item in observation.regions)
    global_span_x = global_max_x - global_min_x
    global_span_y = global_max_y - global_min_y
    global_span_z = global_max_z - global_min_z
    global_planar_span = max(global_span_x, global_span_y)
    current_region = next(
        item for item in observation.regions if item.region_id == observation.room_id
    )
    body_by_id = {item.body_id: item for item in observation.bodies}
    body = body_by_id[observation.self_body_id]
    position = body.pose.position
    span_x = bounds.maximum.x - bounds.minimum.x
    span_y = bounds.maximum.y - bounds.minimum.y
    span_z = bounds.maximum.z - bounds.minimum.z
    planar_span = max(span_x, span_y)
    vertical_denominator = span_z if span_z > 0 else 1

    sight_values = (
        _unit_interval(position.x, bounds.minimum.x, bounds.maximum.x, "left wall clearance"),
        _unit_interval(bounds.maximum.x - position.x, 0, span_x, "right wall clearance"),
        _unit_interval(position.y, bounds.minimum.y, bounds.maximum.y, "near wall clearance"),
        _unit_interval(bounds.maximum.y - position.y, 0, span_y, "far wall clearance"),
        _signed_interval(position.x, bounds.minimum.x, bounds.maximum.x, "body sight x"),
        _signed_interval(position.y, bounds.minimum.y, bounds.maximum.y, "body sight y"),
        _bounded_ratio(body.pose.heading_millidegrees, 360_000, "body sight heading"),
        Fraction(1) if current_region.ceiling_height_mm is not None else Fraction(-1),
        *(
            Fraction(value, 1_000_000)
            for value in current_region.reflectance_ppm
        ),
        *(
            Fraction(value, 1_000_000)
            for value in current_region.illumination_ppm
        ),
    )
    sight: list[NativeSensorySubstreamInput] = [
        _native_signal(
            sense=PhysicalSense.SIGHT,
            sensor_id="W1-exact-geometry-sight",
            substream_id="W1-room-boundary",
            topology_index=0,
            coordinates=(
                NativeAxisCoordinate("reference-frame", "body-centered"),
                NativeAxisCoordinate("physical-domain", current_region.region_id),
            ),
            values=sight_values,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        )
    ]
    for portal in observation.portals:
        if current_region.region_id not in portal.region_ids:
            continue
        if portal.axis == "x":
            portal_values = (
                _signed_interval(
                    portal.plane_mm,
                    global_min_x,
                    global_max_x,
                    "portal plane x",
                ),
                _signed_interval(
                    portal.aperture_min_mm,
                    global_min_y,
                    global_max_y,
                    "portal aperture minimum y",
                ),
                _signed_interval(
                    portal.aperture_max_mm,
                    global_min_y,
                    global_max_y,
                    "portal aperture maximum y",
                ),
            )
        else:
            portal_values = (
                _signed_interval(
                    portal.plane_mm,
                    global_min_y,
                    global_max_y,
                    "portal plane y",
                ),
                _signed_interval(
                    portal.aperture_min_mm,
                    global_min_x,
                    global_max_x,
                    "portal aperture minimum x",
                ),
                _signed_interval(
                    portal.aperture_max_mm,
                    global_min_x,
                    global_max_x,
                    "portal aperture maximum x",
                ),
            )
        sight.append(
            _native_signal(
                sense=PhysicalSense.SIGHT,
                sensor_id="W1-exact-geometry-sight",
                substream_id=f"W1-visible-portal-{portal.portal_id}",
                topology_index=len(sight),
                coordinates=(
                    NativeAxisCoordinate("reference-frame", "body-centered"),
                    NativeAxisCoordinate("physical-portal", portal.portal_id),
                ),
                values=(
                    *portal_values,
                    _bounded_ratio(
                        portal.height_mm,
                        max(global_span_z, 1),
                        "portal height",
                    ),
                ),
                source_time_start=source_time_start,
                source_time_end=source_time_end,
            )
        )
    for other_body in observation.bodies:
        if other_body.body_id == observation.self_body_id:
            continue
        other_position = other_body.pose.position
        if not _is_visible(
            observation,
            position,
            other_position,
            other_body.radius_mm,
        ):
            continue
        values = (
            _bounded_ratio(other_position.x - position.x, global_span_x, "body relative x"),
            _bounded_ratio(other_position.y - position.y, global_span_y, "body relative y"),
            _bounded_ratio(other_position.z - position.z, max(global_span_z, 1), "body relative z"),
            _unit_interval(other_position.x, global_min_x, global_max_x, "body absolute x"),
            _unit_interval(other_position.y, global_min_y, global_max_y, "body absolute y"),
            _bounded_ratio(other_body.radius_mm, global_planar_span, "visible body radius"),
            _bounded_ratio(other_body.pose.heading_millidegrees, 360_000, "visible body heading"),
            Fraction(1) if other_body.held_object_id is not None else Fraction(-1),
        )
        sight.append(
            _native_signal(
                sense=PhysicalSense.SIGHT,
                sensor_id="W1-exact-geometry-sight",
                substream_id=f"W1-visible-body-{other_body.body_id}",
                topology_index=len(sight),
                coordinates=(
                    NativeAxisCoordinate("reference-frame", "body-centered"),
                    NativeAxisCoordinate("physical-body-track", other_body.body_id),
                ),
                values=values,
                source_time_start=source_time_start,
                source_time_end=source_time_end,
            )
        )

    for item in observation.objects:
        item_position = item.position
        if item_position is None:
            item_position = body_by_id[item.held_by_body_id].pose.position
        if item.held_by_body_id != observation.self_body_id and not _is_visible(
            observation,
            position,
            item_position,
            item.radius_mm,
        ):
            continue
        dx = item_position.x - position.x
        dy = item_position.y - position.y
        dz = item_position.z - position.z
        values = (
            _bounded_ratio(dx, global_span_x, "object relative x"),
            _bounded_ratio(dy, global_span_y, "object relative y"),
            _bounded_ratio(dz, max(global_span_z, 1), "object relative z"),
            _unit_interval(item_position.x, global_min_x, global_max_x, "object absolute x"),
            _unit_interval(item_position.y, global_min_y, global_max_y, "object absolute y"),
            _bounded_ratio(item.radius_mm, global_planar_span, "object apparent radius"),
            Fraction(1) if item.held_by_body_id is not None else Fraction(-1),
            *(Fraction(value, 1_000_000) for value in item.reflectance_ppm),
        )
        sight.append(
            _native_signal(
                sense=PhysicalSense.SIGHT,
                sensor_id="W1-exact-geometry-sight",
                substream_id=f"W1-visible-object-{item.object_id}",
                topology_index=len(sight),
                coordinates=(
                    NativeAxisCoordinate("reference-frame", "body-centered"),
                    NativeAxisCoordinate("object-identity", item.object_id),
                ),
                values=values,
                source_time_start=source_time_start,
                source_time_end=source_time_end,
            )
        )

    body_values = (
        _signed_interval(position.x, bounds.minimum.x, bounds.maximum.x, "body x"),
        _signed_interval(position.y, bounds.minimum.y, bounds.maximum.y, "body y"),
        _signed_interval(position.z, bounds.minimum.z, bounds.maximum.z, "body z")
        if span_z > 0
        else Fraction(0),
        _bounded_ratio(body.pose.heading_millidegrees, 360_000, "body heading"),
        _bounded_ratio(body.radius_mm, planar_span, "body radius"),
        _bounded_ratio(body.reach_mm, planar_span, "body reach"),
        Fraction(1) if body.held_object_id is not None else Fraction(-1),
    )
    body_input = _native_signal(
        sense=PhysicalSense.BODY,
        sensor_id="W1-exact-body-sense",
        substream_id="W1-body-pose",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate("reference-frame", "W1-room"),
            NativeAxisCoordinate("body-identity", body.body_id),
        ),
        values=body_values,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
    )

    held = next(
        (
            item
            for item in observation.objects
            if item.held_by_body_id == observation.self_body_id
        ),
        None,
    )
    touch_values = (
        Fraction(1) if held is not None else Fraction(-1),
        _bounded_ratio(held.radius_mm, planar_span, "held object radius")
        if held is not None
        else Fraction(0),
        _bounded_ratio(held.mass_grams, 1_000_000_000, "held object mass")
        if held is not None
        else Fraction(0),
        _bounded_ratio(body.radius_mm, planar_span, "contact body radius"),
        _bounded_ratio(body.reach_mm, planar_span, "contact body reach"),
    )
    touch_input = _native_signal(
        sense=PhysicalSense.TOUCH,
        sensor_id="W1-exact-contact-sense",
        substream_id="W1-body-contact",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate("reference-frame", "body-surface"),
            NativeAxisCoordinate(
                "contact-identity", held.object_id if held is not None else "no-contact"
            ),
        ),
        values=touch_values,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
    )
    return {
        PhysicalSense.SIGHT: tuple(sight),
        PhysicalSense.TOUCH: (touch_input,),
        PhysicalSense.BODY: (body_input,),
    }


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


class EmbodimentSensoryOutcomeAuthority:
    """Stateless authenticated transducer from exact W1 geometry."""

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
        receipt = _digest({"authority_hmac_sha256": signature, "payload": unsigned})
        return OutcomeObservationReceipt(
            world_observation_receipt_sha256=observation.authority_receipt_sha256,
            execution_receipt_sha256=unsigned["execution_receipt_sha256"],
            world_revision=observation.revision,
            transducer_profile=TRANSDUCER_PROFILE,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=receipt,
        )

    def verify_outcome_observation_receipt(
        self, receipt: OutcomeObservationReceipt
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
                "bound action execution receipt",
            )
        if receipt.transducer_profile != TRANSDUCER_PROFILE:
            raise ValueError("outcome observation transducer profile changed")
        if (
            isinstance(receipt.world_revision, bool)
            or not isinstance(receipt.world_revision, int)
            or not 0 <= receipt.world_revision <= MAX_WORLD_REVISION
        ):
            raise ValueError("outcome observation revision changed")
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
            raise ValueError("embodied sensory outcome requires an exact causal owner")
        if not isinstance(commit, bool):
            raise ValueError("embodied sensory outcome commit flag must be boolean")
        _verify_observation(self._key, observation)
        if execution_receipt is not None:
            _verify_execution(self._key, execution_receipt, observation)

        outcome_receipt = self._observation_receipt(observation, execution_receipt)
        self.verify_outcome_observation_receipt(outcome_receipt)
        # The revision authenticates causal order in the observation receipt;
        # it is not a sensed physical coordinate.  Native W1 waveforms use a
        # local observation interval so identical geometry yields identical
        # structural perception at different revisions.
        source_time_start = Fraction(0)
        source_time_end = Fraction(1)
        observed = _spatial_substreams(
            observation,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
        )
        states = {
            sense: (
                SenseBoundaryState.OBSERVED
                if sense in observed
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        }
        assembly_id = f"embodied-outcome-{outcome_receipt.authority_receipt_sha256}"
        built = build_six_sense_full_field(
            assembly_id=assembly_id,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            observed_substreams=observed,
            states=states,
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
        )


__all__ = (
    "EmbodiedSensoryOutcome",
    "EmbodimentSensoryOutcomeAuthority",
    "OUTCOME_OBSERVATION_SCHEMA",
    "OutcomeObservationReceipt",
    "TRANSDUCER_PROFILE",
)
