"""Truthful persistent-world sampling for the lean Guala runtime."""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from typing import Any

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import PhysicalSense
from dsf_ai_service.guala_physical_sensorium import PhysicalSensorium, RETINAL_PORTS
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    AdvancePhysicalTimeCommand,
    ENVIRONMENT_PORT_ID,
    PreparedActionExecution,
    encode_command,
)
from dsf_ai_service.substrate.w1_coupled_material_sensory_physics import (
    material_receptor_substreams,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    OPTICAL_BANDS,
    physical_contact_substreams,
    retinal_irradiance_field,
)


PASSIVE_INTERVAL_MICROSECONDS = 250_000
BODY_INTERVAL_MICROSECONDS = 1_000
THERMAL_MIN_MILLIKELVIN = 273_000
THERMAL_MAX_MILLIKELVIN = 323_000
WORLD_DISPLACEMENT_SPAN_MM = 4_000
WORLD_TURN_SPAN_MILLIDEGREES = 180_000


def _receipt(value: object) -> str:
    body = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def retinal_carriage(body_axes: tuple[Any, ...]) -> tuple[int, int, Fraction]:
    """Read actual mono retinal aim (neck and eyes together; the eyes turn in the
    head within their declared range, and the carriage never pitches past straight
    down or up) and eyelid transmission from native anatomy."""

    angles: list[int] = []
    for name, bound in (("neck_yaw", 180_000), ("neck_pitch", 90_000), ("left_eye_yaw", 90_000), ("left_eye_pitch", 90_000)):
        matches = tuple(axis for axis in body_axes if axis[1] == name)
        if not matches and name.startswith("left_eye_"):
            angles.append(0)   # a body without eye axes carries its retina on the neck alone
            continue
        if len(matches) != 1 or matches[0][2] != "millidegree":
            raise RuntimeError(f"native body has no unique typed {name}")
        position, minimum, maximum = matches[0][3], matches[0][4], matches[0][6]
        if (
            any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in (position, minimum, maximum)
            )
            or not -bound <= minimum < maximum <= bound
            or not minimum <= position <= maximum
        ):
            raise RuntimeError(f"native {name} left retinal geometry")
        angles.append(position)
    apertures: list[tuple[int, int, int]] = []
    for name in ("left_eyelid_aperture", "right_eyelid_aperture"):
        matches = tuple(axis for axis in body_axes if axis[1] == name)
        if len(matches) != 1 or matches[0][2] != "micrometre":
            raise RuntimeError(f"native body has no unique typed {name}")
        position, minimum, maximum = matches[0][3], matches[0][4], matches[0][6]
        if (
            any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in (position, minimum, maximum)
            )
            or minimum >= maximum
            or not minimum <= position <= maximum
        ):
            raise RuntimeError(f"native {name} left its physical anatomy")
        apertures.append((position, minimum, maximum))
    admitted = sum(position - minimum for position, minimum, _ in apertures)
    possible = sum(maximum - minimum for _, minimum, maximum in apertures)
    heading = angles[0] + angles[2]
    pitch = max(-90_000, min(90_000, angles[1] + angles[3]))
    return heading, pitch, Fraction(admitted, possible)


def _prepare_world_interval(
    world: Any,
    *,
    duration_microseconds: int,
    schema: str,
    native_transition_sha256: str | None = None,
) -> PreparedActionExecution:
    before = world.observation_snapshot()
    intent = _receipt({
        "duration_microseconds": duration_microseconds,
        "native_transition_sha256": native_transition_sha256,
        "schema": schema,
        "world_revision": before.revision,
        "world_state_before_sha256": before.state_sha256,
    })
    prepared = world.prepare_port_command(
        port_id=ENVIRONMENT_PORT_ID,
        command_payload=encode_command(AdvancePhysicalTimeCommand(duration_microseconds)),
        causal_intent_receipt_sha256=intent,
        expected_revision=before.revision,
    )
    if isinstance(prepared, ActionExecutionReceipt):
        raise RuntimeError("physical world interval was refused: " + prepared.reason)
    if not isinstance(prepared, PreparedActionExecution):
        raise RuntimeError("physical world interval lost prepared custody")
    return prepared


def prepare_passive_world_interval(world: Any) -> PreparedActionExecution:
    return _prepare_world_interval(
        world,
        duration_microseconds=PASSIVE_INTERVAL_MICROSECONDS,
        schema="guala.lean_passive_world_interval.v1",
    )


def prepare_passive_body_interval(
    world: Any,
    *,
    native_transition_sha256: str,
) -> PreparedActionExecution:
    return _prepare_world_interval(
        world,
        duration_microseconds=BODY_INTERVAL_MICROSECONDS,
        schema="guala.lean_passive_body_consequence.v1",
        native_transition_sha256=native_transition_sha256,
    )


RetinalField = tuple[tuple[Fraction, ...], ...]

_LUM_DENOMINATOR = 1530  # 255 * OPTICAL_BANDS
_LUM_LOOKUP = tuple(Fraction(s, _LUM_DENOMINATOR) for s in range(256 * OPTICAL_BANDS))


def _retinal_luminance(pixels: RetinalField) -> tuple[Fraction, ...]:
    """Preserve exact conversion order, reusing identical bands only this call."""

    converted: dict[float, Fraction] = {}

    def rational(band: Fraction) -> Fraction:
        value = float(band)
        retained = converted.get(value)
        if retained is None:
            retained = Fraction(value).limit_denominator(1_000_000)
            converted[value] = retained
        return retained

    out: list[Fraction] = []
    for p in pixels:
        # Fast path for eight-bit fractions (denominator == 255):
        if (
            p[0]._denominator == 255
            and p[1]._denominator == 255
            and p[2]._denominator == 255
            and p[3]._denominator == 255
            and p[4]._denominator == 255
            and p[5]._denominator == 255
        ):
            if p[0] == p[1] == p[2] == p[3] == p[4] == p[5]:
                out.append(p[0])
            else:
                num_sum = (
                    p[0]._numerator
                    + p[1]._numerator
                    + p[2]._numerator
                    + p[3]._numerator
                    + p[4]._numerator
                    + p[5]._numerator
                )
                out.append(_LUM_LOOKUP[num_sum])
            continue

        if p[0] == p[1] == p[2] == p[3] == p[4] == p[5]:
            out.append(rational(p[0]))
        else:
            out.append(
                (
                    rational(p[0])
                    + rational(p[1])
                    + rational(p[2])
                    + rational(p[3])
                    + rational(p[4])
                    + rational(p[5])
                )
                / OPTICAL_BANDS
            )
    return tuple(out)


def _retinal_rgb(pixels: RetinalField) -> tuple[tuple[Fraction, Fraction, Fraction], ...]:
    """The eye's colour sensation: 3 channels (RGB) per site.
    Red = mean of bands 0 and 1
    Green = mean of bands 2 and 3
    Blue = mean of bands 4 and 5
    """
    out: list[tuple[Fraction, Fraction, Fraction]] = []
    for p in pixels:
        r = p[0] if p[0] == p[1] else (p[0] + p[1]) / 2
        g = p[2] if p[2] == p[3] else (p[2] + p[3]) / 2
        b = p[4] if p[4] == p[5] else (p[4] + p[5]) / 2
        out.append((r, g, b))
    return tuple(out)


def _sun_of(world: Any) -> tuple[float, float, float, int] | None:
    """The sun as the world authority knows it now (its direction and the sky's light),
    for the world eye's direct light; None for a world without a sun, or at night."""

    read = getattr(world, "solar_sun", None)
    return None if read is None else read()


def passive_receptor_capture(
    *,
    snapshot: Any,
    body_axes: tuple[Any, ...],
    include_world_sight: bool = True,
    sun: tuple[float, float, float, int] | None = None,
) -> tuple[RetinalField, dict[PhysicalSense, tuple[Any, ...]], Fraction]:
    """Capture current contacts and, when consumed, all six optical bands."""

    if not isinstance(include_world_sight, bool):
        raise TypeError("world sight selection must be boolean")
    heading, pitch, transmission = retinal_carriage(body_axes)
    pixels = (
        retinal_irradiance_field(
            snapshot, retinal_heading_offset_millidegrees=heading,
            retinal_pitch_offset_millidegrees=pitch, include_focal=True,
            sun=sun,
        )
        if include_world_sight else ()
    )
    physical = physical_contact_substreams(
        snapshot, snapshot, causal_transition=False,
        source_time_start=Fraction(0), source_time_end=Fraction(1, 4),
    )
    return pixels, physical, transmission


def _palmar_endpoints(streams: tuple[Any, ...]) -> tuple[Fraction, Fraction]:
    matches = tuple(
        stream
        for stream in streams
        if stream.sensor_id == "W1-body-surface-receptors"
        and stream.substream_id == "palmar-contact"
    )
    if len(matches) != 1 or len(matches[0].normalized_signal) != 2:
        raise RuntimeError("world lost its unique palmar contact")
    values = tuple(
        Fraction(value).limit_denominator(1_000_000)
        for value in matches[0].normalized_signal
    )
    if any(value not in {Fraction(0), Fraction(1)} for value in values):
        raise RuntimeError("palmar contact left its exact binary boundary")
    return values


def _chemical_endpoints(
    streams: dict[PhysicalSense, tuple[Any, ...]],
    sense: PhysicalSense,
    width: int,
) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...]]:
    endpoints = ([Fraction(0)] * width, [Fraction(0)] * width)
    for stream in streams.get(sense, ()):
        if not 0 <= stream.topology_index < width:
            raise RuntimeError("world chemical receptor left mounted anatomy")
        for endpoint, raw in zip(
            endpoints,
            (stream.normalized_signal[0], stream.normalized_signal[-1]),
            strict=True,
        ):
            value = Fraction(raw).limit_denominator(1_000_000)
            if not Fraction(0) <= value <= Fraction(1):
                raise RuntimeError("world chemical receptor left physical bounds")
            endpoint[stream.topology_index] = value
    return tuple(endpoints[0]), tuple(endpoints[1])


def _normalize_temperatures(
    temperatures: tuple[Fraction | int, Fraction | int],
) -> tuple[Fraction, Fraction]:
    span = THERMAL_MAX_MILLIKELVIN - THERMAL_MIN_MILLIKELVIN
    normalized = tuple(
        (temperature - THERMAL_MIN_MILLIKELVIN) / span
        for temperature in temperatures
    )
    if any(not Fraction(0) <= value <= Fraction(1) for value in normalized):
        raise RuntimeError("body temperature left mounted receptor interval")
    return normalized


def _thermal_current(world: Any) -> tuple[Fraction, Fraction]:
    observation = world.thermal_observation()
    by_id = dict(zip(observation.node_ids, observation.temperatures_millikelvin, strict=True))
    try:
        values = (by_id["body:cutaneous-shell"], by_id["body:core"])
    except KeyError as error:
        raise RuntimeError("world lost cutaneous or core thermal anatomy") from error
    return _normalize_temperatures(values)


def _thermal_endpoints(
    world: Any,
    execution: ActionExecutionReceipt,
) -> tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]]:
    observation = world.thermal_endpoints_for_execution(execution)
    before = dict(zip(observation.node_ids, observation.before_temperatures_millikelvin, strict=True))
    after = dict(zip(observation.node_ids, observation.after_temperatures_millikelvin, strict=True))
    try:
        return (
            _normalize_temperatures((before["body:cutaneous-shell"], before["body:core"])),
            _normalize_temperatures((after["body:cutaneous-shell"], after["body:core"])),
        )
    except KeyError as error:
        raise RuntimeError("world consequence lost thermal endpoints") from error


def passive_sensorium(
    *,
    world: Any,
    snapshot: Any,
    body_axes: tuple[Any, ...],
    frame_count: int,
    pending_execution: ActionExecutionReceipt | None = None,
    receptor_capture: tuple[
        RetinalField, dict[PhysicalSense, tuple[Any, ...]], Fraction
    ] | None = None,
    include_world_sight: bool = True,
) -> PhysicalSensorium:
    """Sample current world/body inputs; omit only explicitly replaced sight."""

    if not isinstance(include_world_sight, bool):
        raise TypeError("world sight selection must be boolean")
    if not include_world_sight and receptor_capture is not None:
        raise ValueError("omitted world sight cannot reuse a retinal capture")
    pixels, physical, transmission = (
        passive_receptor_capture(
            snapshot=snapshot, body_axes=body_axes,
            include_world_sight=include_world_sight, sun=_sun_of(world),
        )
        if receptor_capture is None
        else receptor_capture
    )
    retina = tuple(value * transmission for value in _retinal_luminance(pixels))
    palmar = _palmar_endpoints(physical[PhysicalSense.TOUCH])[1]
    chemicals = material_receptor_substreams(
        world_authority=world,
        before=snapshot,
        after=snapshot,
        source_time_start=Fraction(0),
        source_time_end=Fraction(1, 4),
    )
    thermal = (
        _thermal_current(world)
        if pending_execution is None
        else _thermal_endpoints(world, pending_execution)[1]
    )
    return PhysicalSensorium.constant(
        frame_count=frame_count,
        retina=retina[:RETINAL_PORTS],
        retina_focal=retina[RETINAL_PORTS:],
        legacy_ears=(Fraction(0),) * 2,
        cochleae=(Fraction(0),) * 32,
        touch=(Fraction(0),) * 27 + (palmar,),
        smell=_chemical_endpoints(chemicals, PhysicalSense.SMELL, 8)[1],
        taste=_chemical_endpoints(chemicals, PhysicalSense.TASTE, 5)[1],
        displacement=(Fraction(0),) * 4,
        articulation=(Fraction(0),) * 4,
        thermal=thermal,
    )


def consequence_source_times(
    passive_times: tuple[Fraction, ...],
) -> tuple[Fraction, ...]:
    action_end = Fraction(BODY_INTERVAL_MICROSECONDS, 1_000_000)
    return tuple(sorted(set(passive_times) | {action_end}))


def _world_displacement(before: Any, after: Any) -> tuple[Fraction, ...]:
    def pose(snapshot: Any) -> Any:
        return next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id).pose

    start, end = pose(before), pose(after)
    turn = end.heading_millidegrees - start.heading_millidegrees
    while turn > WORLD_TURN_SPAN_MILLIDEGREES:
        turn -= 2 * WORLD_TURN_SPAN_MILLIDEGREES
    while turn < -WORLD_TURN_SPAN_MILLIDEGREES:
        turn += 2 * WORLD_TURN_SPAN_MILLIDEGREES
    values = (
        Fraction(end.position.x - start.position.x, WORLD_DISPLACEMENT_SPAN_MM),
        Fraction(end.position.y - start.position.y, WORLD_DISPLACEMENT_SPAN_MM),
        Fraction(end.position.z - start.position.z, WORLD_DISPLACEMENT_SPAN_MM),
        Fraction(turn, WORLD_TURN_SPAN_MILLIDEGREES),
    )
    if any(not Fraction(-1) <= value <= Fraction(1) for value in values):
        raise RuntimeError("world displacement left mounted receptor span")
    return values


def body_consequence_receptor_capture(
    *,
    execution: ActionExecutionReceipt,
    predecessor_body_axes: tuple[Any, ...],
    successor_body_axes: tuple[Any, ...],
    sun: tuple[float, float, float, int] | None = None,
) -> tuple[
    RetinalField, RetinalField, dict[PhysicalSense, tuple[Any, ...]], Fraction, Fraction
]:
    """Render the exact before/after fields across one body/world consequence."""

    action_end = Fraction(BODY_INTERVAL_MICROSECONDS, 1_000_000)
    before_heading, before_pitch, before_transmission = retinal_carriage(predecessor_body_axes)
    after_heading, after_pitch, after_transmission = retinal_carriage(successor_body_axes)
    before_pixels = retinal_irradiance_field(
        execution.before, retinal_heading_offset_millidegrees=before_heading,
        retinal_pitch_offset_millidegrees=before_pitch, include_focal=True, sun=sun,
    )
    after_pixels = retinal_irradiance_field(
        execution.after, retinal_heading_offset_millidegrees=after_heading,
        retinal_pitch_offset_millidegrees=after_pitch, include_focal=True, sun=sun,
    )
    physical = physical_contact_substreams(
        execution.before, execution.after, causal_transition=True,
        source_time_start=Fraction(0), source_time_end=action_end,
    )
    return before_pixels, after_pixels, physical, before_transmission, after_transmission


def passive_body_consequence_sensorium(
    *,
    world: Any,
    execution: ActionExecutionReceipt,
    predecessor_body_axes: tuple[Any, ...],
    successor_body_axes: tuple[Any, ...],
    source_times: tuple[Fraction, ...],
    receptor_capture: tuple[
        RetinalField, RetinalField, dict[PhysicalSense, tuple[Any, ...]], Fraction, Fraction
    ] | None = None,
) -> PhysicalSensorium:
    """Build the exact world/body consequence of one passive 1 ms return."""

    action_end = Fraction(BODY_INTERVAL_MICROSECONDS, 1_000_000)
    before_pixels, after_pixels, physical, before_transmission, after_transmission = (
        body_consequence_receptor_capture(
            execution=execution,
            predecessor_body_axes=predecessor_body_axes,
            successor_body_axes=successor_body_axes,
            sun=_sun_of(world),
        )
        if receptor_capture is None
        else receptor_capture
    )
    before_retina = _retinal_luminance(before_pixels)
    after_retina = _retinal_luminance(after_pixels)
    before_palmar, after_palmar = _palmar_endpoints(physical[PhysicalSense.TOUCH])
    chemicals = material_receptor_substreams(
        world_authority=world,
        before=execution.before,
        after=execution.after,
        source_time_start=Fraction(0),
        source_time_end=action_end,
    )
    before_smell, after_smell = _chemical_endpoints(chemicals, PhysicalSense.SMELL, 8)
    before_taste, after_taste = _chemical_endpoints(chemicals, PhysicalSense.TASTE, 5)
    before_thermal, after_thermal = _thermal_endpoints(world, execution)
    displacement = _world_displacement(execution.before, execution.after)

    def step(before: Fraction, after: Fraction) -> tuple[Fraction, ...]:
        return tuple(before if time < action_end else after for time in source_times)

    retina = tuple(
        step(before * before_transmission, after * after_transmission)
        for before, after in zip(before_retina, after_retina, strict=True)
    )
    touch = (
        *((Fraction(0),) * len(source_times) for _ in range(27)),
        step(before_palmar, after_palmar),
    )
    displacement_trajectories = tuple(
        tuple(value if time <= action_end else Fraction(0) for time in source_times)
        for value in displacement
    )
    return PhysicalSensorium(
        retina=retina[:RETINAL_PORTS],
        retina_focal=retina[RETINAL_PORTS:],
        legacy_ears=((Fraction(0),) * len(source_times),) * 2,
        cochleae=((Fraction(0),) * len(source_times),) * 32,
        touch=touch,
        smell=tuple(step(before, after) for before, after in zip(before_smell, after_smell, strict=True)),
        taste=tuple(step(before, after) for before, after in zip(before_taste, after_taste, strict=True)),
        displacement=displacement_trajectories,
        articulation=((Fraction(0),) * len(source_times),) * 4,
        thermal=tuple(step(before, after) for before, after in zip(before_thermal, after_thermal, strict=True)),
    )


__all__ = (
    "BODY_INTERVAL_MICROSECONDS",
    "PASSIVE_INTERVAL_MICROSECONDS",
    "RetinalField",
    "body_consequence_receptor_capture",
    "consequence_source_times",
    "passive_body_consequence_sensorium",
    "passive_receptor_capture",
    "passive_sensorium",
    "prepare_passive_body_interval",
    "prepare_passive_world_interval",
    "retinal_carriage",
    "_retinal_luminance",
    "_retinal_rgb",
    "_sun_of",
)
