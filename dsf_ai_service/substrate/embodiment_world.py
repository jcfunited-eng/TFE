"""Deterministic bounded authority for Guala's first multi-region world.

This module owns opaque physical regions, portals, bodies, and objects.  One
body is the substrate's self-body.  Every body has a
separate physical command port; those ports are control topology, never names,
language meanings, or sensory identity.
does not choose actions or assign meaning to them.  It executes canonical typed
commands arriving as opaque bytes on actor-specific embodiment ports, using exact integer
geometry.  Each accepted transition is atomic and produces authenticated
before/after observations and an authenticated execution receipt.

There is deliberately no random movement, script, object-to-verb lookup,
language lookup, chi identity, DSF projection, or dependency on the retired
semantic-environment mechanisms here.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, replace
from typing import Mapping, Sequence


PORT_ID = "guala.embodiment.w1"
SECOND_BODY_PORT_ID = "guala.embodiment.w1.body-2"

COMMAND_SCHEMA = "guala.embodiment.command.v1"
OBSERVATION_SCHEMA = "guala.embodiment.observation.v3"
EXECUTION_SCHEMA = "guala.embodiment.execution.v3"
STATE_SCHEMA = "guala.embodiment.state.v3"
ENVELOPE_SCHEMA = "guala.embodiment.state.hmac.v3"
MIGRATION_SCHEMA = "guala.embodiment.topology_migration.v2"

V2_OBSERVATION_SCHEMA = "guala.embodiment.observation.v2"
V2_EXECUTION_SCHEMA = "guala.embodiment.execution.v2"
V2_STATE_SCHEMA = "guala.embodiment.state.v2"
V2_ENVELOPE_SCHEMA = "guala.embodiment.state.hmac.v2"
V2_MIGRATION_SCHEMA = "guala.embodiment.migration.v1"

LEGACY_OBSERVATION_SCHEMA = "guala.embodiment.observation.v1"
LEGACY_STATE_SCHEMA = "guala.embodiment.state.v1"
LEGACY_ENVELOPE_SCHEMA = "guala.embodiment.state.hmac.v1"

OBSERVATION_DOMAIN = b"guala-embodiment-observation-v3\0"
EXECUTION_DOMAIN = b"guala-embodiment-execution-v3\0"
STATE_DOMAIN = b"guala-embodiment-state-v3\0"
MIGRATION_DOMAIN = b"guala-embodiment-topology-migration-v2\0"

V2_OBSERVATION_DOMAIN = b"guala-embodiment-observation-v2\0"
V2_EXECUTION_DOMAIN = b"guala-embodiment-execution-v2\0"
V2_STATE_DOMAIN = b"guala-embodiment-state-v2\0"

LEGACY_OBSERVATION_DOMAIN = b"guala-embodiment-observation-v1\0"
LEGACY_STATE_DOMAIN = b"guala-embodiment-state-v1\0"

DEFAULT_MAX_REGIONS = 4
DEFAULT_MAX_PORTALS = 6
DEFAULT_MAX_OBJECTS = 16
DEFAULT_MAX_BODIES = 4
DEFAULT_RECEIPT_CAPACITY = 16
DEFAULT_MAX_COMMAND_BYTES = 4096
DEFAULT_MAX_ENCODED_STATE_BYTES = 2 * 1024 * 1024
LEGACY_MAX_ENCODED_STATE_BYTES = 8 * 1024 * 1024
MAX_IDENTIFIER_BYTES = 256
MAX_REVISION = (1 << 63) - 1
OPTICAL_BANDS = 6
MAX_PHYSICAL_PPM = 1_000_000
VOCAL_SAMPLE_RATE_HZ = 16_000
MIN_VOCAL_SAMPLE_COUNT = 160
MAX_VOCAL_SAMPLE_COUNT = 2_048


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


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _authority_key(value: object) -> bytes:
    if isinstance(value, str):
        if len(value) > 4096:
            raise ValueError("embodiment authority key must be bounded and nonempty")
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        if len(value) > 4096:
            raise ValueError("embodiment authority key must be bounded and nonempty")
        result = bytes(value)
    else:
        raise ValueError("embodiment authority key must be bytes or text")
    if not result or len(result) > 4096:
        raise ValueError("embodiment authority key must be bounded and nonempty")
    return result


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES
    ):
        raise ValueError(f"{name} must be a bounded canonical identifier")
    return value


def _bounded_integer(
    value: object,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"{name} is outside its exact integer boundary")
    return value


def _sha256_identity(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(item not in "0123456789abcdef" for item in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _sign(key: bytes, domain: bytes, payload: Mapping[str, object]) -> str:
    return hmac.new(key, domain + _canonical(payload), hashlib.sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class PositionMM:
    x: int
    y: int
    z: int = 0

    def verify(self) -> None:
        _bounded_integer(self.x, "position x", minimum=-(1 << 31), maximum=(1 << 31) - 1)
        _bounded_integer(self.y, "position y", minimum=-(1 << 31), maximum=(1 << 31) - 1)
        _bounded_integer(self.z, "position z", minimum=-(1 << 31), maximum=(1 << 31) - 1)

    def as_record(self) -> dict[str, int]:
        self.verify()
        return {"x_mm": self.x, "y_mm": self.y, "z_mm": self.z}


@dataclass(frozen=True, slots=True)
class PoseMM:
    position: PositionMM
    heading_millidegrees: int

    def verify(self) -> None:
        self.position.verify()
        _bounded_integer(
            self.heading_millidegrees,
            "body heading",
            minimum=0,
            maximum=359_999,
        )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "heading_millidegrees": self.heading_millidegrees,
            "position": self.position.as_record(),
        }


@dataclass(frozen=True, slots=True)
class RoomBoundsMM:
    minimum: PositionMM
    maximum: PositionMM

    def verify(self) -> None:
        self.minimum.verify()
        self.maximum.verify()
        if not (
            self.minimum.x < self.maximum.x
            and self.minimum.y < self.maximum.y
            and self.minimum.z <= self.maximum.z
        ):
            raise ValueError("room bounds are not ordered")

    def contains_floor_disc(self, position: PositionMM, radius_mm: int) -> bool:
        return (
            position.z == self.minimum.z
            and self.minimum.x + radius_mm <= position.x <= self.maximum.x - radius_mm
            and self.minimum.y + radius_mm <= position.y <= self.maximum.y - radius_mm
        )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "maximum": self.maximum.as_record(),
            "minimum": self.minimum.as_record(),
        }


def _physical_bands(value: object, name: str) -> tuple[int, ...]:
    if (
        not isinstance(value, tuple)
        or len(value) != OPTICAL_BANDS
        or any(
            isinstance(item, bool)
            or not isinstance(item, int)
            or not 0 <= item <= MAX_PHYSICAL_PPM
            for item in value
        )
    ):
        raise ValueError(f"{name} must contain six bounded integer bands")
    return value


@dataclass(frozen=True, slots=True)
class PhysicalRegion:
    region_id: str
    bounds: RoomBoundsMM
    ceiling_height_mm: int | None
    reflectance_ppm: tuple[int, ...]
    illumination_ppm: tuple[int, ...]

    def verify(self) -> None:
        _identifier(self.region_id, "physical region id")
        self.bounds.verify()
        if self.ceiling_height_mm is not None:
            _bounded_integer(
                self.ceiling_height_mm,
                "physical ceiling height",
                minimum=1,
                maximum=(1 << 31) - 1,
            )
            if self.ceiling_height_mm > self.bounds.maximum.z:
                raise ValueError("physical ceiling exceeds region volume")
        _physical_bands(self.reflectance_ppm, "region reflectance")
        _physical_bands(self.illumination_ppm, "region illumination")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "bounds": self.bounds.as_record(),
            "ceiling_height_mm": self.ceiling_height_mm,
            "illumination_ppm": list(self.illumination_ppm),
            "reflectance_ppm": list(self.reflectance_ppm),
            "region_id": self.region_id,
        }


@dataclass(frozen=True, slots=True)
class PhysicalPortal:
    portal_id: str
    region_ids: tuple[str, str]
    axis: str
    plane_mm: int
    aperture_min_mm: int
    aperture_max_mm: int
    height_mm: int

    def verify(self) -> None:
        _identifier(self.portal_id, "physical portal id")
        if (
            not isinstance(self.region_ids, tuple)
            or len(self.region_ids) != 2
            or self.region_ids != tuple(sorted(self.region_ids))
            or len(set(self.region_ids)) != 2
        ):
            raise ValueError("portal region pair is not canonical")
        for value in self.region_ids:
            _identifier(value, "portal region id")
        if self.axis not in {"x", "y"}:
            raise ValueError("portal axis must be x or y")
        for value, name in (
            (self.plane_mm, "portal plane"),
            (self.aperture_min_mm, "portal aperture minimum"),
            (self.aperture_max_mm, "portal aperture maximum"),
            (self.height_mm, "portal height"),
        ):
            _bounded_integer(
                value, name, minimum=-(1 << 31), maximum=(1 << 31) - 1
            )
        if (
            self.aperture_min_mm >= self.aperture_max_mm
            or self.height_mm <= 0
        ):
            raise ValueError("portal aperture is not physically ordered")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "aperture_max_mm": self.aperture_max_mm,
            "aperture_min_mm": self.aperture_min_mm,
            "axis": self.axis,
            "height_mm": self.height_mm,
            "plane_mm": self.plane_mm,
            "portal_id": self.portal_id,
            "region_ids": list(self.region_ids),
        }


@dataclass(frozen=True, slots=True)
class EmbodiedBody:
    body_id: str
    pose: PoseMM
    radius_mm: int
    reach_mm: int
    held_object_id: str | None = None

    def verify(self) -> None:
        _identifier(self.body_id, "body id")
        self.pose.verify()
        _bounded_integer(self.radius_mm, "body radius", minimum=1, maximum=1_000_000)
        _bounded_integer(self.reach_mm, "body reach", minimum=1, maximum=1_000_000)
        if self.held_object_id is not None:
            _identifier(self.held_object_id, "held object id")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "body_id": self.body_id,
            "held_object_id": self.held_object_id,
            "pose": self.pose.as_record(),
            "radius_mm": self.radius_mm,
            "reach_mm": self.reach_mm,
        }


@dataclass(frozen=True, slots=True)
class EmbodiedObject:
    object_id: str
    radius_mm: int
    mass_grams: int
    position: PositionMM | None
    held_by_body_id: str | None = None
    reflectance_ppm: tuple[int, ...] = (
        500_000, 500_000, 500_000, 500_000, 500_000, 500_000
    )

    def verify(self) -> None:
        _identifier(self.object_id, "object id")
        _bounded_integer(self.radius_mm, "object radius", minimum=1, maximum=1_000_000)
        _bounded_integer(self.mass_grams, "object mass", minimum=1, maximum=1_000_000_000)
        if (self.position is None) == (self.held_by_body_id is None):
            raise ValueError("object must be either placed or held")
        if self.position is not None:
            self.position.verify()
        if self.held_by_body_id is not None:
            _identifier(self.held_by_body_id, "holding body id")
        _physical_bands(self.reflectance_ppm, "object reflectance")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "held_by_body_id": self.held_by_body_id,
            "mass_grams": self.mass_grams,
            "object_id": self.object_id,
            "position": self.position.as_record() if self.position is not None else None,
            "radius_mm": self.radius_mm,
            "reflectance_ppm": list(self.reflectance_ppm),
        }


@dataclass(frozen=True, slots=True)
class EmbodimentPort:
    port_id: str
    actor_body_id: str

    def verify(self) -> None:
        _identifier(self.port_id, "embodiment port id")
        _identifier(self.actor_body_id, "embodiment port actor body id")

    def as_record(self) -> dict[str, str]:
        self.verify()
        return {
            "actor_body_id": self.actor_body_id,
            "port_id": self.port_id,
        }


@dataclass(frozen=True, slots=True)
class MoveCommand:
    target_pose: PoseMM


@dataclass(frozen=True, slots=True)
class PickCommand:
    object_id: str


@dataclass(frozen=True, slots=True)
class PlaceCommand:
    object_id: str
    target_position: PositionMM


@dataclass(frozen=True, slots=True)
class VocalizeCommand:
    """One bounded physical pressure actuation by the addressed body."""

    epoch_commitment_sha256: str
    sequence: int
    source_sample_start: int
    pcm_sha256: str
    sample_count: int


EmbodimentCommand = MoveCommand | PickCommand | PlaceCommand | VocalizeCommand


def command_record(command: EmbodimentCommand) -> dict[str, object]:
    if isinstance(command, MoveCommand):
        command.target_pose.verify()
        return {
            "operation": "move",
            "schema": COMMAND_SCHEMA,
            "target_pose": command.target_pose.as_record(),
        }
    if isinstance(command, PickCommand):
        return {
            "object_id": _identifier(command.object_id, "pick object id"),
            "operation": "pick",
            "schema": COMMAND_SCHEMA,
        }
    if isinstance(command, PlaceCommand):
        command.target_position.verify()
        return {
            "object_id": _identifier(command.object_id, "place object id"),
            "operation": "place",
            "schema": COMMAND_SCHEMA,
            "target_position": command.target_position.as_record(),
        }
    if isinstance(command, VocalizeCommand):
        sample_count = _bounded_integer(
            command.sample_count,
            "vocal sample count",
            minimum=MIN_VOCAL_SAMPLE_COUNT,
            maximum=MAX_VOCAL_SAMPLE_COUNT,
        )
        return {
            "epoch_commitment_sha256": _sha256_identity(
                command.epoch_commitment_sha256,
                "vocal epoch commitment",
            ),
            "operation": "vocalize",
            "pcm_sha256": _sha256_identity(
                command.pcm_sha256, "vocal pressure identity"
            ),
            "sample_count": sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "sequence": _bounded_integer(
                command.sequence,
                "vocal sequence",
                minimum=0,
                maximum=MAX_REVISION,
            ),
            "schema": COMMAND_SCHEMA,
            "source_sample_start": _bounded_integer(
                command.source_sample_start,
                "vocal source sample start",
                minimum=0,
                maximum=MAX_REVISION - sample_count,
            ),
        }
    raise ValueError("unsupported embodiment command type")


def encode_command(command: EmbodimentCommand) -> bytes:
    """Encode one typed command into the exact opaque port payload."""

    return _canonical(command_record(command))


def _position_from(value: object, name: str) -> PositionMM:
    if not isinstance(value, Mapping) or set(value) != {"x_mm", "y_mm", "z_mm"}:
        raise ValueError(f"{name} fields changed")
    result = PositionMM(x=value.get("x_mm"), y=value.get("y_mm"), z=value.get("z_mm"))
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError(f"{name} is not canonical")
    return result


def _pose_from(value: object, name: str) -> PoseMM:
    if not isinstance(value, Mapping) or set(value) != {"heading_millidegrees", "position"}:
        raise ValueError(f"{name} fields changed")
    result = PoseMM(
        position=_position_from(value.get("position"), f"{name} position"),
        heading_millidegrees=value.get("heading_millidegrees"),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError(f"{name} is not canonical")
    return result


def decode_command(payload: bytes, *, max_command_bytes: int = DEFAULT_MAX_COMMAND_BYTES) -> EmbodimentCommand:
    """Decode only the canonical typed command language owned by this port."""

    if not isinstance(payload, bytes) or not payload or len(payload) > max_command_bytes:
        raise ValueError("embodiment command exceeds its exact byte boundary")
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("embodiment command is not canonical JSON") from error
    if not isinstance(decoded, Mapping) or decoded.get("schema") != COMMAND_SCHEMA:
        raise ValueError("embodiment command schema changed")
    operation = decoded.get("operation")
    if operation == "move" and set(decoded) == {"operation", "schema", "target_pose"}:
        result: EmbodimentCommand = MoveCommand(_pose_from(decoded.get("target_pose"), "move target pose"))
    elif operation == "pick" and set(decoded) == {"object_id", "operation", "schema"}:
        result = PickCommand(_identifier(decoded.get("object_id"), "pick object id"))
    elif operation == "place" and set(decoded) == {"object_id", "operation", "schema", "target_position"}:
        result = PlaceCommand(
            _identifier(decoded.get("object_id"), "place object id"),
            _position_from(decoded.get("target_position"), "place target position"),
        )
    elif operation == "vocalize" and set(decoded) == {
        "epoch_commitment_sha256", "operation", "pcm_sha256", "sample_count",
        "sample_rate_hz", "schema", "sequence", "source_sample_start"
    }:
        if decoded.get("sample_rate_hz") != VOCAL_SAMPLE_RATE_HZ:
            raise ValueError("vocal sample rate changed")
        result = VocalizeCommand(
            epoch_commitment_sha256=_sha256_identity(
                decoded.get("epoch_commitment_sha256"),
                "vocal epoch commitment",
            ),
            sequence=_bounded_integer(
                decoded.get("sequence"),
                "vocal sequence",
                minimum=0,
                maximum=MAX_REVISION,
            ),
            source_sample_start=_bounded_integer(
                decoded.get("source_sample_start"),
                "vocal source sample start",
                minimum=0,
                maximum=MAX_REVISION - _bounded_integer(
                    decoded.get("sample_count"),
                    "vocal sample count",
                    minimum=MIN_VOCAL_SAMPLE_COUNT,
                    maximum=MAX_VOCAL_SAMPLE_COUNT,
                ),
            ),
            pcm_sha256=_sha256_identity(
                decoded.get("pcm_sha256"), "vocal pressure identity"
            ),
            sample_count=_bounded_integer(
                decoded.get("sample_count"),
                "vocal sample count",
                minimum=MIN_VOCAL_SAMPLE_COUNT,
                maximum=MAX_VOCAL_SAMPLE_COUNT,
            ),
        )
    else:
        raise ValueError("embodiment command operation or fields changed")
    if encode_command(result) != payload:
        raise ValueError("embodiment command bytes are not canonical")
    return result


@dataclass(frozen=True, slots=True)
class _WorldState:
    revision: int
    room_id: str
    room_bounds: RoomBoundsMM
    regions: tuple[PhysicalRegion, ...]
    portals: tuple[PhysicalPortal, ...]
    self_body_id: str
    bodies: tuple[EmbodiedBody, ...]
    objects: tuple[EmbodiedObject, ...]

    def as_record(self) -> dict[str, object]:
        return {
            "bodies": [item.as_record() for item in self.bodies],
            "objects": [item.as_record() for item in self.objects],
            "revision": self.revision,
            "room_bounds": self.room_bounds.as_record(),
            "room_id": self.room_id,
            "regions": [item.as_record() for item in self.regions],
            "portals": [item.as_record() for item in self.portals],
            "self_body_id": self.self_body_id,
        }


@dataclass(frozen=True, slots=True)
class ObservationSnapshot:
    revision: int
    room_id: str
    room_bounds: RoomBoundsMM
    regions: tuple[PhysicalRegion, ...]
    portals: tuple[PhysicalPortal, ...]
    self_body_id: str
    bodies: tuple[EmbodiedBody, ...]
    objects: tuple[EmbodiedObject, ...]
    state_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "bodies": [item.as_record() for item in self.bodies],
            "objects": [item.as_record() for item in self.objects],
            "revision": self.revision,
            "room_bounds": self.room_bounds.as_record(),
            "room_id": self.room_id,
            "regions": [item.as_record() for item in self.regions],
            "portals": [item.as_record() for item in self.portals],
            "schema": OBSERVATION_SCHEMA,
            "self_body_id": self.self_body_id,
            "state_sha256": self.state_sha256,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class ActionExecutionReceipt:
    port_id: str
    actor_body_id: str | None
    causal_intent_receipt_sha256: str
    command_sha256: str
    expected_revision: int
    observed_revision: int
    disposition: str
    reason: str
    lifecycle: tuple[str, ...]
    before: ObservationSnapshot
    after: ObservationSnapshot
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "actor_body_id": self.actor_body_id,
            "after": self.after.as_record(),
            "before": self.before.as_record(),
            "causal_intent_receipt_sha256": self.causal_intent_receipt_sha256,
            "command_sha256": self.command_sha256,
            "disposition": self.disposition,
            "expected_revision": self.expected_revision,
            "lifecycle": list(self.lifecycle),
            "observed_revision": self.observed_revision,
            "port_id": self.port_id,
            "reason": self.reason,
            "schema": EXECUTION_SCHEMA,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class _AuthorityState:
    world: _WorldState
    recent_applied_receipts: tuple[ActionExecutionReceipt, ...]
    migration_receipt: "WorldMigrationReceipt | None" = None


@dataclass(frozen=True, slots=True)
class WorldMigrationReceipt:
    prior_envelope_sha256: str
    prior_observation_receipt_sha256: str
    resulting_observation_receipt_sha256: str
    prior_revision: int
    resulting_revision: int
    parent_migration_receipt_sha256: str | None
    manifest_sha256: str
    prior_topology_sha256: str
    resulting_topology_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "manifest_sha256": self.manifest_sha256,
            "parent_migration_receipt_sha256": (
                self.parent_migration_receipt_sha256
            ),
            "prior_envelope_sha256": self.prior_envelope_sha256,
            "prior_observation_receipt_sha256": (
                self.prior_observation_receipt_sha256
            ),
            "prior_revision": self.prior_revision,
            "resulting_observation_receipt_sha256": (
                self.resulting_observation_receipt_sha256
            ),
            "resulting_revision": self.resulting_revision,
            "prior_topology_sha256": self.prior_topology_sha256,
            "resulting_topology_sha256": self.resulting_topology_sha256,
            "schema": MIGRATION_SCHEMA,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


def _distance_squared(left: PositionMM, right: PositionMM) -> int:
    return (left.x - right.x) ** 2 + (left.y - right.y) ** 2 + (left.z - right.z) ** 2


def _floor_discs_overlap(left: PositionMM, left_radius: int, right: PositionMM, right_radius: int) -> bool:
    distance = (left.x - right.x) ** 2 + (left.y - right.y) ** 2
    return distance < (left_radius + right_radius) ** 2


def _straight_path_intersects_disc(
    start: PositionMM,
    finish: PositionMM,
    obstacle: PositionMM,
    combined_radius: int,
) -> bool:
    """Exact line-segment/disc intersection with integer arithmetic."""

    dx = finish.x - start.x
    dy = finish.y - start.y
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return _floor_discs_overlap(start, 0, obstacle, combined_radius)
    ox = obstacle.x - start.x
    oy = obstacle.y - start.y
    projection = ox * dx + oy * dy
    if projection <= 0:
        return ox * ox + oy * oy < combined_radius * combined_radius
    if projection >= length_squared:
        ex = obstacle.x - finish.x
        ey = obstacle.y - finish.y
        return ex * ex + ey * ey < combined_radius * combined_radius
    cross = ox * dy - oy * dx
    return cross * cross < combined_radius * combined_radius * length_squared


def _room_from(value: object) -> RoomBoundsMM:
    if not isinstance(value, Mapping) or set(value) != {"maximum", "minimum"}:
        raise ValueError("room bounds fields changed")
    result = RoomBoundsMM(
        minimum=_position_from(value.get("minimum"), "room minimum"),
        maximum=_position_from(value.get("maximum"), "room maximum"),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("room bounds are not canonical")
    return result


def _body_from(value: object) -> EmbodiedBody:
    expected = {"body_id", "held_object_id", "pose", "radius_mm", "reach_mm"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("body fields changed")
    result = EmbodiedBody(
        body_id=value.get("body_id"),
        held_object_id=value.get("held_object_id"),
        pose=_pose_from(value.get("pose"), "body pose"),
        radius_mm=value.get("radius_mm"),
        reach_mm=value.get("reach_mm"),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("body record is not canonical")
    return result


def _object_from(value: object) -> EmbodiedObject:
    expected = {
        "held_by_body_id", "mass_grams", "object_id", "position",
        "radius_mm", "reflectance_ppm"
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("object fields changed")
    raw_position = value.get("position")
    result = EmbodiedObject(
        object_id=value.get("object_id"),
        radius_mm=value.get("radius_mm"),
        mass_grams=value.get("mass_grams"),
        position=_position_from(raw_position, "object position") if raw_position is not None else None,
        held_by_body_id=value.get("held_by_body_id"),
        reflectance_ppm=_physical_bands(
            tuple(value.get("reflectance_ppm"))
            if isinstance(value.get("reflectance_ppm"), list)
            else value.get("reflectance_ppm"),
            "object reflectance",
        ),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("object record is not canonical")
    return result


def _legacy_object_from(value: object) -> EmbodiedObject:
    expected = {
        "held_by_body_id", "mass_grams", "object_id", "position", "radius_mm"
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("legacy object fields changed")
    raw_position = value.get("position")
    result = EmbodiedObject(
        object_id=value.get("object_id"),
        radius_mm=value.get("radius_mm"),
        mass_grams=value.get("mass_grams"),
        position=(
            _position_from(raw_position, "legacy object position")
            if raw_position is not None else None
        ),
        held_by_body_id=value.get("held_by_body_id"),
    )
    result.verify()
    legacy_record = result.as_record()
    del legacy_record["reflectance_ppm"]
    if legacy_record != dict(value):
        raise ValueError("legacy object record is not canonical")
    return result


def _region_from(value: object) -> PhysicalRegion:
    expected = {
        "bounds", "ceiling_height_mm", "illumination_ppm",
        "reflectance_ppm", "region_id"
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("physical region fields changed")
    result = PhysicalRegion(
        region_id=value.get("region_id"),
        bounds=_room_from(value.get("bounds")),
        ceiling_height_mm=value.get("ceiling_height_mm"),
        reflectance_ppm=_physical_bands(
            tuple(value.get("reflectance_ppm"))
            if isinstance(value.get("reflectance_ppm"), list)
            else value.get("reflectance_ppm"),
            "region reflectance",
        ),
        illumination_ppm=_physical_bands(
            tuple(value.get("illumination_ppm"))
            if isinstance(value.get("illumination_ppm"), list)
            else value.get("illumination_ppm"),
            "region illumination",
        ),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("physical region record is not canonical")
    return result


def _portal_from(value: object) -> PhysicalPortal:
    expected = {
        "aperture_max_mm", "aperture_min_mm", "axis", "height_mm",
        "plane_mm", "portal_id", "region_ids"
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("physical portal fields changed")
    raw_regions = value.get("region_ids")
    result = PhysicalPortal(
        portal_id=value.get("portal_id"),
        region_ids=tuple(raw_regions) if isinstance(raw_regions, list) else raw_regions,
        axis=value.get("axis"),
        plane_mm=value.get("plane_mm"),
        aperture_min_mm=value.get("aperture_min_mm"),
        aperture_max_mm=value.get("aperture_max_mm"),
        height_mm=value.get("height_mm"),
    )
    result.verify()
    if result.as_record() != dict(value):
        raise ValueError("physical portal record is not canonical")
    return result


def _default_regions() -> tuple[PhysicalRegion, ...]:
    return (
        PhysicalRegion(
            "W1-region-A",
            RoomBoundsMM(PositionMM(0, 0, 0), PositionMM(5000, 5000, 3000)),
            3000,
            (620000, 600000, 580000, 560000, 540000, 520000),
            (700000, 680000, 650000, 620000, 590000, 560000),
        ),
        PhysicalRegion(
            "W1-region-B",
            RoomBoundsMM(PositionMM(5000, 0, 0), PositionMM(15000, 5000, 3000)),
            None,
            (310000, 360000, 420000, 480000, 540000, 600000),
            (820000, 800000, 770000, 730000, 690000, 650000),
        ),
        PhysicalRegion(
            "W1-region-C",
            RoomBoundsMM(PositionMM(15000, 0, 0), PositionMM(20000, 5000, 3000)),
            3000,
            (470000, 500000, 530000, 560000, 590000, 620000),
            (640000, 630000, 620000, 610000, 600000, 590000),
        ),
    )


def _default_portals() -> tuple[PhysicalPortal, ...]:
    return (
        PhysicalPortal(
            "W1-portal-1", ("W1-region-A", "W1-region-B"),
            "x", 5000, 2000, 3000, 2200,
        ),
        PhysicalPortal(
            "W1-portal-2", ("W1-region-B", "W1-region-C"),
            "x", 15000, 2000, 3000, 2200,
        ),
    )


def _manifest_objects() -> tuple[EmbodiedObject, ...]:
    return (
        EmbodiedObject("W1-object-1", 100, 500, PositionMM(1500, 1000, 0), reflectance_ppm=(700000, 300000, 180000, 120000, 90000, 70000)),
        EmbodiedObject("W1-object-2", 80, 240, PositionMM(2500, 1000, 0), reflectance_ppm=(150000, 650000, 240000, 120000, 90000, 60000)),
        EmbodiedObject("W1-object-3", 120, 900, PositionMM(3500, 1000, 0), reflectance_ppm=(120000, 220000, 720000, 300000, 120000, 80000)),
        EmbodiedObject("W1-object-4", 90, 360, PositionMM(8000, 1000, 0), reflectance_ppm=(680000, 600000, 180000, 100000, 80000, 60000)),
        EmbodiedObject("W1-object-5", 140, 1400, PositionMM(12000, 3500, 0), reflectance_ppm=(240000, 180000, 620000, 520000, 180000, 90000)),
        EmbodiedObject("W1-object-6", 110, 720, PositionMM(17500, 1000, 0), reflectance_ppm=(520000, 200000, 180000, 650000, 300000, 120000)),
    )


class EmbodimentWorldAuthority:
    """Atomic authority for one exact W1 multi-body/object world."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        room_id: str = "W1",
        room_bounds: RoomBoundsMM | None = None,
        self_body_id: str = "guala-body-1",
        bodies: Sequence[EmbodiedBody] | None = None,
        actor_ports: Sequence[EmbodimentPort] | None = None,
        initial_objects: Sequence[EmbodiedObject] | None = None,
        regions: Sequence[PhysicalRegion] | None = None,
        portals: Sequence[PhysicalPortal] | None = None,
        max_regions: int = DEFAULT_MAX_REGIONS,
        max_portals: int = DEFAULT_MAX_PORTALS,
        max_bodies: int = DEFAULT_MAX_BODIES,
        max_objects: int = DEFAULT_MAX_OBJECTS,
        receipt_capacity: int = DEFAULT_RECEIPT_CAPACITY,
        max_command_bytes: int = DEFAULT_MAX_COMMAND_BYTES,
        max_encoded_state_bytes: int = DEFAULT_MAX_ENCODED_STATE_BYTES,
    ) -> None:
        self._key = _authority_key(authority_key)
        self._max_regions = _bounded_integer(
            max_regions, "region capacity", minimum=3, maximum=4
        )
        self._max_portals = _bounded_integer(
            max_portals, "portal capacity", minimum=2, maximum=6
        )
        self._max_bodies = _bounded_integer(
            max_bodies, "body capacity", minimum=2, maximum=DEFAULT_MAX_BODIES
        )
        self._max_objects = _bounded_integer(
            max_objects,
            "object capacity",
            minimum=1,
            maximum=DEFAULT_MAX_OBJECTS,
        )
        self._receipt_capacity = _bounded_integer(
            receipt_capacity,
            "receipt capacity",
            minimum=1,
            maximum=DEFAULT_RECEIPT_CAPACITY,
        )
        self._max_command_bytes = _bounded_integer(
            max_command_bytes,
            "command byte capacity",
            minimum=64,
            maximum=DEFAULT_MAX_COMMAND_BYTES,
        )
        self._max_encoded_state_bytes = _bounded_integer(
            max_encoded_state_bytes,
            "encoded state byte capacity",
            minimum=4096,
            maximum=DEFAULT_MAX_ENCODED_STATE_BYTES,
        )
        if regions is None:
            physical_regions = _default_regions()
        else:
            if (
                not isinstance(regions, Sequence)
                or isinstance(regions, (str, bytes, bytearray))
                or not 3 <= len(regions) <= self._max_regions
                or any(not isinstance(item, PhysicalRegion) for item in regions)
            ):
                raise ValueError("physical region inventory exceeds capacity")
            physical_regions = tuple(regions)
        physical_regions = tuple(
            sorted(physical_regions, key=lambda item: item.region_id)
        )
        if portals is None:
            physical_portals = _default_portals()
        else:
            if (
                not isinstance(portals, Sequence)
                or isinstance(portals, (str, bytes, bytearray))
                or not 2 <= len(portals) <= self._max_portals
                or any(not isinstance(item, PhysicalPortal) for item in portals)
            ):
                raise ValueError("physical portal inventory exceeds capacity")
            physical_portals = tuple(portals)
        physical_portals = tuple(
            sorted(physical_portals, key=lambda item: item.portal_id)
        )
        bounds = physical_regions[0].bounds
        canonical_self_body_id = _identifier(self_body_id, "self body id")
        if bodies is None:
            embodied_bodies = (
                EmbodiedBody(
                    body_id=canonical_self_body_id,
                    pose=PoseMM(PositionMM(1000, 1000, 0), 0),
                    radius_mm=250,
                    reach_mm=800,
                ),
                EmbodiedBody(
                    body_id="w1-body-2",
                    pose=PoseMM(
                        PositionMM(
                            bounds.maximum.x - 250,
                            bounds.maximum.y - 250,
                            bounds.minimum.z,
                        ),
                        180_000,
                    ),
                    radius_mm=250,
                    reach_mm=800,
                ),
            )
        else:
            if (
                not isinstance(bodies, Sequence)
                or isinstance(bodies, (str, bytes, bytearray))
                or not 2 <= len(bodies) <= self._max_bodies
                or any(not isinstance(item, EmbodiedBody) for item in bodies)
            ):
                raise ValueError("world body inventory exceeds its exact capacity")
            embodied_bodies = tuple(bodies)
        embodied_bodies = tuple(
            sorted(embodied_bodies, key=lambda item: item.body_id)
        )
        if actor_ports is None:
            other_ids = tuple(
                item.body_id
                for item in embodied_bodies
                if item.body_id != canonical_self_body_id
            )
            if len(other_ids) != 1:
                raise ValueError(
                    "custom multi-body worlds require explicit actor ports"
                )
            embodied_ports = (
                EmbodimentPort(PORT_ID, canonical_self_body_id),
                EmbodimentPort(SECOND_BODY_PORT_ID, other_ids[0]),
            )
        else:
            if (
                not isinstance(actor_ports, Sequence)
                or isinstance(actor_ports, (str, bytes, bytearray))
                or len(actor_ports) != len(embodied_bodies)
                or any(not isinstance(item, EmbodimentPort) for item in actor_ports)
            ):
                raise ValueError("actor port topology differs from body topology")
            embodied_ports = tuple(actor_ports)
        self._actor_ports = tuple(
            sorted(embodied_ports, key=lambda item: item.port_id)
        )
        self._validate_port_topology(
            canonical_self_body_id, embodied_bodies, self._actor_ports
        )
        if initial_objects is None:
            objects = _manifest_objects()
        else:
            if (
                not isinstance(initial_objects, Sequence)
                or isinstance(initial_objects, (str, bytes, bytearray))
                or not 1 <= len(initial_objects) <= self._max_objects
            ):
                raise ValueError("world object inventory exceeds its exact capacity")
            if any(not isinstance(item, EmbodiedObject) for item in initial_objects):
                raise ValueError("world object inventory contains an invalid object")
            objects = tuple(initial_objects)
        world = _WorldState(
            revision=0,
            room_id=physical_regions[0].region_id,
            room_bounds=bounds,
            regions=physical_regions,
            portals=physical_portals,
            self_body_id=canonical_self_body_id,
            bodies=embodied_bodies,
            objects=tuple(sorted(objects, key=lambda item: item.object_id)),
        )
        self._validate_world(world)
        self._state = _AuthorityState(
            world=world,
            recent_applied_receipts=(),
            migration_receipt=None,
        )
        self._lock = threading.RLock()
        self._encoded_state_for(self._state)

    @property
    def port_id(self) -> str:
        return next(
            item.port_id
            for item in self._actor_ports
            if item.actor_body_id == self._state.world.self_body_id
        )

    @property
    def self_body_id(self) -> str:
        return self._state.world.self_body_id

    @property
    def actor_ports(self) -> tuple[EmbodimentPort, ...]:
        return self._actor_ports

    def _validate_port_topology(
        self,
        self_body_id: str,
        bodies: tuple[EmbodiedBody, ...],
        ports: tuple[EmbodimentPort, ...],
    ) -> None:
        if len(ports) != len(bodies):
            raise ValueError("every body requires exactly one actor port")
        for item in ports:
            item.verify()
        if tuple(sorted(ports, key=lambda item: item.port_id)) != ports:
            raise ValueError("actor ports are not in canonical port order")
        port_ids = tuple(item.port_id for item in ports)
        actor_ids = tuple(item.actor_body_id for item in ports)
        body_ids = tuple(item.body_id for item in bodies)
        if len(set(port_ids)) != len(port_ids):
            raise ValueError("actor port identities repeat")
        if len(set(actor_ids)) != len(actor_ids) or set(actor_ids) != set(body_ids):
            raise ValueError("actor port/body reciprocity changed")
        self_ports = tuple(
            item for item in ports if item.actor_body_id == self_body_id
        )
        if len(self_ports) != 1 or self_ports[0].port_id != PORT_ID:
            raise ValueError("self body must retain the canonical self port")

    def _validate_physical_topology(
        self,
        regions: tuple[PhysicalRegion, ...],
        portals: tuple[PhysicalPortal, ...],
    ) -> None:
        if (
            not 3 <= len(regions) <= self._max_regions
            or regions != tuple(sorted(regions, key=lambda item: item.region_id))
            or len({item.region_id for item in regions}) != len(regions)
        ):
            raise ValueError("physical region topology is not canonical")
        for item in regions:
            item.verify()
        if (
            not 2 <= len(portals) <= self._max_portals
            or portals != tuple(sorted(portals, key=lambda item: item.portal_id))
            or len({item.portal_id for item in portals}) != len(portals)
        ):
            raise ValueError("physical portal topology is not canonical")
        region_by_id = {item.region_id: item for item in regions}
        connected_pairs = set()
        for portal in portals:
            portal.verify()
            if any(value not in region_by_id for value in portal.region_ids):
                raise ValueError("portal names a region outside topology")
            if portal.region_ids in connected_pairs:
                raise ValueError("physical regions repeat a portal edge")
            connected_pairs.add(portal.region_ids)
            left, right = (region_by_id[value] for value in portal.region_ids)
            if portal.axis == "x":
                shared = {
                    left.bounds.minimum.x, left.bounds.maximum.x
                }.intersection({right.bounds.minimum.x, right.bounds.maximum.x})
                overlap_min = max(left.bounds.minimum.y, right.bounds.minimum.y)
                overlap_max = min(left.bounds.maximum.y, right.bounds.maximum.y)
            else:
                shared = {
                    left.bounds.minimum.y, left.bounds.maximum.y
                }.intersection({right.bounds.minimum.y, right.bounds.maximum.y})
                overlap_min = max(left.bounds.minimum.x, right.bounds.minimum.x)
                overlap_max = min(left.bounds.maximum.x, right.bounds.maximum.x)
            if (
                shared != {portal.plane_mm}
                or not overlap_min <= portal.aperture_min_mm
                < portal.aperture_max_mm <= overlap_max
                or portal.height_mm > min(
                    left.bounds.maximum.z, right.bounds.maximum.z
                )
            ):
                raise ValueError("portal aperture differs from shared boundaries")

    @staticmethod
    def _region_containing(
        regions: tuple[PhysicalRegion, ...],
        position: PositionMM,
        radius_mm: int,
    ) -> PhysicalRegion | None:
        matches = tuple(
            item for item in regions
            if item.bounds.contains_floor_disc(position, radius_mm)
        )
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _portal_between(
        portals: tuple[PhysicalPortal, ...],
        left: str,
        right: str,
    ) -> PhysicalPortal | None:
        pair = tuple(sorted((left, right)))
        return next((item for item in portals if item.region_ids == pair), None)

    @staticmethod
    def _portal_crossing_is_clear(
        portal: PhysicalPortal,
        start: PositionMM,
        finish: PositionMM,
        radius_mm: int,
    ) -> bool:
        if portal.axis == "x":
            delta = finish.x - start.x
            if delta == 0:
                return False
            numerator = (portal.plane_mm - start.x) * (finish.y - start.y)
            crossing_num = start.y * delta + numerator
            denominator = delta
        else:
            delta = finish.y - start.y
            if delta == 0:
                return False
            numerator = (portal.plane_mm - start.y) * (finish.x - start.x)
            crossing_num = start.x * delta + numerator
            denominator = delta
        if denominator < 0:
            crossing_num = -crossing_num
            denominator = -denominator
        return (
            (portal.aperture_min_mm + radius_mm) * denominator
            <= crossing_num
            <= (portal.aperture_max_mm - radius_mm) * denominator
            and start.z + radius_mm <= portal.height_mm
            and finish.z + radius_mm <= portal.height_mm
        )

    def _validate_world(self, world: _WorldState) -> None:
        _bounded_integer(world.revision, "world revision", minimum=0, maximum=MAX_REVISION)
        self._validate_physical_topology(world.regions, world.portals)
        region_by_id = {item.region_id: item for item in world.regions}
        if (
            world.room_id not in region_by_id
            or world.room_bounds != region_by_id[world.room_id].bounds
        ):
            raise ValueError("self region projection differs from topology")
        _identifier(world.self_body_id, "self body id")
        if not 2 <= len(world.bodies) <= self._max_bodies:
            raise ValueError("world body inventory exceeds its exact capacity")
        if tuple(sorted(world.bodies, key=lambda item: item.body_id)) != world.bodies:
            raise ValueError("world bodies are not in canonical identity order")
        body_ids = [item.body_id for item in world.bodies]
        if len(body_ids) != len(set(body_ids)) or world.self_body_id not in body_ids:
            raise ValueError("world body identities or self-body changed")
        for body in world.bodies:
            body.verify()
        self._validate_port_topology(
            world.self_body_id, world.bodies, self._actor_ports
        )
        if not 1 <= len(world.objects) <= self._max_objects:
            raise ValueError("world object inventory exceeds its exact capacity")
        if tuple(sorted(world.objects, key=lambda item: item.object_id)) != world.objects:
            raise ValueError("world objects are not in canonical identity order")
        ids = [item.object_id for item in world.objects]
        if len(ids) != len(set(ids)):
            raise ValueError("world object identities are not unique")
        held_by_body: dict[str, list[str]] = {
            item.body_id: [] for item in world.bodies
        }
        placed = []
        for item in world.objects:
            item.verify()
            if item.held_by_body_id is not None:
                if item.held_by_body_id not in held_by_body:
                    raise ValueError("object is held by a body outside this authority")
                held_by_body[item.held_by_body_id].append(item.object_id)
            else:
                if self._region_containing(
                    world.regions, item.position, item.radius_mm
                ) is None:
                    raise ValueError("object position is outside room geometry")
                placed.append(item)
        object_by_id = {item.object_id: item for item in world.objects}
        occupied: list[tuple[EmbodiedBody, int]] = []
        for body in world.bodies:
            held = held_by_body[body.body_id]
            expected_held = held[0] if len(held) == 1 else None
            if len(held) > 1 or body.held_object_id != expected_held:
                raise ValueError("body/object holding relation is not reciprocal")
            carried_radius = body.radius_mm
            if expected_held is not None:
                carried_radius = max(
                    carried_radius, object_by_id[expected_held].radius_mm
                )
            if self._region_containing(
                world.regions, body.pose.position, carried_radius
            ) is None:
                raise ValueError("body and held object are outside room geometry")
            occupied.append((body, carried_radius))
        self_body = next(
            item for item in world.bodies if item.body_id == world.self_body_id
        )
        self_region = self._region_containing(
            world.regions,
            self_body.pose.position,
            next(
                radius for body, radius in occupied
                if body.body_id == world.self_body_id
            ),
        )
        if self_region is None or self_region.region_id != world.room_id:
            raise ValueError("self body current region changed")
        for index, (left, left_radius) in enumerate(occupied):
            for right, right_radius in occupied[index + 1 :]:
                if (
                    self._region_containing(
                        world.regions, left.pose.position, left_radius
                    )
                    == self._region_containing(
                        world.regions, right.pose.position, right_radius
                    )
                    and _floor_discs_overlap(
                    left.pose.position,
                    left_radius,
                    right.pose.position,
                    right_radius,
                    )
                ):
                    raise ValueError("body geometries intersect")
        for body, carried_radius in occupied:
            for item in placed:
                if (
                    self._region_containing(
                        world.regions, body.pose.position, carried_radius
                    )
                    == self._region_containing(
                        world.regions, item.position, item.radius_mm
                    )
                    and _floor_discs_overlap(
                    body.pose.position,
                    carried_radius,
                    item.position,
                    item.radius_mm,
                    )
                ):
                    raise ValueError("body or held object intersects placed object geometry")
        for index, left in enumerate(placed):
            for right in placed[index + 1 :]:
                if (
                    self._region_containing(
                        world.regions, left.position, left.radius_mm
                    )
                    == self._region_containing(
                        world.regions, right.position, right.radius_mm
                    )
                    and _floor_discs_overlap(
                        left.position, left.radius_mm,
                        right.position, right.radius_mm
                    )
                ):
                    raise ValueError("placed objects intersect each other")

    def _observation_for(self, world: _WorldState) -> ObservationSnapshot:
        state_record = world.as_record()
        state_sha = _digest(state_record)
        unsigned = {
            **state_record,
            "schema": OBSERVATION_SCHEMA,
            "state_sha256": state_sha,
        }
        signature = _sign(self._key, OBSERVATION_DOMAIN, unsigned)
        receipt = _digest({"authority_hmac_sha256": signature, "payload": unsigned})
        return ObservationSnapshot(
            revision=world.revision,
            room_id=world.room_id,
            room_bounds=world.room_bounds,
            regions=world.regions,
            portals=world.portals,
            self_body_id=world.self_body_id,
            bodies=world.bodies,
            objects=world.objects,
            state_sha256=state_sha,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=receipt,
        )

    def observation_snapshot(self) -> ObservationSnapshot:
        with self._lock:
            return self._observation_for(self._state.world)

    def latest_execution_snapshot(self) -> ActionExecutionReceipt | None:
        """Return the latest immutable completed action, if one exists."""
        with self._lock:
            if not self._state.recent_applied_receipts:
                return None
            receipt = self._state.recent_applied_receipts[-1]
            self._verify_execution(receipt)
            return receipt

    def _execution_receipt(
        self,
        *,
        port_id: str,
        actor_body_id: str | None,
        causal_intent_receipt_sha256: str,
        command_sha256: str,
        expected_revision: int,
        disposition: str,
        reason: str,
        lifecycle: tuple[str, ...],
        before: ObservationSnapshot,
        after: ObservationSnapshot,
    ) -> ActionExecutionReceipt:
        unsigned = {
            "actor_body_id": actor_body_id,
            "after": after.as_record(),
            "before": before.as_record(),
            "causal_intent_receipt_sha256": causal_intent_receipt_sha256,
            "command_sha256": command_sha256,
            "disposition": disposition,
            "expected_revision": expected_revision,
            "lifecycle": list(lifecycle),
            "observed_revision": before.revision,
            "port_id": port_id,
            "reason": reason,
            "schema": EXECUTION_SCHEMA,
        }
        signature = _sign(self._key, EXECUTION_DOMAIN, unsigned)
        receipt = _digest({"authority_hmac_sha256": signature, "payload": unsigned})
        return ActionExecutionReceipt(
            port_id=port_id,
            actor_body_id=actor_body_id,
            causal_intent_receipt_sha256=causal_intent_receipt_sha256,
            command_sha256=command_sha256,
            expected_revision=expected_revision,
            observed_revision=before.revision,
            disposition=disposition,
            reason=reason,
            lifecycle=lifecycle,
            before=before,
            after=after,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=receipt,
        )

    def _reject(
        self,
        *,
        port_id: str,
        actor_body_id: str | None,
        causal_intent_receipt_sha256: str,
        command_sha256: str,
        expected_revision: int,
        reason: str,
        lifecycle: tuple[str, ...],
        before: ObservationSnapshot,
    ) -> ActionExecutionReceipt:
        return self._execution_receipt(
            port_id=port_id,
            actor_body_id=actor_body_id,
            causal_intent_receipt_sha256=causal_intent_receipt_sha256,
            command_sha256=command_sha256,
            expected_revision=expected_revision,
            disposition="rejected",
            reason=reason,
            lifecycle=lifecycle + ("rejected",),
            before=before,
            after=before,
        )

    def _transition(
        self,
        world: _WorldState,
        actor_body_id: str,
        command: EmbodimentCommand,
    ) -> tuple[_WorldState | None, str]:
        bodies = list(world.bodies)
        body_index = next(
            index
            for index, item in enumerate(bodies)
            if item.body_id == actor_body_id
        )
        body = bodies[body_index]
        objects = list(world.objects)
        by_id = {item.object_id: (index, item) for index, item in enumerate(objects)}

        def occupied_radius(value: EmbodiedBody) -> int:
            if value.held_object_id is None:
                return value.radius_mm
            return max(value.radius_mm, by_id[value.held_object_id][1].radius_mm)

        if isinstance(command, MoveCommand):
            target = command.target_pose
            carried_radius = occupied_radius(body)
            start_region = self._region_containing(
                world.regions, body.pose.position, carried_radius
            )
            target_region = self._region_containing(
                world.regions, target.position, carried_radius
            )
            if target_region is None:
                return None, "move_outside_room"
            if start_region is None:
                raise RuntimeError("body lost its physical region")
            if start_region.region_id != target_region.region_id:
                portal = self._portal_between(
                    world.portals,
                    start_region.region_id,
                    target_region.region_id,
                )
                if portal is None:
                    return None, "move_crosses_disconnected_regions"
                if not self._portal_crossing_is_clear(
                    portal, body.pose.position, target.position, carried_radius
                ):
                    return None, "move_misses_portal_aperture"
            for other in bodies:
                if other.body_id == body.body_id:
                    continue
                other_region = self._region_containing(
                    world.regions,
                    other.pose.position,
                    occupied_radius(other),
                )
                if (
                    other_region in {start_region, target_region}
                    and _straight_path_intersects_disc(
                    body.pose.position,
                    target.position,
                    other.pose.position,
                    carried_radius + occupied_radius(other),
                    )
                ):
                    return None, "move_path_intersects_body"
            for item in objects:
                item_region = (
                    self._region_containing(
                        world.regions, item.position, item.radius_mm
                    ) if item.position is not None else None
                )
                if (
                    item.position is not None
                    and item_region in {start_region, target_region}
                    and _straight_path_intersects_disc(
                    body.pose.position,
                    target.position,
                    item.position,
                    carried_radius + item.radius_mm,
                    )
                ):
                    return None, "move_path_intersects_object"
            bodies[body_index] = replace(body, pose=target)
            changed = replace(world, bodies=tuple(bodies))
            if body.body_id == world.self_body_id:
                changed = replace(
                    changed,
                    room_id=target_region.region_id,
                    room_bounds=target_region.bounds,
                )
            return changed, "applied"

        if isinstance(command, PickCommand):
            found = by_id.get(command.object_id)
            if found is None:
                return None, "pick_unknown_object"
            if body.held_object_id is not None:
                return None, "pick_body_already_holding"
            index, item = found
            if item.position is None:
                return None, "pick_object_unavailable"
            body_region = self._region_containing(
                world.regions, body.pose.position, body.radius_mm
            )
            object_region = self._region_containing(
                world.regions, item.position, item.radius_mm
            )
            if body_region != object_region:
                return None, "pick_object_outside_region"
            if _distance_squared(body.pose.position, item.position) > body.reach_mm**2:
                return None, "pick_out_of_reach"
            if self._region_containing(
                world.regions,
                body.pose.position,
                max(body.radius_mm, item.radius_mm),
            ) is None:
                return None, "pick_carried_geometry_outside_room"
            objects[index] = replace(item, position=None, held_by_body_id=body.body_id)
            bodies[body_index] = replace(
                body, held_object_id=item.object_id
            )
            return replace(
                world,
                bodies=tuple(bodies),
                objects=tuple(objects),
            ), "applied"

        if isinstance(command, PlaceCommand):
            found = by_id.get(command.object_id)
            if found is None:
                return None, "place_unknown_object"
            index, item = found
            if body.held_object_id != item.object_id or item.held_by_body_id != body.body_id:
                return None, "place_object_not_held"
            body_region = self._region_containing(
                world.regions, body.pose.position, body.radius_mm
            )
            target_region = self._region_containing(
                world.regions, command.target_position, item.radius_mm
            )
            if target_region is None:
                return None, "place_outside_room"
            if target_region != body_region:
                return None, "place_target_outside_region"
            if _distance_squared(body.pose.position, command.target_position) > body.reach_mm**2:
                return None, "place_out_of_reach"
            for other in bodies:
                other_region = self._region_containing(
                    world.regions,
                    other.pose.position,
                    occupied_radius(other),
                )
                if other_region == target_region and _floor_discs_overlap(
                    other.pose.position,
                    occupied_radius(other),
                    command.target_position,
                    item.radius_mm,
                ):
                    return None, "place_intersects_body"
            for other in objects:
                if (
                    other.object_id != item.object_id
                    and other.position is not None
                    and self._region_containing(
                        world.regions, other.position, other.radius_mm
                    ) == target_region
                    and _floor_discs_overlap(
                    command.target_position,
                    item.radius_mm,
                    other.position,
                    other.radius_mm,
                    )
                ):
                    return None, "place_intersects_object"
            objects[index] = replace(item, position=command.target_position, held_by_body_id=None)
            bodies[body_index] = replace(body, held_object_id=None)
            return replace(
                world,
                bodies=tuple(bodies),
                objects=tuple(objects),
            ), "applied"

        if isinstance(command, VocalizeCommand):
            # Pressure is transient and therefore does not become retained
            # world state.  The authenticated execution still advances the
            # causal revision exactly once; the acoustic authority separately
            # proves that the emitted bytes match this command commitment.
            command_record(command)
            return world, "applied"

        raise ValueError("unsupported embodiment command type")

    def _commit_authority_state(self, candidate: _AuthorityState) -> None:
        self._state = candidate

    def execute_port_command(
        self,
        *,
        port_id: str,
        command_payload: bytes,
        causal_intent_receipt_sha256: str,
        expected_revision: int,
    ) -> ActionExecutionReceipt:
        """Execute one opaque port command against an exact observed revision.

        Revision binding makes each execution a one-time causal transition:
        replay after a successful transition fails closed as stale.  Rejected
        commands do not alter world state or retained authority state.
        """

        port = _identifier(port_id, "embodiment port id")
        intent = _sha256_identity(causal_intent_receipt_sha256, "causal intent receipt")
        revision = _bounded_integer(expected_revision, "expected revision", minimum=0, maximum=MAX_REVISION)
        if (
            not isinstance(command_payload, bytes)
            or not command_payload
            or len(command_payload) > self._max_command_bytes
        ):
            raise ValueError("embodiment command payload exceeds its exact byte boundary")
        command_sha = _sha256(command_payload)

        with self._lock:
            before_state = self._state
            before = self._observation_for(before_state.world)
            lifecycle = ("received",)
            actor_by_port = {
                item.port_id: item.actor_body_id for item in self._actor_ports
            }
            actor_body_id = actor_by_port.get(port)
            if actor_body_id is None:
                return self._reject(
                    port_id=port,
                    actor_body_id=None,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason="port_mismatch",
                    lifecycle=lifecycle,
                    before=before,
                )
            lifecycle += ("port_validated",)
            if revision != before.revision:
                return self._reject(
                    port_id=port,
                    actor_body_id=actor_body_id,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason="stale_world_revision",
                    lifecycle=lifecycle,
                    before=before,
                )
            if before.revision == MAX_REVISION:
                return self._reject(
                    port_id=port,
                    actor_body_id=actor_body_id,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason="world_revision_exhausted",
                    lifecycle=lifecycle,
                    before=before,
                )
            try:
                command = decode_command(command_payload, max_command_bytes=self._max_command_bytes)
            except ValueError:
                return self._reject(
                    port_id=port,
                    actor_body_id=actor_body_id,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason="command_not_canonical",
                    lifecycle=lifecycle,
                    before=before,
                )
            lifecycle += ("command_decoded",)
            transitioned, reason = self._transition(
                before_state.world, actor_body_id, command
            )
            if transitioned is None:
                return self._reject(
                    port_id=port,
                    actor_body_id=actor_body_id,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason=reason,
                    lifecycle=lifecycle + ("geometry_rejected",),
                    before=before,
                )
            transitioned = replace(transitioned, revision=before.revision + 1)
            consequence_lifecycle = (
                "vocal_commitment_validated"
                if isinstance(command, VocalizeCommand)
                else "geometry_validated"
            )
            self._validate_world(transitioned)
            after = self._observation_for(transitioned)
            receipt = self._execution_receipt(
                port_id=port,
                actor_body_id=actor_body_id,
                causal_intent_receipt_sha256=intent,
                command_sha256=command_sha,
                expected_revision=revision,
                disposition="applied",
                reason="applied",
                lifecycle=lifecycle + (consequence_lifecycle, "applied"),
                before=before,
                after=after,
            )
            retained = (before_state.recent_applied_receipts + (receipt,))[-self._receipt_capacity :]
            candidate = _AuthorityState(
                world=transitioned,
                recent_applied_receipts=retained,
                migration_receipt=before_state.migration_receipt,
            )
            try:
                self._encoded_state_for(candidate)
            except ValueError as error:
                if "byte capacity" not in str(error):
                    raise
                return self._reject(
                    port_id=port,
                    actor_body_id=actor_body_id,
                    causal_intent_receipt_sha256=intent,
                    command_sha256=command_sha,
                    expected_revision=revision,
                    reason="state_capacity_exhausted",
                    lifecycle=lifecycle + (
                        consequence_lifecycle,
                        "state_capacity_rejected",
                    ),
                    before=before,
                )
            try:
                self._commit_authority_state(candidate)
            except BaseException:
                self._state = before_state
                raise
            return receipt

    def recent_applied_receipts(self) -> tuple[ActionExecutionReceipt, ...]:
        with self._lock:
            return self._state.recent_applied_receipts

    def verify_execution_receipt(self, receipt: ActionExecutionReceipt) -> None:
        """Verify one self-contained applied W1 execution authority.

        Verification authenticates the exact before/after geometry and command
        identity.  It does not require the receipt to remain in the bounded
        recent-receipt window.
        """

        if not isinstance(receipt, ActionExecutionReceipt):
            raise ValueError("execution receipt is not typed")
        with self._lock:
            self._verify_execution(receipt)

    def verify_observation_snapshot(
        self, observation: ObservationSnapshot
    ) -> None:
        """Verify one self-contained authenticated W1 observation."""

        if not isinstance(observation, ObservationSnapshot):
            raise ValueError("observation snapshot is not typed")
        with self._lock:
            self._verify_observation(observation)

    def _verify_observation(self, observation: ObservationSnapshot) -> None:
        world = _WorldState(
            revision=observation.revision,
            room_id=observation.room_id,
            room_bounds=observation.room_bounds,
            regions=observation.regions,
            portals=observation.portals,
            self_body_id=observation.self_body_id,
            bodies=observation.bodies,
            objects=observation.objects,
        )
        self._validate_world(world)
        expected = self._observation_for(world)
        if expected != observation:
            raise ValueError("observation authentication changed")

    def _verify_execution(self, receipt: ActionExecutionReceipt) -> None:
        if receipt.disposition != "applied" or receipt.reason != "applied":
            raise ValueError("retained execution must be applied")
        if receipt.lifecycle[-2:] not in (
            ("geometry_validated", "applied"),
            ("vocal_commitment_validated", "applied"),
        ):
            raise ValueError("retained execution lifecycle changed")
        port_actor = next(
            (
                item.actor_body_id
                for item in self._actor_ports
                if item.port_id == receipt.port_id
            ),
            None,
        )
        if port_actor is None or receipt.actor_body_id != port_actor:
            raise ValueError("retained execution port changed")
        _sha256_identity(receipt.causal_intent_receipt_sha256, "causal intent receipt")
        _sha256_identity(receipt.command_sha256, "command identity")
        self._verify_observation(receipt.before)
        self._verify_observation(receipt.after)
        if (
            receipt.expected_revision != receipt.before.revision
            or receipt.observed_revision != receipt.before.revision
            or receipt.after.revision != receipt.before.revision + 1
        ):
            raise ValueError("retained execution revision chain changed")
        unsigned = receipt.unsigned_record()
        expected_hmac = _sign(self._key, EXECUTION_DOMAIN, unsigned)
        if not hmac.compare_digest(expected_hmac, receipt.authority_hmac_sha256):
            raise ValueError("execution HMAC changed")
        expected_receipt = _digest({"authority_hmac_sha256": expected_hmac, "payload": unsigned})
        if expected_receipt != receipt.authority_receipt_sha256:
            raise ValueError("execution receipt identity changed")

    def _state_payload_for(self, state: _AuthorityState) -> dict[str, object]:
        return {
            "actor_ports": [item.as_record() for item in self._actor_ports],
            "limits": {
                "max_regions": self._max_regions,
                "max_portals": self._max_portals,
                "max_bodies": self._max_bodies,
                "max_command_bytes": self._max_command_bytes,
                "max_encoded_state_bytes": self._max_encoded_state_bytes,
                "max_objects": self._max_objects,
                "receipt_capacity": self._receipt_capacity,
            },
            "migration_receipt": (
                state.migration_receipt.as_record()
                if state.migration_receipt is not None
                else None
            ),
            "recent_applied_receipts": [item.as_record() for item in state.recent_applied_receipts],
            "schema": STATE_SCHEMA,
            "world": state.world.as_record(),
        }

    def _encoded_state_for(self, state: _AuthorityState) -> bytes:
        payload = _canonical(self._state_payload_for(state))
        if len(payload) > self._max_encoded_state_bytes:
            raise ValueError("embodiment state exceeds its exact byte capacity")
        signature = hmac.new(self._key, STATE_DOMAIN + payload, hashlib.sha256).hexdigest()
        envelope = {
            "authority_hmac_sha256": signature,
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": ENVELOPE_SCHEMA,
        }
        encoded = _canonical(envelope)
        if len(encoded) > self._max_encoded_state_bytes:
            raise ValueError("encoded embodiment state exceeds its exact byte capacity")
        return encoded

    def encoded_snapshot(self) -> bytes:
        with self._lock:
            return self._encoded_state_for(self._state)

    def _observation_from_record(self, value: object) -> ObservationSnapshot:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "bodies",
            "objects",
            "portals",
            "regions",
            "revision",
            "room_bounds",
            "room_id",
            "schema",
            "self_body_id",
            "state_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected or value.get("schema") != OBSERVATION_SCHEMA:
            raise ValueError("observation record fields changed")
        raw_objects = value.get("objects")
        raw_bodies = value.get("bodies")
        raw_regions = value.get("regions")
        raw_portals = value.get("portals")
        if not isinstance(raw_bodies, list) or not 2 <= len(raw_bodies) <= self._max_bodies:
            raise ValueError("observation bodies changed")
        if not isinstance(raw_objects, list) or not 1 <= len(raw_objects) <= self._max_objects:
            raise ValueError("observation objects changed")
        result = ObservationSnapshot(
            revision=value.get("revision"),
            room_id=value.get("room_id"),
            room_bounds=_room_from(value.get("room_bounds")),
            regions=tuple(_region_from(item) for item in raw_regions)
            if isinstance(raw_regions, list) else (),
            portals=tuple(_portal_from(item) for item in raw_portals)
            if isinstance(raw_portals, list) else (),
            self_body_id=_identifier(value.get("self_body_id"), "self body id"),
            bodies=tuple(_body_from(item) for item in raw_bodies),
            objects=tuple(_object_from(item) for item in raw_objects),
            state_sha256=_sha256_identity(value.get("state_sha256"), "observation state identity"),
            authority_hmac_sha256=_sha256_identity(value.get("authority_hmac_sha256"), "observation HMAC"),
            authority_receipt_sha256=_sha256_identity(value.get("authority_receipt_sha256"), "observation receipt"),
        )
        if result.as_record() != dict(value):
            raise ValueError("observation record is not canonical")
        self._verify_observation(result)
        return result

    def _execution_from_record(self, value: object) -> ActionExecutionReceipt:
        expected = {
            "actor_body_id",
            "after",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "before",
            "causal_intent_receipt_sha256",
            "command_sha256",
            "disposition",
            "expected_revision",
            "lifecycle",
            "observed_revision",
            "port_id",
            "reason",
            "schema",
        }
        if not isinstance(value, Mapping) or set(value) != expected or value.get("schema") != EXECUTION_SCHEMA:
            raise ValueError("execution record fields changed")
        lifecycle = value.get("lifecycle")
        if not isinstance(lifecycle, list) or not lifecycle or any(not isinstance(item, str) for item in lifecycle):
            raise ValueError("execution lifecycle changed")
        result = ActionExecutionReceipt(
            port_id=_identifier(value.get("port_id"), "execution port id"),
            actor_body_id=_identifier(
                value.get("actor_body_id"), "execution actor body id"
            ),
            causal_intent_receipt_sha256=_sha256_identity(value.get("causal_intent_receipt_sha256"), "causal intent receipt"),
            command_sha256=_sha256_identity(value.get("command_sha256"), "command identity"),
            expected_revision=_bounded_integer(value.get("expected_revision"), "expected revision", minimum=0, maximum=MAX_REVISION),
            observed_revision=_bounded_integer(value.get("observed_revision"), "observed revision", minimum=0, maximum=MAX_REVISION),
            disposition=value.get("disposition"),
            reason=value.get("reason"),
            lifecycle=tuple(lifecycle),
            before=self._observation_from_record(value.get("before")),
            after=self._observation_from_record(value.get("after")),
            authority_hmac_sha256=_sha256_identity(value.get("authority_hmac_sha256"), "execution HMAC"),
            authority_receipt_sha256=_sha256_identity(value.get("authority_receipt_sha256"), "execution receipt"),
        )
        if result.as_record() != dict(value):
            raise ValueError("execution record is not canonical")
        self._verify_execution(result)
        return result

    def _migration_receipt_for(
        self,
        *,
        prior_envelope_sha256: str,
        prior_observation_receipt_sha256: str,
        resulting_observation_receipt_sha256: str,
        prior_revision: int,
        resulting_revision: int,
        parent_migration_receipt_sha256: str | None,
        manifest_sha256: str,
        prior_topology_sha256: str,
        resulting_topology_sha256: str,
    ) -> WorldMigrationReceipt:
        unsigned = {
            "manifest_sha256": manifest_sha256,
            "parent_migration_receipt_sha256": parent_migration_receipt_sha256,
            "prior_envelope_sha256": prior_envelope_sha256,
            "prior_observation_receipt_sha256": prior_observation_receipt_sha256,
            "prior_revision": prior_revision,
            "resulting_observation_receipt_sha256": resulting_observation_receipt_sha256,
            "resulting_revision": resulting_revision,
            "prior_topology_sha256": prior_topology_sha256,
            "resulting_topology_sha256": resulting_topology_sha256,
            "schema": MIGRATION_SCHEMA,
        }
        signature = _sign(self._key, MIGRATION_DOMAIN, unsigned)
        return WorldMigrationReceipt(
            prior_envelope_sha256=prior_envelope_sha256,
            prior_observation_receipt_sha256=prior_observation_receipt_sha256,
            resulting_observation_receipt_sha256=resulting_observation_receipt_sha256,
            prior_revision=prior_revision,
            resulting_revision=resulting_revision,
            parent_migration_receipt_sha256=parent_migration_receipt_sha256,
            manifest_sha256=manifest_sha256,
            prior_topology_sha256=prior_topology_sha256,
            resulting_topology_sha256=resulting_topology_sha256,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest(
                {"authority_hmac_sha256": signature, "payload": unsigned}
            ),
        )

    def _verify_migration_receipt(
        self, receipt: WorldMigrationReceipt, world: _WorldState
    ) -> None:
        if not isinstance(receipt, WorldMigrationReceipt):
            raise ValueError("world migration receipt is not typed")
        for value, name in (
            (receipt.prior_envelope_sha256, "prior envelope"),
            (receipt.prior_observation_receipt_sha256, "prior observation"),
            (receipt.resulting_observation_receipt_sha256, "resulting observation"),
            (receipt.manifest_sha256, "migration manifest"),
            (receipt.prior_topology_sha256, "prior topology"),
            (receipt.resulting_topology_sha256, "resulting topology"),
        ):
            _sha256_identity(value, name)
        if receipt.parent_migration_receipt_sha256 is not None:
            _sha256_identity(
                receipt.parent_migration_receipt_sha256,
                "parent migration receipt",
            )
        _bounded_integer(
            receipt.prior_revision,
            "migration prior revision",
            minimum=0,
            maximum=MAX_REVISION,
        )
        _bounded_integer(
            receipt.resulting_revision,
            "migration resulting revision",
            minimum=1,
            maximum=MAX_REVISION,
        )
        if (
            receipt.resulting_revision != receipt.prior_revision + 1
            or receipt.resulting_revision > world.revision
            or receipt.manifest_sha256 != self._physical_manifest_sha256()
            or receipt.resulting_topology_sha256
            != self._topology_sha256(world.regions, world.portals)
        ):
            raise ValueError("world migration causal chain changed")
        unsigned = receipt.unsigned_record()
        expected_hmac = _sign(self._key, MIGRATION_DOMAIN, unsigned)
        if not hmac.compare_digest(
            expected_hmac, receipt.authority_hmac_sha256
        ):
            raise ValueError("world migration HMAC changed")
        if receipt.authority_receipt_sha256 != _digest(
            {"authority_hmac_sha256": expected_hmac, "payload": unsigned}
        ):
            raise ValueError("world migration identity changed")

    def _migration_from_record(
        self, value: object, world: _WorldState
    ) -> WorldMigrationReceipt:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "manifest_sha256",
            "parent_migration_receipt_sha256",
            "prior_envelope_sha256",
            "prior_observation_receipt_sha256",
            "prior_revision",
            "prior_topology_sha256",
            "resulting_observation_receipt_sha256",
            "resulting_revision",
            "resulting_topology_sha256",
            "schema",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != MIGRATION_SCHEMA
        ):
            raise ValueError("world migration fields changed")
        result = WorldMigrationReceipt(
            prior_envelope_sha256=_sha256_identity(
                value.get("prior_envelope_sha256"), "prior envelope"
            ),
            prior_observation_receipt_sha256=_sha256_identity(
                value.get("prior_observation_receipt_sha256"),
                "prior observation",
            ),
            resulting_observation_receipt_sha256=_sha256_identity(
                value.get("resulting_observation_receipt_sha256"),
                "resulting observation",
            ),
            prior_revision=_bounded_integer(
                value.get("prior_revision"),
                "migration prior revision",
                minimum=0,
                maximum=MAX_REVISION,
            ),
            resulting_revision=_bounded_integer(
                value.get("resulting_revision"),
                "migration resulting revision",
                minimum=1,
                maximum=MAX_REVISION,
            ),
            parent_migration_receipt_sha256=(
                _sha256_identity(
                    value.get("parent_migration_receipt_sha256"),
                    "parent migration receipt",
                )
                if value.get("parent_migration_receipt_sha256") is not None
                else None
            ),
            manifest_sha256=_sha256_identity(
                value.get("manifest_sha256"), "migration manifest"
            ),
            prior_topology_sha256=_sha256_identity(
                value.get("prior_topology_sha256"), "prior topology"
            ),
            resulting_topology_sha256=_sha256_identity(
                value.get("resulting_topology_sha256"), "resulting topology"
            ),
            authority_hmac_sha256=_sha256_identity(
                value.get("authority_hmac_sha256"), "migration HMAC"
            ),
            authority_receipt_sha256=_sha256_identity(
                value.get("authority_receipt_sha256"), "migration receipt"
            ),
        )
        if result.as_record() != dict(value):
            raise ValueError("world migration record is not canonical")
        self._verify_migration_receipt(result, world)
        return result

    def _topology_sha256(
        self,
        regions: tuple[PhysicalRegion, ...],
        portals: tuple[PhysicalPortal, ...],
    ) -> str:
        return _digest(
            {
                "portals": [item.as_record() for item in portals],
                "regions": [item.as_record() for item in regions],
            }
        )

    def _physical_manifest_sha256(self) -> str:
        return _digest(
            {
                "object_physics": [
                    {
                        "mass_grams": item.mass_grams,
                        "object_id": item.object_id,
                        "radius_mm": item.radius_mm,
                        "reflectance_ppm": list(item.reflectance_ppm),
                    }
                    for item in _manifest_objects()
                ],
                "portals": [item.as_record() for item in _default_portals()],
                "regions": [item.as_record() for item in _default_regions()],
            }
        )

    def _decode_authenticated_envelope(
        self, encoded: bytes, *, envelope_schema: str, domain: bytes, limit: int
    ) -> tuple[Mapping[str, object], bytes]:
        if not isinstance(encoded, bytes) or not encoded or len(encoded) > limit:
            raise ValueError("encoded embodiment state exceeds its exact byte capacity")
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("embodiment state envelope is not canonical JSON") from error
        expected_envelope = {"authority_hmac_sha256", "payload_base64", "schema"}
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != expected_envelope
            or envelope.get("schema") != envelope_schema
        ):
            raise ValueError("embodiment state envelope fields changed")
        if _canonical(envelope) != encoded:
            raise ValueError("embodiment state envelope is not canonical")
        try:
            payload = base64.b64decode(
                envelope.get("payload_base64"), validate=True
            )
        except Exception as error:
            raise ValueError("embodiment state payload is not canonical base64") from error
        if not payload or len(payload) > limit:
            raise ValueError("embodiment state payload exceeds its exact byte capacity")
        provided_hmac = _sha256_identity(
            envelope.get("authority_hmac_sha256"), "state HMAC"
        )
        expected_hmac = hmac.new(
            self._key, domain + payload, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_hmac, provided_hmac):
            raise ValueError("embodiment state HMAC changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("embodiment state payload is not canonical JSON") from error
        if not isinstance(decoded, Mapping) or _canonical(decoded) != payload:
            raise ValueError("embodiment state payload is not canonical")
        return decoded, payload

    def _migrated_objects(
        self, prior_objects: tuple[EmbodiedObject, ...]
    ) -> tuple[EmbodiedObject, ...]:
        manifest = {item.object_id: item for item in _manifest_objects()}
        migrated: list[EmbodiedObject] = []
        present: set[str] = set()
        for item in prior_objects:
            if item.object_id in present:
                raise ValueError("prior world object identities repeat")
            present.add(item.object_id)
            reference = manifest.get(item.object_id)
            migrated.append(
                replace(
                    item,
                    reflectance_ppm=(
                        reference.reflectance_ppm
                        if reference is not None
                        else item.reflectance_ppm
                    ),
                )
            )
        for item in _manifest_objects():
            if item.object_id not in present:
                migrated.append(item)
        if len(migrated) > self._max_objects:
            raise ValueError("migrated world object inventory exceeds capacity")
        return tuple(sorted(migrated, key=lambda item: item.object_id))

    def _commit_migrated_world(
        self,
        *,
        encoded: bytes,
        prior_revision: int,
        prior_room_id: str,
        prior_room_bounds: RoomBoundsMM,
        prior_bodies: tuple[EmbodiedBody, ...],
        prior_objects: tuple[EmbodiedObject, ...],
        prior_observation_unsigned: Mapping[str, object],
        prior_observation_domain: bytes,
        parent_migration_receipt_sha256: str | None,
    ) -> None:
        regions = _default_regions()
        portals = _default_portals()
        self_body_id = self._state.world.self_body_id
        bodies = prior_bodies
        if {item.body_id for item in bodies} != {
            item.actor_body_id for item in self._actor_ports
        }:
            raise ValueError("prior physical bodies differ from actor port topology")
        if self_body_id not in {item.body_id for item in bodies}:
            raise ValueError("prior world self body changed")
        self_body = next(item for item in bodies if item.body_id == self_body_id)
        current_region = self._region_containing(
            regions, self_body.pose.position, self_body.radius_mm
        )
        if current_region is None:
            raise ValueError("prior self body is outside the v3 physical topology")
        migrated_world = _WorldState(
            revision=prior_revision + 1,
            room_id=current_region.region_id,
            room_bounds=current_region.bounds,
            regions=regions,
            portals=portals,
            self_body_id=self_body_id,
            bodies=tuple(sorted(bodies, key=lambda item: item.body_id)),
            objects=self._migrated_objects(prior_objects),
        )
        try:
            self._validate_world(migrated_world)
        except ValueError as error:
            raise ValueError(
                "prior physical state cannot settle into the v3 topology"
            ) from error
        prior_hmac = _sign(
            self._key, prior_observation_domain, prior_observation_unsigned
        )
        prior_observation_receipt = _digest(
            {
                "authority_hmac_sha256": prior_hmac,
                "payload": prior_observation_unsigned,
            }
        )
        resulting_observation = self._observation_for(migrated_world)
        migration = self._migration_receipt_for(
            prior_envelope_sha256=hashlib.sha256(encoded).hexdigest(),
            prior_observation_receipt_sha256=prior_observation_receipt,
            resulting_observation_receipt_sha256=(
                resulting_observation.authority_receipt_sha256
            ),
            prior_revision=prior_revision,
            resulting_revision=migrated_world.revision,
            parent_migration_receipt_sha256=parent_migration_receipt_sha256,
            manifest_sha256=self._physical_manifest_sha256(),
            prior_topology_sha256=_digest(
                {
                    "room_bounds": prior_room_bounds.as_record(),
                    "room_id": prior_room_id,
                }
            ),
            resulting_topology_sha256=self._topology_sha256(regions, portals),
        )
        candidate = _AuthorityState(
            world=migrated_world,
            recent_applied_receipts=(),
            migration_receipt=migration,
        )
        self._encoded_state_for(candidate)
        with self._lock:
            before_state = self._state
            try:
                self._commit_authority_state(candidate)
            except BaseException:
                self._state = before_state
                raise

    def _restore_legacy_encoded(self, encoded: bytes) -> None:
        decoded, _payload = self._decode_authenticated_envelope(
            encoded,
            envelope_schema=LEGACY_ENVELOPE_SCHEMA,
            domain=LEGACY_STATE_DOMAIN,
            limit=LEGACY_MAX_ENCODED_STATE_BYTES,
        )
        expected_state = {
            "limits", "port_id", "recent_applied_receipts", "schema", "world"
        }
        if set(decoded) != expected_state or decoded.get("schema") != LEGACY_STATE_SCHEMA:
            raise ValueError("legacy embodiment state fields changed")
        limits = decoded.get("limits")
        expected_limit_fields = {
            "max_command_bytes",
            "max_encoded_state_bytes",
            "max_objects",
            "receipt_capacity",
        }
        if not isinstance(limits, Mapping) or set(limits) != expected_limit_fields:
            raise ValueError("legacy embodiment authority limits changed")
        _bounded_integer(
            limits.get("max_command_bytes"),
            "legacy command capacity",
            minimum=64,
            maximum=self._max_command_bytes,
        )
        prior_state_capacity = _bounded_integer(
            limits.get("max_encoded_state_bytes"),
            "legacy encoded state capacity",
            minimum=4096,
            maximum=LEGACY_MAX_ENCODED_STATE_BYTES,
        )
        prior_object_capacity = _bounded_integer(
            limits.get("max_objects"),
            "legacy object capacity",
            minimum=1,
            maximum=self._max_objects,
        )
        prior_receipt_capacity = _bounded_integer(
            limits.get("receipt_capacity"),
            "legacy receipt capacity",
            minimum=1,
            maximum=4096,
        )
        if decoded.get("port_id") != PORT_ID or len(encoded) > prior_state_capacity:
            raise ValueError("legacy embodiment authority port or capacity changed")
        raw_receipts = decoded.get("recent_applied_receipts")
        if (
            not isinstance(raw_receipts, list)
            or len(raw_receipts) > prior_receipt_capacity
            or any(not isinstance(item, Mapping) for item in raw_receipts)
        ):
            raise ValueError("legacy retained execution receipts changed")
        world_value = decoded.get("world")
        expected_world = {"body", "objects", "revision", "room_bounds", "room_id"}
        if not isinstance(world_value, Mapping) or set(world_value) != expected_world:
            raise ValueError("legacy world state fields changed")
        raw_objects = world_value.get("objects")
        if (
            not isinstance(raw_objects, list)
            or not 1 <= len(raw_objects) <= prior_object_capacity
        ):
            raise ValueError("legacy world object inventory changed")
        prior_revision = _bounded_integer(
            world_value.get("revision"),
            "legacy world revision",
            minimum=0,
            maximum=MAX_REVISION - 1,
        )
        room_id = _identifier(world_value.get("room_id"), "legacy room id")
        room_bounds = _room_from(world_value.get("room_bounds"))
        legacy_body = _body_from(world_value.get("body"))
        legacy_objects = tuple(_legacy_object_from(item) for item in raw_objects)
        legacy_world_record = {
            "body": legacy_body.as_record(),
            "objects": [],
            "revision": prior_revision,
            "room_bounds": room_bounds.as_record(),
            "room_id": room_id,
        }
        for item in legacy_objects:
            record = item.as_record()
            del record["reflectance_ppm"]
            legacy_world_record["objects"].append(record)
        if legacy_world_record != dict(world_value):
            raise ValueError("legacy world state is not canonical")
        other_bodies = tuple(
            item
            for item in self._state.world.bodies
            if item.body_id != legacy_body.body_id
        )
        if len(other_bodies) != 1:
            raise ValueError("legacy migration requires one added physical body")
        bodies = tuple(
            sorted((legacy_body, other_bodies[0]), key=lambda item: item.body_id)
        )
        prior_observation_unsigned = {
            **legacy_world_record,
            "schema": LEGACY_OBSERVATION_SCHEMA,
            "state_sha256": _digest(legacy_world_record),
        }
        self._commit_migrated_world(
            encoded=encoded,
            prior_revision=prior_revision,
            prior_room_id=room_id,
            prior_room_bounds=room_bounds,
            prior_bodies=bodies,
            prior_objects=legacy_objects,
            prior_observation_unsigned=prior_observation_unsigned,
            prior_observation_domain=LEGACY_OBSERVATION_DOMAIN,
            parent_migration_receipt_sha256=None,
        )

    def _restore_v2_encoded(self, encoded: bytes) -> None:
        decoded, _payload = self._decode_authenticated_envelope(
            encoded,
            envelope_schema=V2_ENVELOPE_SCHEMA,
            domain=V2_STATE_DOMAIN,
            limit=self._max_encoded_state_bytes,
        )
        expected_state = {
            "actor_ports", "limits", "migration_receipt",
            "recent_applied_receipts", "schema", "world"
        }
        if set(decoded) != expected_state or decoded.get("schema") != V2_STATE_SCHEMA:
            raise ValueError("v2 embodiment state fields changed")
        limits = decoded.get("limits")
        expected_limit_fields = {
            "max_bodies",
            "max_command_bytes",
            "max_encoded_state_bytes",
            "max_objects",
            "receipt_capacity",
        }
        if not isinstance(limits, Mapping) or set(limits) != expected_limit_fields:
            raise ValueError("v2 embodiment authority limits changed")
        _bounded_integer(
            limits.get("max_bodies"),
            "v2 body capacity",
            minimum=2,
            maximum=self._max_bodies,
        )
        _bounded_integer(
            limits.get("max_command_bytes"),
            "v2 command capacity",
            minimum=64,
            maximum=self._max_command_bytes,
        )
        prior_state_capacity = _bounded_integer(
            limits.get("max_encoded_state_bytes"),
            "v2 encoded state capacity",
            minimum=4096,
            maximum=self._max_encoded_state_bytes,
        )
        prior_object_capacity = _bounded_integer(
            limits.get("max_objects"),
            "v2 object capacity",
            minimum=1,
            maximum=self._max_objects,
        )
        prior_receipt_capacity = _bounded_integer(
            limits.get("receipt_capacity"),
            "v2 receipt capacity",
            minimum=1,
            maximum=4096,
        )
        if len(encoded) > prior_state_capacity:
            raise ValueError("v2 embodiment state exceeded its own byte capacity")
        if decoded.get("actor_ports") != [
            item.as_record() for item in self._actor_ports
        ]:
            raise ValueError("v2 actor port topology changed")
        raw_receipts = decoded.get("recent_applied_receipts")
        if (
            not isinstance(raw_receipts, list)
            or len(raw_receipts) > prior_receipt_capacity
            or any(not isinstance(item, Mapping) for item in raw_receipts)
        ):
            raise ValueError("v2 retained execution receipts changed")
        world_value = decoded.get("world")
        expected_world = {
            "bodies", "objects", "revision", "room_bounds", "room_id",
            "self_body_id"
        }
        if not isinstance(world_value, Mapping) or set(world_value) != expected_world:
            raise ValueError("v2 world state fields changed")
        raw_bodies = world_value.get("bodies")
        raw_objects = world_value.get("objects")
        if (
            not isinstance(raw_bodies, list)
            or not 2 <= len(raw_bodies) <= limits["max_bodies"]
            or not isinstance(raw_objects, list)
            or not 1 <= len(raw_objects) <= prior_object_capacity
        ):
            raise ValueError("v2 physical inventory changed")
        prior_revision = _bounded_integer(
            world_value.get("revision"),
            "v2 world revision",
            minimum=0,
            maximum=MAX_REVISION - 1,
        )
        room_id = _identifier(world_value.get("room_id"), "v2 room id")
        room_bounds = _room_from(world_value.get("room_bounds"))
        self_body_id = _identifier(
            world_value.get("self_body_id"), "v2 self body id"
        )
        if self_body_id != self._state.world.self_body_id:
            raise ValueError("v2 self body identity changed")
        bodies = tuple(_body_from(item) for item in raw_bodies)
        objects = tuple(_legacy_object_from(item) for item in raw_objects)
        v2_world_record = {
            "bodies": [item.as_record() for item in bodies],
            "objects": [],
            "revision": prior_revision,
            "room_bounds": room_bounds.as_record(),
            "room_id": room_id,
            "self_body_id": self_body_id,
        }
        for item in objects:
            record = item.as_record()
            del record["reflectance_ppm"]
            v2_world_record["objects"].append(record)
        if v2_world_record != dict(world_value):
            raise ValueError("v2 world state is not canonical")
        parent_migration_receipt_sha256 = None
        parent = decoded.get("migration_receipt")
        if parent is not None:
            if (
                not isinstance(parent, Mapping)
                or parent.get("schema") != V2_MIGRATION_SCHEMA
            ):
                raise ValueError("v2 migration receipt changed")
            parent_migration_receipt_sha256 = _sha256_identity(
                parent.get("authority_receipt_sha256"),
                "v2 migration receipt",
            )
        prior_observation_unsigned = {
            **v2_world_record,
            "schema": V2_OBSERVATION_SCHEMA,
            "state_sha256": _digest(v2_world_record),
        }
        self._commit_migrated_world(
            encoded=encoded,
            prior_revision=prior_revision,
            prior_room_id=room_id,
            prior_room_bounds=room_bounds,
            prior_bodies=bodies,
            prior_objects=objects,
            prior_observation_unsigned=prior_observation_unsigned,
            prior_observation_domain=V2_OBSERVATION_DOMAIN,
            parent_migration_receipt_sha256=parent_migration_receipt_sha256,
        )

    def restore_encoded(self, encoded: bytes) -> None:
        """Atomically restore one exact authenticated authority snapshot."""
        if not isinstance(encoded, bytes) or not encoded or len(encoded) > LEGACY_MAX_ENCODED_STATE_BYTES:
            raise ValueError("encoded embodiment state exceeds its exact byte capacity")
        try:
            envelope_probe = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("embodiment state envelope is not canonical JSON") from error
        if isinstance(envelope_probe, Mapping) and envelope_probe.get("schema") == LEGACY_ENVELOPE_SCHEMA:
            self._restore_legacy_encoded(encoded)
            return
        if isinstance(envelope_probe, Mapping) and envelope_probe.get("schema") == V2_ENVELOPE_SCHEMA:
            self._restore_v2_encoded(encoded)
            return
        decoded, _payload = self._decode_authenticated_envelope(
            encoded,
            envelope_schema=ENVELOPE_SCHEMA,
            domain=STATE_DOMAIN,
            limit=self._max_encoded_state_bytes,
        )
        expected_state = {
            "actor_ports", "limits", "migration_receipt",
            "recent_applied_receipts", "schema", "world"
        }
        if not isinstance(decoded, Mapping) or set(decoded) != expected_state or decoded.get("schema") != STATE_SCHEMA:
            raise ValueError("embodiment state fields changed")
        expected_limits = {
            "max_regions": self._max_regions,
            "max_portals": self._max_portals,
            "max_bodies": self._max_bodies,
            "max_command_bytes": self._max_command_bytes,
            "max_encoded_state_bytes": self._max_encoded_state_bytes,
            "max_objects": self._max_objects,
            "receipt_capacity": self._receipt_capacity,
        }
        if decoded.get("limits") != expected_limits:
            raise ValueError("embodiment state limits changed")
        if decoded.get("actor_ports") != [item.as_record() for item in self._actor_ports]:
            raise ValueError("embodiment actor port topology changed")
        world_value = decoded.get("world")
        world_expected = {
            "bodies", "objects", "portals", "regions", "revision",
            "room_bounds", "room_id", "self_body_id"
        }
        if not isinstance(world_value, Mapping) or set(world_value) != world_expected:
            raise ValueError("world state fields changed")
        raw_objects = world_value.get("objects")
        raw_bodies = world_value.get("bodies")
        raw_regions = world_value.get("regions")
        raw_portals = world_value.get("portals")
        if not isinstance(raw_bodies, list) or not 2 <= len(raw_bodies) <= self._max_bodies:
            raise ValueError("world body inventory changed")
        if not isinstance(raw_objects, list) or not 1 <= len(raw_objects) <= self._max_objects:
            raise ValueError("world object inventory changed")
        world = _WorldState(
            revision=_bounded_integer(world_value.get("revision"), "world revision", minimum=0, maximum=MAX_REVISION),
            room_id=_identifier(world_value.get("room_id"), "room id"),
            room_bounds=_room_from(world_value.get("room_bounds")),
            regions=tuple(_region_from(item) for item in raw_regions)
            if isinstance(raw_regions, list) else (),
            portals=tuple(_portal_from(item) for item in raw_portals)
            if isinstance(raw_portals, list) else (),
            self_body_id=_identifier(world_value.get("self_body_id"), "self body id"),
            bodies=tuple(_body_from(item) for item in raw_bodies),
            objects=tuple(_object_from(item) for item in raw_objects),
        )
        self._validate_world(world)
        if world.as_record() != dict(world_value):
            raise ValueError("world state is not canonical")
        raw_receipts = decoded.get("recent_applied_receipts")
        if not isinstance(raw_receipts, list) or len(raw_receipts) > self._receipt_capacity:
            raise ValueError("retained execution receipts exceed capacity")
        receipts = tuple(self._execution_from_record(item) for item in raw_receipts)
        for left, right in zip(receipts, receipts[1:]):
            if left.after != right.before:
                raise ValueError("retained execution chain changed")
        if receipts and receipts[-1].after != self._observation_for(world):
            raise ValueError("retained execution chain does not end at current world")
        migration_value = decoded.get("migration_receipt")
        migration = (
            self._migration_from_record(migration_value, world)
            if migration_value is not None
            else None
        )
        candidate = _AuthorityState(
            world=world,
            recent_applied_receipts=receipts,
            migration_receipt=migration,
        )
        if self._encoded_state_for(candidate) != encoded:
            raise ValueError("embodiment state is not canonical")
        with self._lock:
            before_state = self._state
            try:
                self._commit_authority_state(candidate)
            except BaseException:
                self._state = before_state
                raise

    def status(self) -> dict[str, object]:
        with self._lock:
            world = self._state.world
            self_body = next(
                item for item in world.bodies
                if item.body_id == world.self_body_id
            )
            return {
                "body_capacity": self._max_bodies,
                "body_count": len(world.bodies),
                "body_ids": [item.body_id for item in world.bodies],
                "self_body_id": world.self_body_id,
                "held_object_id": self_body.held_object_id,
                "object_capacity": self._max_objects,
                "object_count": len(world.objects),
                "portal_capacity": self._max_portals,
                "portal_count": len(world.portals),
                "portal_ids": [item.portal_id for item in world.portals],
                "port_id": self.port_id,
                "region_capacity": self._max_regions,
                "region_count": len(world.regions),
                "region_ids": [item.region_id for item in world.regions],
                "actor_ports": [item.as_record() for item in self._actor_ports],
                "migration_receipt_sha256": (
                    self._state.migration_receipt.authority_receipt_sha256
                    if self._state.migration_receipt is not None
                    else None
                ),
                "receipt_capacity": self._receipt_capacity,
                "retained_applied_receipts": len(self._state.recent_applied_receipts),
                "revision": world.revision,
                "room_id": world.room_id,
            }


__all__ = [
    "ActionExecutionReceipt",
    "EmbodiedBody",
    "EmbodiedObject",
    "EmbodimentPort",
    "EmbodimentWorldAuthority",
    "MoveCommand",
    "MAX_VOCAL_SAMPLE_COUNT",
    "MIN_VOCAL_SAMPLE_COUNT",
    "ObservationSnapshot",
    "PORT_ID",
    "SECOND_BODY_PORT_ID",
    "PickCommand",
    "PlaceCommand",
    "VocalizeCommand",
    "VOCAL_SAMPLE_RATE_HZ",
    "PoseMM",
    "PositionMM",
    "PhysicalPortal",
    "PhysicalRegion",
    "RoomBoundsMM",
    "WorldMigrationReceipt",
    "decode_command",
    "encode_command",
]
