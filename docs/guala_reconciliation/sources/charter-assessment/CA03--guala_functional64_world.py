"""Explicit new-law commissioning and exact ordinary restore of the lived home.

These functions operate only on private authorities restored from supplied
canonical bytes. The actor's live world is never mutated here.
"""
from __future__ import annotations

from dataclasses import replace
import struct
from typing import Any

from guala_core import Functional64Core
from .guala_home_world import home_world_authority, world_authority_key
from .substrate.bounded_home_thermal_physics import commission_paid_thermal_state
from .substrate.compound_motor_material import MAX_MOTOR_COMMAND_BYTES, MotorContactState
from .substrate.paid_thermal_energy import POWER_RESIDUE_DENOMINATOR
from .substrate.world_material_transport import MaterialTransportState


def _restore_private(identity: str, encoded: bytes, *, compound: bool) -> Any:
    if type(identity) is not str or not identity or type(encoded) is not bytes or not encoded:
        raise ValueError("private world requires actual identity and canonical bytes")
    # Declare geometry, then restore directly. home_world_authority(encoded=...)
    # also performs legacy custody reconciliation; ordinary decoding must not.
    authority = home_world_authority(identity=identity)
    if compound:
        authority._max_command_bytes = MAX_MOTOR_COMMAND_BYTES
    authority.restore_encoded(encoded, allow_physical_return_migration=False,
                              allow_authenticated_physical_manifest_migration=False)
    if authority.encoded_snapshot() != encoded:
        raise ValueError("private ordinary world restore changed original bytes")
    return authority


def thermal_source_identities(world: Any) -> tuple[tuple[bytes, int], ...]:
    """Original anatomy digest/node/power; this creates no new energy source."""
    anatomy = world._thermal_anatomy
    digest = bytes.fromhex(anatomy.receipt_sha256)
    if len(digest) != 32:
        raise ValueError("actual thermal anatomy receipt changed")
    return tuple((b"GL64TH01" + digest + struct.pack("<QQ", source.node_index,
                                                  source.power_microwatts),
                  source.node_index) for source in anatomy.power_sources)


def verify_world_current(authority: Any, core: Functional64Core) -> None:
    """Bind the restored private world after its geometry decoded the core.

    This is a read-only check, also required before constructing the physical
    loop. Ordinary world restore alone never asserts that the pair is mounted.
    """
    if type(core) is not Functional64Core:
        raise TypeError("world requires the actual native current")
    expected_key = world_authority_key(core.identity).encode("utf-8")
    if authority._key != expected_key or authority._thermal_key != expected_key:
        raise ValueError("native identity and authenticated world identity differ")
    world = authority._state.world
    body = next(body for body in world.bodies if body.body_id == world.self_body_id)
    motor = body.motor_contact
    axes = core.body_axes
    if len(axes) != 45 or any(row[0] != index for index, row in enumerate(axes)):
        raise ValueError("native body changed its complete declared axes")
    for ordinal, name in ((14, "jaw_opening"), (23, "left_grip_aperture"),
                          (28, "right_grip_aperture")):
        if axes[ordinal][1] != name or axes[ordinal][2] != "micrometre":
            raise ValueError("actual native/world contact geometry changed")
    if (motor is None or motor.source_millisecond != core.source_millisecond
            or (motor.left_grip_micrometres, motor.right_grip_micrometres,
                motor.jaw_micrometres) != (axes[23][3], axes[28][3], axes[14][3])):
        raise ValueError("current world contact and native body are not one chronological pair")
    if (world.material_transport is None
            or authority._thermal_state.power_residue_denominator != POWER_RESIDUE_DENOMINATOR):
        raise ValueError("current world lacks its retained material and paid thermal state")
    if tuple(identity for identity, _node in thermal_source_identities(authority)) != core.thermal_source_identities:
        raise ValueError("native funding and actual world thermal anatomy differ")


def restore_home_world(*, identity: str, encoded: bytes) -> Any:
    """Decode unchanged world before core geometry; verify_world_current follows.

    This explicit order removes the world/core restore cycle without genesis,
    commissioning, replenishment, migration or an implicit binding claim.
    """
    return _restore_private(identity, encoded, compound=True)


def commission_home_world(*, original_world: bytes, core: Functional64Core) -> Any:
    """One zero-elapsed format/anatomy installation on a private original copy.

    The root canonical envelope retains original_world byte-for-byte once,
    including its old latest thermal receipt. The actual original pair and
    complete native capture are authenticated by the commissioning caller.
    """
    if type(core) is not Functional64Core:
        raise TypeError("world commissioning requires the actual commissioned native current")
    authority = _restore_private(core.identity, original_world, compound=False)
    world = authority._state.world
    if (authority.pending_physical_return is not None
            or authority._prepared_action_execution is not None
            or authority._committing_prepared_action_execution is not None
            or authority._visibility_prepared_action is not None
            or authority._pending_thermal is not None
            or authority._committed_thermal_tail is not None):
        raise ValueError("original world retains physical experience requiring delivery")
    if world.material_transport is not None or any(b.motor_contact is not None for b in world.bodies):
        raise ValueError("world commissioning cannot run twice or reinterpret a mixed current")
    axes = core.body_axes
    if len(axes) != 45 or any(row[0] != index for index, row in enumerate(axes)):
        raise ValueError("commissioned body lacks its complete actual axes")
    index = next(i for i, body in enumerate(world.bodies) if body.body_id == world.self_body_id)
    body = world.bodies[index]
    oral = (body.active_contact.object_id if body.active_contact is not None
            and body.active_contact.kind == "oral" else None)
    motor = MotorContactState(
        axes[23][3], axes[28][3], axes[14][3], 0,
        body.held_object_id is not None, oral, oral is None, core.source_millisecond,
    )
    motor.verify()
    bodies = list(world.bodies)
    bodies[index] = replace(body, motor_contact=motor)
    successor_world = replace(world, revision=world.revision + 1, bodies=tuple(bodies),
                              material_transport=MaterialTransportState.commission(world))
    authority._validate_world(successor_world)
    observation = authority._observation_for(successor_world)
    authority._verify_retained_execution_order(authority._state.recent_applied_receipts, observation)
    thermal = commission_paid_thermal_state(authority._thermal_state)
    thermal.verify(authority._thermal_anatomy.conductive_edges(observation.room_id),
                   authority._thermal_anatomy.bath_edges, authority._thermal_anatomy.power_sources)
    # Every replacement belongs only to this private restored copy. Original
    # world bytes retain the retired latest receipt under the outer envelope.
    authority._state = replace(authority._state, world=successor_world, observation=observation)
    authority._thermal_state = thermal
    authority._thermal_world_revision = observation.revision
    authority._thermal_world_observation_receipt_sha256 = observation.authority_receipt_sha256
    authority._latest_thermal_transition = None
    authority._max_command_bytes = MAX_MOTOR_COMMAND_BYTES
    verify_world_current(authority, core)
    authority.encoded_snapshot()
    return authority
