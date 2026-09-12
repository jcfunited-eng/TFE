"""Minimal native motor-to-world-to-sensor consequence bridge."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from dsf_ai_service.glew_runtime.native_resident_organism import (
    exact_native_root_translation_proprioceptive_source,
    exact_native_root_yaw_proprioceptive_source,
    exact_native_yaw_trajectory,
)
from dsf_ai_service.guala_physical_sensorium import PhysicalSensorium
from dsf_ai_service.guala_physical_return import PhysicalReturnSource, RETURN_TIMES
from dsf_ai_service.guala_world_sensorium import (
    BODY_INTERVAL_MICROSECONDS,
    passive_body_consequence_sensorium,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    AdvancePhysicalTimeCommand,
    ENVIRONMENT_PORT_ID,
    GraspContactCommand,
    MoveCommand,
    PORT_ID,
    PositionMM,
    PoseMM,
    PreparedActionExecution,
    ReleaseHeldObjectCommand,
    encode_command,
)


@dataclass(frozen=True, slots=True)
class PreparedMotorConsequence:
    prepared_world: PreparedActionExecution
    sensorium: PhysicalSensorium
    sources: tuple[PhysicalReturnSource, ...]
    vestibular: tuple[int, int] | None
    requested_action: str
    refusal_reason: str | None
    requested_root_motion: tuple[int, int, int]
    actual_root_motion: tuple[int, int, int]


def _receipt(value: object) -> str:
    body = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _self_body(snapshot: Any) -> Any:
    matches = tuple(
        body for body in snapshot.bodies if body.body_id == snapshot.self_body_id
    )
    if len(matches) != 1:
        raise RuntimeError("physical world lost its unique organism body")
    return matches[0]


def _signed_root_motion(evidence: Any) -> tuple[int, int, int]:
    yaw = 0
    for _lineage, _topology, carriers, direction in tuple(
        evidence.root_yaw_unit_recruitments
    ):
        if direction not in {"negative", "positive"}:
            raise RuntimeError("native root-yaw discharge lost typed direction")
        yaw += int(carriers) if direction == "positive" else -int(carriers)
    x = 0
    y = 0
    for _lineage, _topology, carriers, axis, direction in tuple(
        evidence.root_translation_unit_recruitments
    ):
        if axis not in {"x", "y"} or direction not in {"negative", "positive"}:
            raise RuntimeError("native root-translation discharge lost typed anatomy")
        signed = int(carriers) if direction == "positive" else -int(carriers)
        if axis == "x":
            x += signed
        else:
            y += signed
    if any(not -(1 << 31) <= value < (1 << 31) for value in (yaw, x, y)):
        raise RuntimeError("native root discharge exceeded signed 32-bit anatomy")
    return yaw, x, y


def _new_body_discharge(consequence: object) -> bool:
    if not isinstance(consequence, tuple) or len(consequence) != 11:
        raise RuntimeError("native body consequence changed its exact shape")
    toward_minimum = int(consequence[6])
    toward_maximum = int(consequence[7])
    stalled = int(consequence[10])
    if min(toward_minimum, toward_maximum, stalled) < 0:
        raise RuntimeError("native body consequence carried negative carriers")
    if stalled > abs(toward_maximum - toward_minimum):
        raise RuntimeError("native body consequence stalled beyond net discharge")
    return bool(toward_minimum or toward_maximum)


def _active_grips(evidence: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    displacement = {"left_grip_aperture": 0, "right_grip_aperture": 0}
    for consequence in tuple(evidence.articulated_body_consequences):
        if _new_body_discharge(consequence) and consequence[1] in displacement:
            signed = int(consequence[5])
            toward_minimum = int(consequence[6])
            toward_maximum = int(consequence[7])
            stalled = int(consequence[10])
            admitted = abs(toward_maximum - toward_minimum) - stalled
            same_direction = admitted > 0 and (
                (signed < 0 and toward_minimum > toward_maximum)
                or (signed > 0 and toward_maximum > toward_minimum)
            )
            if same_direction:
                displacement[consequence[1]] += signed
    closing = tuple(sorted(axis for axis, value in displacement.items() if value < 0))
    opening = tuple(sorted(axis for axis, value in displacement.items() if value > 0))
    return closing, opening


def _body_sources(evidence: Any) -> tuple[PhysicalReturnSource, ...]:
    bodies = tuple(bytes(value) for value in evidence.body_proprioceptive_sources)
    extents = tuple(evidence.body_proprioceptive_source_extents)
    if len(bodies) != len(extents) or len(bodies) > 1:
        raise RuntimeError("one native interval lost its sparse body source")
    sources = []
    for body, extent in zip(bodies, extents, strict=True):
        if not isinstance(extent, tuple) or len(extent) != 5:
            raise RuntimeError("native body source extent changed shape")
        _tick, ports, samples, occurrences, frames = extent
        sources.append(PhysicalReturnSource(
            body, (ports, samples, occurrences, frames),
            ((1, 1000),) * occurrences,
        ))
    return tuple(sources)

def _actual_root_motion(execution: ActionExecutionReceipt) -> tuple[int, int, int]:
    before = _self_body(execution.before).pose
    after = _self_body(execution.after).pose
    yaw = after.heading_millidegrees - before.heading_millidegrees
    while yaw > 180_000:
        yaw -= 360_000
    while yaw < -180_000:
        yaw += 360_000
    return yaw, after.position.x - before.position.x, after.position.y - before.position.y


def prepare_motor_consequence(
    *,
    world: Any,
    evidence: Any,
    predecessor_state_sha256: str,
    predecessor_body_axes: tuple[Any, ...],
    successor_body_axes: tuple[Any, ...],
) -> PreparedMotorConsequence:
    """Prepare exactly one truthful world action and its complete return."""

    requested_yaw, requested_x, requested_y = _signed_root_motion(evidence)
    closing, opening = _active_grips(evidence)
    before = world.observation_snapshot()
    before_body = _self_body(before)
    if requested_yaw or requested_x or requested_y:
        heading, _trajectory = exact_native_yaw_trajectory(
            predecessor_heading_millidegrees=before_body.pose.heading_millidegrees,
            signed_displacement_millidegrees=requested_yaw,
            duration_microseconds=BODY_INTERVAL_MICROSECONDS,
        )
        command = MoveCommand(
            target_pose=PoseMM(
                PositionMM(
                    before_body.pose.position.x + requested_x,
                    before_body.pose.position.y + requested_y,
                    before_body.pose.position.z,
                ),
                heading,
            ),
            duration_microseconds=BODY_INTERVAL_MICROSECONDS,
        )
        port_id = PORT_ID
        requested_action = "move"
    elif closing and not opening:
        command = GraspContactCommand(BODY_INTERVAL_MICROSECONDS)
        port_id = PORT_ID
        requested_action = "grasp"
    elif len(opening) == 1 and not closing and before_body.held_object_id is not None:
        command = ReleaseHeldObjectCommand(BODY_INTERVAL_MICROSECONDS)
        port_id = PORT_ID
        requested_action = "release"
    else:
        command = AdvancePhysicalTimeCommand(BODY_INTERVAL_MICROSECONDS)
        port_id = ENVIRONMENT_PORT_ID
        requested_action = "body"

    intent = _receipt({
        "body_consequences": tuple(evidence.articulated_body_consequences),
        "causal_transition_sha256": evidence.causal_transition_sha256,
        "duration_microseconds": BODY_INTERVAL_MICROSECONDS,
        "predecessor_state_sha256": predecessor_state_sha256,
        "requested_action": requested_action,
        "requested_root_motion": (requested_yaw, requested_x, requested_y),
        "schema": "guala.lean_native_motor_world_intent.v1",
        "world_revision": before.revision,
        "world_state_before_sha256": before.state_sha256,
    })
    prepared = world.prepare_port_command(
        port_id=port_id,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=intent,
        expected_revision=before.revision,
    )
    refusal_reason = None
    if isinstance(prepared, ActionExecutionReceipt):
        refusal_reason = prepared.reason
        fallback_intent = _receipt({
            "refused_action_receipt_sha256": prepared.authority_receipt_sha256,
            "schema": "guala.lean_native_motor_blocked_return.v1",
            "world_revision": before.revision,
        })
        prepared = world.prepare_port_command(
            port_id=ENVIRONMENT_PORT_ID,
            command_payload=encode_command(
                AdvancePhysicalTimeCommand(BODY_INTERVAL_MICROSECONDS)
            ),
            causal_intent_receipt_sha256=fallback_intent,
            expected_revision=before.revision,
        )
    if not isinstance(prepared, PreparedActionExecution):
        raise RuntimeError("native motor world consequence lost prepared custody")

    execution = prepared.execution_receipt
    actual_yaw, actual_x, actual_y = _actual_root_motion(execution)
    sensorium = passive_body_consequence_sensorium(
        world=world,
        execution=execution,
        predecessor_body_axes=predecessor_body_axes,
        successor_body_axes=successor_body_axes,
        source_times=RETURN_TIMES,
    )
    consequence_sources = list(_body_sources(evidence))
    source_tick = int(evidence.organism_tick)
    if actual_yaw:
        source = exact_native_root_yaw_proprioceptive_source(
            source_tick=source_tick,
            signed_displacement_millidegrees=actual_yaw,
        )
        consequence_sources.append(PhysicalReturnSource.capture(
            source, [(1, 1000)] * source.occurrence_count,
        ))
    if actual_x or actual_y:
        source = exact_native_root_translation_proprioceptive_source(
            source_tick=source_tick,
            signed_x_millimetres=actual_x,
            signed_y_millimetres=actual_y,
        )
        consequence_sources.append(PhysicalReturnSource.capture(
            source, [(1, 1000)] * source.occurrence_count,
        ))
    predecessor_axes = {axis[1]: axis[3] for axis in predecessor_body_axes}
    successor_axes = {axis[1]: axis[3] for axis in successor_body_axes}
    if predecessor_axes.keys() != successor_axes.keys():
        raise RuntimeError("native action changed articulated body anatomy")
    total_yaw = actual_yaw + successor_axes["neck_yaw"] - predecessor_axes["neck_yaw"]
    vestibular = None
    if total_yaw:
        predecessor_heading = (
            _self_body(execution.before).pose.heading_millidegrees
            + predecessor_axes["neck_yaw"]
        ) % 360_000
        expected_heading = (
            _self_body(execution.after).pose.heading_millidegrees
            + successor_axes["neck_yaw"]
        ) % 360_000
        successor_heading, trajectory = exact_native_yaw_trajectory(
            predecessor_heading_millidegrees=predecessor_heading,
            signed_displacement_millidegrees=total_yaw,
            duration_microseconds=BODY_INTERVAL_MICROSECONDS,
        )
        if successor_heading != expected_heading:
            raise RuntimeError("native motor return lost vestibular geometry")
        if len(trajectory) != 1:
            raise RuntimeError("one body interval lost its single vestibular step")
        vestibular = predecessor_heading, trajectory[0]

    return PreparedMotorConsequence(
        prepared_world=prepared,
        sensorium=sensorium,
        sources=tuple(consequence_sources),
        vestibular=vestibular,
        requested_action=requested_action,
        refusal_reason=refusal_reason,
        requested_root_motion=(requested_yaw, requested_x, requested_y),
        actual_root_motion=(actual_yaw, actual_x, actual_y),
    )
