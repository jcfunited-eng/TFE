"""Truthful persistent-world sampling for the lean Guala runtime."""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from typing import Any

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import PhysicalSense
from dsf_ai_service.guala_physical_sensorium import PhysicalSensorium
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
    RETINA_TOTAL_RECEPTOR_COUNT,
    physical_receptor_substreams,
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


def retinal_carriage(body_axes: tuple[Any, ...]) -> tuple[int, Fraction]:
    """Read exact neck heading and eyelid transmission from native anatomy."""

    neck = tuple(axis for axis in body_axes if axis[1] == "neck_yaw")
    if len(neck) != 1:
        raise RuntimeError("native body has no unique neck-yaw axis")
    heading = neck[0][3]
    if (
        isinstance(heading, bool)
        or not isinstance(heading, int)
        or not -180_000 <= heading <= 180_000
    ):
        raise RuntimeError("native neck yaw left retinal geometry")
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
    return heading, Fraction(admitted, possible)


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


def _retinal_endpoints(
    streams: tuple[Any, ...],
) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...]]:
    totals = (
        [Fraction(0)] * RETINA_TOTAL_RECEPTOR_COUNT,
        [Fraction(0)] * RETINA_TOTAL_RECEPTOR_COUNT,
    )
    counts = [0] * RETINA_TOTAL_RECEPTOR_COUNT
    for stream in streams:
        cell = stream.topology_index // OPTICAL_BANDS
        if 0 <= cell < RETINA_TOTAL_RECEPTOR_COUNT:
            if len(stream.normalized_signal) != 2:
                raise RuntimeError("world retinal endpoint count changed")
            for endpoint, value in zip(totals, stream.normalized_signal, strict=True):
                endpoint[cell] += Fraction(value).limit_denominator(1_000_000)
            counts[cell] += 1
    if any(count != OPTICAL_BANDS for count in counts):
        raise RuntimeError("world lost the six-band retinal field")
    return tuple(
        tuple(
            total[index] / counts[index]
            for index in range(RETINA_TOTAL_RECEPTOR_COUNT)
        )
        for total in totals
    )


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
) -> PhysicalSensorium:
    """Sample one current world/body state into every mounted receptor."""

    heading, transmission = retinal_carriage(body_axes)
    physical = physical_receptor_substreams(
        snapshot,
        snapshot,
        causal_transition=False,
        before_retinal_heading_offset_millidegrees=heading,
        after_retinal_heading_offset_millidegrees=heading,
        source_time_start=Fraction(0),
        source_time_end=Fraction(1, 4),
    )
    retina = tuple(value * transmission for value in _retinal_endpoints(physical[PhysicalSense.SIGHT])[1])
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
        retina=retina,
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


def passive_body_consequence_sensorium(
    *,
    world: Any,
    execution: ActionExecutionReceipt,
    predecessor_body_axes: tuple[Any, ...],
    successor_body_axes: tuple[Any, ...],
    source_times: tuple[Fraction, ...],
) -> PhysicalSensorium:
    """Build the exact world/body consequence of one passive 1 ms return."""

    action_end = Fraction(BODY_INTERVAL_MICROSECONDS, 1_000_000)
    before_heading, before_transmission = retinal_carriage(predecessor_body_axes)
    after_heading, after_transmission = retinal_carriage(successor_body_axes)
    physical = physical_receptor_substreams(
        execution.before,
        execution.after,
        causal_transition=True,
        before_retinal_heading_offset_millidegrees=before_heading,
        after_retinal_heading_offset_millidegrees=after_heading,
        source_time_start=Fraction(0),
        source_time_end=action_end,
    )
    before_retina, after_retina = _retinal_endpoints(physical[PhysicalSense.SIGHT])
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
        retina=retina,
        legacy_ears=((Fraction(0),) * len(source_times),) * 2,
        cochleae=((Fraction(0),) * len(source_times),) * 32,
        touch=touch,
        smell=tuple(step(before, after) for before, after in zip(before_smell, after_smell, strict=True)),
        taste=tuple(step(before, after) for before, after in zip(before_taste, after_taste, strict=True)),
        displacement=displacement_trajectories,
        articulation=((Fraction(0),) * len(source_times),) * 4,
        thermal=tuple(step(before, after) for before, after in zip(before_thermal, after_thermal, strict=True)),
    )
