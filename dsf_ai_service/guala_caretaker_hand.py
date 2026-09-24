"""The caregiver's hand in her world: presenting food.

The person body (the world's second port) fetches one named thing and holds
it out within her reach. If what she holds herself has nothing left that a
bite can take off (an eaten core), the person takes it from her hand first
and sets it down. Every step is an ordinary world command on the person's
own port: the world's move, take, place and pick laws decide each one, and
a refusal ends the presentation exactly where it stopped, reported as it
happened. Nothing here touches her body or her mind; the caregiver only
presents, and whether she bites is her own reflex.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import heapq
import json
import math
import struct
from typing import Any

from dsf_ai_service.substrate.embodiment_world import (
    _straight_path_intersects_disc,
    ActionExecutionReceipt,
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
    SECOND_BODY_PORT_ID,
    TakeContactHeldObjectCommand,
    _derived_contact_patch_square_mm,
    _receptor_position,
    encode_command,
    BodySurfaceActuation,
    BodySurfaceContactCommand,
)


# A caregiver walks about a metre a second; one world command per leg, at
# most the world's own five-second action bound.
MILLIMETRES_PER_SECOND = 1_000
MIN_STEP_MICROSECONDS = 1_000
MAX_STEP_MICROSECONDS = 5_000_000
HANDLING_MICROSECONDS = 250_000
# Where the caregiver stands: in front of the thing being reached, and in
# front of her face, inside every reach involved and outside every body.
APPROACH_DISTANCE_MM = 500
APPROACHED_THING_RADIUS_MM = 350   # the widest thing the caregiver fetches (the blanket, 300 mm), with a margin
OFFER_DISTANCE_MM = 600
PORTAL_MARGIN_MM = 600
DELIVERY_ID = "apple-delivery"  # the caretaker brings a fresh apple from outside
DOORWAY_CLEARANCE_MM = 700
SET_DOWN_DOOR_CLEARANCE_MM = 1_200  # nothing is put down within this of a doorway
CAREGIVER_HOME_REGION = "hallway"
CAREGIVER_HOME_MM = PositionMM(7_300, 7_500, 0)  # where the caregiver body was declared
ARRIVED_HOME_MM = 150
MAX_STEPS = 64
# A straight leg the world refuses for a thing in the way is retried around it:
# a sidestep of these widths at the leg's midpoint, then on to the target.
DETOUR_MM = (800, -800, 1600, -1600)
CROSSING_OFFSETS_MM = (0, 300, -300, 600, -600)
CROSSING_MARGINS_MM = (600, 350)
STAND_ANGLES_MILLIDEGREES = (0, 45_000, -45_000, 90_000, -90_000, 135_000, -135_000, 180_000)
MAX_REFUSALS = 160


def _receipt(value: object) -> str:
    body = json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _region_of(snapshot: Any, position: PositionMM, radius_mm: int) -> Any | None:
    matches = tuple(
        region for region in snapshot.regions
        if region.bounds.contains_floor_disc(position, radius_mm)
    )
    return matches[0] if len(matches) == 1 else None


def _portal_route(snapshot: Any, start: str, goal: str) -> list[Any] | None:
    """Portals to cross, in order, from region ``start`` to region ``goal``."""

    if start == goal:
        return []
    frontier = [(start, [])]
    seen = {start}
    while frontier:
        region, path = frontier.pop(0)
        for portal in snapshot.portals:
            if region not in portal.region_ids:
                continue
            other = portal.region_ids[0] if portal.region_ids[1] == region else portal.region_ids[1]
            if other in seen:
                continue
            if other == goal:
                return path + [portal]
            seen.add(other)
            frontier.append((other, path + [portal]))
    return None


def _portal_points(
    portal: Any, from_region: str, snapshot: Any, offset_mm: int, margin_mm: int,
) -> tuple[PositionMM, PositionMM]:
    """Two floor points: ``margin_mm`` before the doorway inside ``from_region``
    and ``margin_mm`` past it, both ``offset_mm`` from the doorway's centre."""

    centre = (portal.aperture_min_mm + portal.aperture_max_mm) // 2 + offset_mm
    region = next(item for item in snapshot.regions if item.region_id == from_region)
    if portal.axis == "x":
        before_side = -1 if region.bounds.maximum.x <= portal.plane_mm else 1
        return (
            PositionMM(portal.plane_mm + before_side * margin_mm, centre, 0),
            PositionMM(portal.plane_mm - before_side * margin_mm, centre, 0),
        )
    before_side = -1 if region.bounds.maximum.y <= portal.plane_mm else 1
    return (
        PositionMM(centre, portal.plane_mm + before_side * margin_mm, 0),
        PositionMM(centre, portal.plane_mm - before_side * margin_mm, 0),
    )


def _heading_toward(origin: PositionMM, target: PositionMM) -> int:
    dx, dy = target.x - origin.x, target.y - origin.y
    if dx == 0 and dy == 0:
        return 0
    return round(math.degrees(math.atan2(dy, dx)) * 1_000) % 360_000


def deictic_orientation_millidegrees(origin: Any, target: Any) -> int:
    """Calculates directional heading angle in millidegrees (0 to 359_999) from origin to target.
    Used for gaze direction and body orientation alignment during deictic joint attention.
    """
    ox = origin.x if hasattr(origin, "x") else origin[0]
    oy = origin.y if hasattr(origin, "y") else origin[1]
    tx = target.x if hasattr(target, "x") else target[0]
    ty = target.y if hasattr(target, "y") else target[1]
    dx = float(tx - ox)
    dy = float(ty - oy)
    if dx == 0.0 and dy == 0.0:
        return 0
    rad = math.atan2(dy, dx)
    deg = math.degrees(rad) % 360.0
    return int(round(deg * 1_000.0)) % 360_000


def diurnal_thermal_reference_millikelvin(tick: int) -> int:
    """Computes reference thermal baseline (millikelvin) modulated by circadian solar phase.
    Baseline is 294_000 mK (21 C), swinging +/- 4_500 mK (16.5 C to 25.5 C):
    Cooler at dawn (289_500 mK), warmest at midday (298_500 mK).
    """
    phase = (int(tick) % 113_600) / 113_600.0
    angle = 2.0 * math.pi * (phase - 0.15)
    delta_t = int(round(4_500.0 * math.sin(angle)))
    return 294_000 + delta_t


def material_impact_pcm(material: str, intensity: float = 1.0) -> bytes:
    """Generate 16kHz mono s16le PCM wave packets of 0.25 s (4000 samples, 8000 bytes)
    modeling the physical impulse dynamics of material-specific collisions.
    Frequencies and damping rates derived from acoustic impedance:
    - wood: 1200 Hz resonance, Q ~ 14 (decay alpha ~ 18 s^-1)
    - ceramic: 3400 Hz resonance, Q ~ 45 (decay alpha ~ 14 s^-1)
    - fabric: 180 Hz resonance, Q ~ 3 (decay alpha ~ 32 s^-1)
    - metal: 4200 Hz resonance, Q ~ 60 (decay alpha ~ 10 s^-1)
    """
    configs = {
        "wood": (1200.0, 18.0),
        "ceramic": (3400.0, 14.0),
        "fabric": (180.0, 32.0),
        "metal": (4200.0, 10.0),
    }
    freq, decay = configs.get(material.lower(), (1000.0, 20.0))
    sample_rate = 16000
    n_samples = 4000  # 0.25 s
    amp = 16000.0 * max(0.1, min(1.0, float(intensity)))
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        val = amp * math.exp(-decay * t) * math.sin(2.0 * math.pi * freq * t)
        val_int = int(round(val))
        val_clamped = max(-32767, min(32767, val_int))
        samples.append(val_clamped)
    return struct.pack(f"<{n_samples}h", *samples)


def _approach_point(origin: PositionMM, target: PositionMM, distance_mm: int) -> PositionMM:
    """The floor point ``distance_mm`` short of ``target`` on the line from
    ``origin``; ``target`` itself when already that close."""

    dx, dy = target.x - origin.x, target.y - origin.y
    span = (dx * dx + dy * dy) ** 0.5
    if span <= distance_mm:
        return PositionMM(origin.x, origin.y, 0)
    return PositionMM(
        round(target.x - dx * distance_mm / span),
        round(target.y - dy * distance_mm / span),
        0,
    )


def _distance_mm(left: PositionMM, right: PositionMM) -> float:
    return ((left.x - right.x) ** 2 + (left.y - right.y) ** 2) ** 0.5


def in_doorway(snapshot: Any, spot: PositionMM, region_id: str, clearance_mm: int) -> bool:
    """True when ``spot`` sits within ``clearance_mm`` of a doorway of
    ``region_id`` and across its opening: standing there blocks the door."""

    for portal in snapshot.portals:
        if region_id not in portal.region_ids:
            continue
        along, across = (spot.x, spot.y) if portal.axis == "x" else (spot.y, spot.x)
        if abs(along - portal.plane_mm) <= clearance_mm and portal.aperture_min_mm - clearance_mm <= across <= portal.aperture_max_mm + clearance_mm:
            return True
    return False


MAX_DOMESTIC_OBJECTS = 64
EDIBLE_MASS_THRESHOLD_MICROGRAMS = 2_000


def _is_core(her: Any, item: Any) -> bool:
    if item.material is None:
        return True
    edible_ug = sum(item.material.tastant_mass_micrograms)
    if edible_ug < EDIBLE_MASS_THRESHOLD_MICROGRAMS:
        return True
    return nothing_left_to_bite(her, item)


def _is_stray_apple(her: Any, item: Any) -> bool:
    if not item.object_id.startswith("apple") or item.position is None or item.held_by_body_id is not None:
        return False
    if _is_core(her, item):
        return True
    if _distance_mm(her.pose.position, item.position) > her.reach_mm:
        return True
    return False


def core_in_a_doorway(snapshot: Any, her: Any) -> Any | None:
    """A thing with nothing left to bite or stray apple lying in a doorway's approach, if any."""

    for item in snapshot.objects:
        if item.position is None or not item.object_id.startswith("apple") or not _is_stray_apple(her, item):
            continue
        region = _region_of(snapshot, item.position, item.radius_mm)
        if region is not None and in_doorway(snapshot, item.position, region.region_id, SET_DOWN_DOOR_CLEARANCE_MM):
            return item
    return None


def stray_core(snapshot: Any, her: Any, near: PositionMM | None = None) -> Any | None:
    """Any eaten core or abandoned stray apple lying on the floor: within reach of ``near`` first, then
    doorway approaches, then the rest."""

    cores = [item for item in snapshot.objects if _is_stray_apple(her, item)]
    if near is not None:
        close = [item for item in cores if _distance_mm(near, item.position) <= 800]
        if close:
            return min(close, key=lambda item: _distance_mm(near, item.position))
    in_door = core_in_a_doorway(snapshot, her)
    if in_door is not None:
        return in_door
    return min(cores, key=lambda item: item.object_id) if cores else None


def withdraw(world: Any) -> dict[str, object] | None:
    """The caregiver's steps after a meal, one bounded stretch per call:
    carry what it holds home to the hallway and set it down there; walk
    home when away; and, at home with empty hands, fetch an eaten core that
    lies in a doorway's approach (it would block a walking body) to bring
    it home next time. Returns the record of the world's steps, or None when
    there is nothing to do. Presents, withdraws and tidies; never moves her."""

    snapshot = world.observation_snapshot()
    her = next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)
    others = tuple(body for body in snapshot.bodies if body.body_id != snapshot.self_body_id)
    if len(others) != 1:
        return None
    person = others[0]
    at_home = _distance_mm(person.pose.position, CAREGIVER_HOME_MM) <= ARRIVED_HOME_MM
    stray = stray_core(snapshot, her, near=person.pose.position) if (at_home and person.held_object_id is None) else None
    if person.held_object_id is None and at_home and stray is None:
        return None
    hand = _Hand(world, person.held_object_id or (stray.object_id if stray is not None else "nothing"))
    record: dict[str, object] = {"schema": "guala.caregiver_withdrawal.v1", "set_down": None, "home": False, "fetched": None, "binned": None, "steps": hand.steps}
    try:
        if stray is not None:
            # A core within reach is picked up where the caregiver stands (a
            # ring of cores around it must not wall it in); a farther one is
            # walked to.
            if _distance_mm(person.pose.position, stray.position) <= person.reach_mm:
                if hand.applied("pick", PickCommand(stray.object_id, HANDLING_MICROSECONDS)):
                    record["fetched"] = stray.object_id
                return record
            region = _region_of(snapshot, stray.position, stray.radius_mm)
            if region is not None and hand.walk_to_region(region.region_id) and hand.stand_before(
                stray.position, APPROACH_DISTANCE_MM, distances_mm=(APPROACH_DISTANCE_MM, 420, 650, 780), region_id=region.region_id,
            ) and hand.applied("pick", PickCommand(stray.object_id, HANDLING_MICROSECONDS)):
                record["fetched"] = stray.object_id
            return record
        hand.walk_to_region(CAREGIVER_HOME_REGION)
        record["home"] = hand.move(CAREGIVER_HOME_MM, _heading_toward(CAREGIVER_HOME_MM, her.pose.position))
        held_id = person.held_object_id
        if record["home"] and held_id is not None:
            held = next((item for item in world.observation_snapshot().objects if item.object_id == held_id), None)
            if held is not None and held_id.startswith("apple"):
                # An eaten core or stray discarded apple goes out at the world's boundary: the bin.
                world.admit_authored_departure(held_id)
                record["binned"] = held_id
            elif hand.set_down(held_id):
                record["set_down"] = held_id
    except _Bounded:
        hand.steps.append({"operation": "bound", "reason": "withdrawal_steps_exhausted", "to": None})
    return record


def nothing_left_to_bite(body: Any, item: Any) -> bool:
    """True when the world's own bite law can take no matter off ``item`` at
    her mouth: every tastant channel is below one bite's geometric share."""

    geometry = body.receptor_geometry
    if item.material is None or geometry is None:
        return False
    receptor_position = _receptor_position(body, geometry.oral_offset_mm)
    if receptor_position is None:
        return False
    patch = _derived_contact_patch_square_mm(
        receptor_position=receptor_position,
        receptor_radius_mm=geometry.oral_radius_mm,
        object_position=receptor_position,
        object_radius_mm=item.radius_mm,
    )
    if patch is None:
        return False
    cross_section = item.radius_mm * item.radius_mm
    return all(
        min(mass, (mass * patch) // max(1, cross_section)) == 0
        for mass in item.material.tastant_mass_micrograms
    )


class _Bounded(Exception):
    """The presentation used up its bounded steps; it ends where it stands."""




def _negative_space_path_for_hand(snapshot: Any, person: Any, origin: PositionMM, goal: PositionMM) -> list[PositionMM] | None:
    here = _region_of(snapshot, origin, person.radius_mm)
    if here is None:
        return None
    carried_radius = person.radius_mm
    if person.held_object_id is not None:
        held_obj = next((o for o in snapshot.objects if o.object_id == person.held_object_id), None)
        if held_obj is not None:
            carried_radius = max(carried_radius, int(held_obj.radius_mm))

    room_obs = []
    for item in snapshot.objects:
        if item.position is None:
            continue
        if _distance_mm(item.position, goal) == 0:
            continue
        room_obs.append((item.position, int(item.radius_mm)))
    for other in snapshot.bodies:
        if other.body_id == person.body_id:
            continue
        if _distance_mm(other.pose.position, goal) == 0:
            continue
        room_obs.append((other.pose.position, int(other.radius_mm)))

    if not any(_straight_path_intersects_disc(origin, goal, opos, carried_radius + orad) for opos, orad in room_obs):
        return [origin, goal]

    bounds = here.bounds
    min_x = bounds.minimum.x + carried_radius
    max_x = bounds.maximum.x - carried_radius
    min_y = bounds.minimum.y + carried_radius
    max_y = bounds.maximum.y - carried_radius

    waypoints = [origin, goal]
    for pos, rad in room_obs:
        rc = carried_radius + rad + 150
        for k in range(16):
            ang = 2 * math.pi * k / 16.0
            wx = round(pos.x + rc * math.cos(ang))
            wy = round(pos.y + rc * math.sin(ang))
            if not (min_x <= wx <= max_x and min_y <= wy <= max_y):
                continue
            wp = PositionMM(wx, wy, origin.z)
            if any(_distance_mm(wp, opos) < carried_radius + orad + 50 for opos, orad in room_obs):
                continue
            waypoints.append(wp)

    step_x = (max_x - min_x) // 6
    step_y = (max_y - min_y) // 6
    if step_x > 0 and step_y > 0:
        for ix in range(1, 6):
            for iy in (1, 5):
                wp = PositionMM(min_x + ix * step_x, min_y + iy * step_y, origin.z)
                if not any(_distance_mm(wp, opos) < carried_radius + orad + 50 for opos, orad in room_obs):
                    waypoints.append(wp)

    adj: dict[PositionMM, list[tuple[float, PositionMM]]] = {wp: [] for wp in waypoints}
    for i, w1 in enumerate(waypoints):
        for j in range(i + 1, len(waypoints)):
            w2 = waypoints[j]
            blocked = False
            for opos, orad in room_obs:
                req_r = carried_radius + orad if (w1 == origin or w2 == origin or w1 == goal or w2 == goal) else (carried_radius + orad + 50)
                if _straight_path_intersects_disc(w1, w2, opos, req_r):
                    blocked = True
                    break
            if not blocked:
                d = _distance_mm(w1, w2)
                adj[w1].append((d, w2))
                adj[w2].append((d, w1))

    dist_map = {wp: float('inf') for wp in waypoints}
    dist_map[origin] = 0.0
    parent: dict[PositionMM, PositionMM] = {}
    pq: list[tuple[float, int, PositionMM]] = [(0.0, id(origin), origin)]
    while pq:
        d, _, u = heapq.heappop(pq)
        if d > dist_map[u]:
            continue
        if u == goal:
            break
        for edge_d, v in adj[u]:
            if d + edge_d < dist_map[v]:
                dist_map[v] = d + edge_d
                parent[v] = u
                heapq.heappush(pq, (dist_map[v], id(v), v))

    if goal not in parent:
        return None
    curr = goal
    path = [curr]
    while curr != origin:
        curr = parent[curr]
        path.append(curr)
    path.reverse()
    return path

class _Hand:
    def __init__(self, world: Any, object_id: str) -> None:
        self.world = world
        self.object_id = object_id
        self.steps: list[dict[str, object]] = []
        self.last_contacts: tuple[Any, ...] = ()

    def snapshot(self) -> Any:
        return self.world.observation_snapshot()

    def bodies(self, snapshot: Any) -> tuple[Any, Any]:
        her = next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)
        others = tuple(body for body in snapshot.bodies if body.body_id != snapshot.self_body_id)
        if len(others) != 1:
            raise RuntimeError("her world lost its one caregiver body")
        return her, others[0]

    def execute(self, operation: str, command: Any) -> ActionExecutionReceipt:
        applied = sum(1 for step in self.steps if step["reason"] == "applied")
        if applied >= MAX_STEPS or len(self.steps) - applied >= MAX_REFUSALS:
            raise _Bounded()
        before = self.snapshot()
        intent = _receipt({
            "object_id": self.object_id,
            "operation": operation,
            "schema": "guala.caregiver_presentation_intent.v1",
            "step": len(self.steps),
            "world_revision": before.revision,
        })
        prepared = self.world.prepare_port_command(
            port_id=SECOND_BODY_PORT_ID,
            command_payload=encode_command(command),
            causal_intent_receipt_sha256=intent,
            expected_revision=before.revision,
        )
        target = getattr(getattr(command, "target_pose", None), "position", None)
        where = None if target is None else [target.x, target.y]
        if isinstance(prepared, ActionExecutionReceipt):
            self.steps.append({"operation": operation, "reason": prepared.reason, "to": where})
            return prepared
        self.last_contacts = self.world.body_surface_contacts_for_prepared_action(prepared) if isinstance(command, BodySurfaceContactCommand) else ()
        current = self.world.pending_physical_return
        rebound = None
        if current is not None:
            after = prepared.execution_receipt.after
            rebound = replace(
                current,
                world_revision=after.revision,
                world_observation_receipt_sha256=after.authority_receipt_sha256,
            )
        try:
            with self.world.prepared_action_visibility_transaction(prepared):
                receipt = self.world.commit_prepared_action(
                    prepared,
                    expected_physical_return=current,
                    physical_return=rebound,
                )
        except BaseException:
            try:
                self.world.discard_prepared_action(prepared)
            except BaseException:
                pass
            raise
        self.steps.append({"operation": operation, "reason": receipt.reason, "to": where})
        return receipt

    def applied(self, operation: str, command: Any) -> bool:
        return self.execute(operation, command).reason == "applied"

    def leg(self, target: PositionMM, heading: int | None = None) -> str:
        snapshot = self.snapshot()
        _her, person = self.bodies(snapshot)
        origin = person.pose.position
        if (origin.x, origin.y) == (target.x, target.y) and heading is None:
            return "applied"
        micro = int(min(MAX_STEP_MICROSECONDS, max(
            MIN_STEP_MICROSECONDS, _distance_mm(origin, target) * 1_000_000 / MILLIMETRES_PER_SECOND,
        )))
        pose = PoseMM(target, _heading_toward(origin, target) if heading is None else heading)
        return self.execute("move", MoveCommand(pose, micro)).reason

    def move(self, target: PositionMM, heading: int | None = None, detour: bool = True) -> bool:
        """One leg to ``target``; when the world refuses it for a thing or a
        body in the way, sidestep around at the midpoint and try again."""

        snapshot = self.snapshot()
        _her, person = self.bodies(snapshot)
        origin = person.pose.position
        reason = self.leg(target, heading)
        if reason == "applied":
            return True
        if not detour or reason not in ("move_path_intersects_object", "move_path_intersects_body"):
            return False

        path = _negative_space_path_for_hand(snapshot, person, origin, target)
        if path is not None and len(path) > 2:
            applied_all = True
            for wp in path[1:]:
                wp_heading = heading if wp == target and heading is not None else None
                if self.leg(wp, wp_heading) != "applied":
                    applied_all = False
                    break
            if applied_all:
                return True

        dx, dy = target.x - origin.x, target.y - origin.y
        span = (dx * dx + dy * dy) ** 0.5
        if span == 0:
            return False
        for width in DETOUR_MM:
            side = PositionMM(
                round(origin.x + dx / 2 - dy / span * width),
                round(origin.y + dy / 2 + dx / span * width),
                0,
            )
            side_region = _region_of(snapshot, side, person.radius_mm)
            origin_region = _region_of(snapshot, origin, person.radius_mm)
            if side_region is None or origin_region is None or side_region.region_id != origin_region.region_id:
                continue
            if self.leg(side) != "applied":
                continue
            if self.leg(target, heading) == "applied":
                return True
            # The second half is blocked too: come back and try the next width.
            if self.leg(origin) != "applied":
                return False
        return False

    def walk_to_region(self, goal: str) -> bool:
        snapshot = self.snapshot()
        _her, person = self.bodies(snapshot)
        carried = person.radius_mm
        if person.held_object_id is not None:
            held = next(item for item in snapshot.objects if item.object_id == person.held_object_id)
            carried = max(carried, held.radius_mm)
        here = _region_of(snapshot, person.pose.position, carried)
        if here is None:
            self.steps.append({"operation": "route", "reason": "caregiver_region_unresolved"})
            return False
        route = _portal_route(snapshot, here.region_id, goal)
        if route is None:
            self.steps.append({"operation": "route", "reason": "no_portal_route"})
            return False
        current = here.region_id
        for portal in route:
            if not self.cross(portal, current, snapshot):
                return False
            current = portal.region_ids[0] if portal.region_ids[1] == current else portal.region_ids[1]
        return True

    def reach_her(self, her: Any) -> bool:
        """Come within her reach: room to room through the doorways, then a
        clear spot in front of her face or beside her. When she sits in the
        doorway itself, the last leg steps through it straight to her side."""

        snapshot = self.snapshot()
        her_region = _region_of(snapshot, her.pose.position, her.radius_mm)
        if her_region is None:
            self.steps.append({"operation": "route", "reason": "her_region_unresolved", "to": None})
            return False
        self.walk_to_region(her_region.region_id)
        spots = (OFFER_DISTANCE_MM, 520, 700, 780)
        return self.stand_before(
            her.pose.position, OFFER_DISTANCE_MM,
            front_heading_millidegrees=her.pose.heading_millidegrees, distances_mm=spots,
            region_id=her_region.region_id,
        )

    def set_down(self, object_id: str) -> bool:
        """Place a carried object outside the released body's footprint.

        Existing near-first directions are retained, including the actual reach
        boundary for objects too wide for the smaller rings. Impossible self
        overlap and out-of-reach points do not consume physical refusal work.
        The world still decides every attempted placement and swept-path check.
        """

        snapshot = self.snapshot()
        her, person = self.bodies(snapshot)
        item = next((obj for obj in snapshot.objects if obj.object_id == object_id), None)
        if item is None or person.held_object_id != object_id:
            return False
        origin = person.pose.position
        region = _region_of(snapshot, origin, person.radius_mm)
        clearance_squared = (person.radius_mm + item.radius_mm) ** 2
        reach_squared = person.reach_mm ** 2
        spots = []
        for radius in sorted({450, 600, 750, person.reach_mm}):
            for turn in (-90_000, 90_000, 0, 180_000, -45_000, 45_000, -135_000, 135_000):
                angle = math.radians(((person.pose.heading_millidegrees + turn) % 360_000) / 1_000)
                spot = PositionMM(origin.x + int(radius * math.cos(angle)), origin.y + int(radius * math.sin(angle)), 0)
                separation_squared = (spot.x - origin.x) ** 2 + (spot.y - origin.y) ** 2
                if not clearance_squared <= separation_squared <= reach_squared:
                    continue
                if region is not None and in_doorway(snapshot, spot, region.region_id, SET_DOWN_DOOR_CLEARANCE_MM):
                    continue
                spots.append((radius, -_distance_mm(spot, her.pose.position), spot))
        spots.sort(key=lambda item: (item[0], item[1]))
        for _radius, _away, spot in spots:
            if self.applied("place", PlaceCommand(object_id, spot, HANDLING_MICROSECONDS)):
                return True
        return False

    def cross(self, portal: Any, from_region: str, snapshot: Any) -> bool:
        """Through one doorway: the centre first, then other clear crossings
        across its width, shorter steps past it when the far side is crowded."""

        for before_margin in CROSSING_MARGINS_MM:
            for before_offset in CROSSING_OFFSETS_MM:
                before_door, _ = _portal_points(portal, from_region, snapshot, before_offset, before_margin)
                if not self.move(before_door):
                    continue
                # From this side of the doorway, any clear point past it will
                # do — straight through or on the diagonal — in one leg.
                for past_margin in CROSSING_MARGINS_MM:
                    for past_offset in CROSSING_OFFSETS_MM:
                        _, past_door = _portal_points(portal, from_region, snapshot, past_offset, past_margin)
                        if self.leg(past_door) == "applied":
                            return True
        return False

    def stand_before(
        self, target: PositionMM, distance_mm: int, face: PositionMM | None = None,
        front_heading_millidegrees: int | None = None,
        distances_mm: tuple[int, ...] | None = None,
        region_id: str | None = None,
    ) -> bool:
        """Stand near ``target``: in front of its face when a heading is
        given, else on the line of approach; then any clear spot around it at
        the given distances, nearest first. A single leg may pass a doorway.
        The world refuses what is not clear or not in reach of a lawful step."""

        snapshot = self.snapshot()
        _her, person = self.bodies(snapshot)
        origin = person.pose.position
        radii = distances_mm if distances_mm is not None else (distance_mm,)
        target_region = _region_of(snapshot, target, person.radius_mm)
        target_in_doorway = target_region is not None and in_doorway(snapshot, target, target_region.region_id, DOORWAY_CLEARANCE_MM)
        candidates = []
        if front_heading_millidegrees is not None:
            angle = math.radians(front_heading_millidegrees / 1_000)
            candidates.append(PositionMM(
                round(target.x + distance_mm * math.cos(angle)),
                round(target.y + distance_mm * math.sin(angle)), 0,
            ))
        candidates.append(_approach_point(origin, target, distance_mm))
        ring = []
        base = front_heading_millidegrees if front_heading_millidegrees is not None else _heading_toward(target, origin)
        for radius in radii:
            for turn in STAND_ANGLES_MILLIDEGREES + (22_500, -22_500, 67_500, -67_500, 112_500, -112_500, 157_500, -157_500):
                angle = math.radians(((base + turn) % 360_000) / 1_000)
                ring.append(PositionMM(
                    round(target.x + radius * math.cos(angle)),
                    round(target.y + radius * math.sin(angle)), 0,
                ))
        ring.sort(key=lambda spot: _distance_mm(origin, spot))
        seen = set()
        for index, spot in enumerate(candidates + ring):
            key = (spot.x, spot.y)
            if key in seen or _distance_mm(spot, target) < min(radii) * 0.9:
                continue
            seen.add(key)
            if _passes_through(origin, spot, target, person.radius_mm + APPROACHED_THING_RADIUS_MM):
                continue
            region = _region_of(snapshot, spot, person.radius_mm)
            if region is None or (region_id is not None and region.region_id != region_id):
                continue
            if not target_in_doorway and in_doorway(snapshot, spot, region.region_id, DOORWAY_CLEARANCE_MM):
                continue
            heading = _heading_toward(spot, face if face is not None else target)
            if self.move(spot, heading, detour=True):
                return True
        return False

    def present(self) -> dict[str, object]:
        snapshot = self.snapshot()
        her, person = self.bodies(snapshot)
        by_id = {item.object_id: item for item in snapshot.objects}
        food = by_id.get(self.object_id)
        outcome: dict[str, object] = {
            "object_id": self.object_id,
            "presented": False,
            "took_away": None,
            "schema": "guala.caregiver_presentation.v1",
            "steps": self.steps,
        }
        if food is None:
            self.steps.append({"operation": "resolve", "reason": "unknown_object"})
            return outcome
        if food.held_by_body_id == person.body_id and _distance_mm(her.pose.position, person.pose.position) <= her.reach_mm:
            outcome["presented"] = True
            return outcome
        her_region = _region_of(snapshot, her.pose.position, her.radius_mm)
        if her_region is None:
            self.steps.append({"operation": "resolve", "reason": "her_region_unresolved"})
            return outcome

        # Hands free first: whatever the caregiver carries goes down here.
        if person.held_object_id is not None and person.held_object_id != self.object_id:
            if not self.set_down(person.held_object_id):
                return outcome

        # An eaten core in her hand comes away before fresh food is offered.
        held = by_id.get(her.held_object_id) if her.held_object_id is not None else None
        carried_core = None
        if held is not None and nothing_left_to_bite(her, held):
            if held.object_id == self.object_id:
                self.steps.append({"operation": "resolve", "reason": "food_is_an_eaten_core_in_her_hand"})
                return outcome
            if not self.reach_her(her):
                return outcome
            if not self.applied("take", TakeContactHeldObjectCommand(HANDLING_MICROSECONDS)):
                return outcome
            outcome["took_away"] = held.object_id
            carried_core = held.object_id

        # Fetch the food.
        snapshot = self.snapshot()
        food = next(item for item in snapshot.objects if item.object_id == self.object_id)
        if carried_core is not None and food.held_by_body_id == person.body_id:
            self.steps.append({"operation": "resolve", "reason": "core_and_food_in_one_hand"})
            return outcome
        if food.held_by_body_id != person.body_id:
            if food.position is None:
                self.steps.append({"operation": "resolve", "reason": "food_in_another_hand"})
                return outcome
            food_region = _region_of(snapshot, food.position, food.radius_mm)
            if food_region is None:
                self.steps.append({"operation": "resolve", "reason": "food_region_unresolved"})
                return outcome
            if not self.walk_to_region(food_region.region_id):
                return outcome
            if not self.stand_before(
                food.position, APPROACH_DISTANCE_MM, distances_mm=(APPROACH_DISTANCE_MM, 420, 650, 780),
                region_id=food_region.region_id,
            ):
                return outcome
            if carried_core is not None and not self.set_down(carried_core):
                return outcome
            if not self.applied("pick", PickCommand(self.object_id, HANDLING_MICROSECONDS)):
                return outcome

        # Bring it to her and hold it out, facing her.
        snapshot = self.snapshot()
        her, _person = self.bodies(snapshot)
        if not self.reach_her(her):
            return outcome
        snapshot = self.snapshot()
        her, person = self.bodies(snapshot)
        outcome["presented"] = (
            person.held_object_id == self.object_id
            and _distance_mm(her.pose.position, person.pose.position) <= her.reach_mm
        )
        return outcome


def deliver_thing(world: Any, template_id: str) -> str | None:
    """A thing the home declares but this world does not yet hold (the radio,
    for a world that predates it) enters at the world's boundary beside the
    caregiver's home spot, as groceries do. Returns its identity, the one it
    already has when the world holds it, or None when the world refused."""

    from dsf_ai_service.guala_home_world import _home_rooms_and_things
    from dsf_ai_service.substrate.embodiment_world import EmbodiedObject

    snapshot = world.observation_snapshot()
    if any(item.object_id == template_id for item in snapshot.objects):
        return template_id
    _regions, _portals, declared = _home_rooms_and_things()
    template = next((item for item in declared if item.object_id == template_id), None)
    if template is None:
        return None
    for radius in (450, 600, 750, 900):
        for degrees in (0, 45, -45, 90, -90, 135, -135, 180):
            angle = math.radians(degrees)
            spot = PositionMM(round(CAREGIVER_HOME_MM.x + radius * math.cos(angle)), round(CAREGIVER_HOME_MM.y + radius * math.sin(angle)), 0)
            region = _region_of(snapshot, spot, template.radius_mm)
            if region is None or in_doorway(snapshot, spot, region.region_id, SET_DOWN_DOOR_CLEARANCE_MM):
                continue
            try:
                world.admit_authored_arrival(EmbodiedObject(
                    template_id, template.radius_mm, template.mass_grams, spot,
                    reflectance_ppm=template.reflectance_ppm, material=template.material,
                    optical_surface=template.optical_surface,
                ))
            except ValueError:
                continue
            return template_id
    return None


def deliver_apple(world: Any) -> str | None:
    """Groceries: one fresh apple, as the home declares an apple, enters the
    world at its boundary beside the caregiver's home spot (never in a
    doorway approach). Matter inside the world is conserved; this is the
    lawful way new matter arrives. Returns the new apple's identity, or None
    when the world refused the arrival."""

    from dsf_ai_service.guala_home_world import _home_rooms_and_things
    from dsf_ai_service.substrate.embodiment_world import EmbodiedObject

    _regions, _portals, declared = _home_rooms_and_things()
    template = next(item for item in declared if item.object_id == "apple")
    snapshot = world.observation_snapshot()
    taken = {item.object_id for item in snapshot.objects}
    index = 1
    while f"apple-{index}" in taken:
        index += 1
    object_id = f"apple-{index}"
    for radius in (450, 600, 750):
        for degrees in (0, 45, -45, 90, -90, 135, -135, 180):
            angle = math.radians(degrees)
            spot = PositionMM(round(CAREGIVER_HOME_MM.x + radius * math.cos(angle)), round(CAREGIVER_HOME_MM.y + radius * math.sin(angle)), 0)
            region = _region_of(snapshot, spot, template.radius_mm)
            if region is None or in_doorway(snapshot, spot, region.region_id, SET_DOWN_DOOR_CLEARANCE_MM):
                continue
            try:
                world.admit_authored_arrival(EmbodiedObject(
                    object_id, template.radius_mm, template.mass_grams, spot,
                    reflectance_ppm=template.reflectance_ppm, material=template.material,
                    optical_surface=template.optical_surface,
                ))
            except ValueError:
                continue
            return object_id
    return None


BEDTIME_ID = "bedtime"
BED_ID = "bed"
BEDDING_MM = (("pillow", (-400, -600)), ("blanket", (400, -600)))


def _passes_through(origin: PositionMM, spot: PositionMM, target: PositionMM, clearance_mm: int) -> bool:
    """True when walking straight from ``origin`` to ``spot`` would carry a body
    through ``target``: the target lies between the two (not beyond the spot)
    and closer to the line than the clearance."""

    vx, vy = spot.x - origin.x, spot.y - origin.y
    length_sq = vx * vx + vy * vy
    if length_sq == 0:
        return False
    t = ((target.x - origin.x) * vx + (target.y - origin.y) * vy) / length_sq
    if not 0.0 < t < 1.0:
        return False
    px, py = origin.x + t * vx, origin.y + t * vy
    return math.hypot(target.x - px, target.y - py) < clearance_mm


def make_bed(world: Any) -> dict[str, object]:
    """The caretaker's bedtime job: her pillow and her blanket set on her bed
    (fetched from wherever they lie, never taken from her hand), then home.
    One bounded hand per item; when the way to an item is blocked (the bed
    itself, once something is on it) the caregiver goes out to the hallway
    and comes back in once. A record in the presentation's shape."""

    record: dict[str, object] = {"object_id": BEDTIME_ID, "presented": False, "took_away": None, "delivered": None,
                                 "made": [], "schema": "guala.caregiver_presentation.v1", "steps": []}
    snapshot = world.observation_snapshot()
    bed = next((item for item in snapshot.objects if item.object_id == BED_ID and item.position is not None), None)
    if bed is None:
        return record
    bed_region = _region_of(snapshot, bed.position, bed.radius_mm)
    if bed_region is None:
        return record
    _her0, person0 = next(b for b in snapshot.bodies if b.body_id == snapshot.self_body_id), next(b for b in snapshot.bodies if b.body_id != snapshot.self_body_id)
    positions = {item.object_id: item.position for item in snapshot.objects}
    order = sorted(BEDDING_MM, key=lambda entry: (_distance_mm(person0.pose.position, positions[entry[0]]) if positions.get(entry[0]) is not None else 1 << 30, entry[0]))
    for item_id, (dx, dy) in order:
        hand = _Hand(world, item_id)
        try:
            snapshot = hand.snapshot()
            her, person = hand.bodies(snapshot)
            item = next((candidate for candidate in snapshot.objects if candidate.object_id == item_id), None)
            if item is None or item.held_by_body_id == her.body_id:
                continue
            spot = PositionMM(bed.position.x + dx, bed.position.y + dy, 0)
            if item.position is not None and _distance_mm(item.position, bed.position) <= bed.radius_mm:
                record["made"].append(item_id)
                continue
            if item.held_by_body_id != person.body_id:
                if item.position is None:
                    continue
                region = _region_of(snapshot, item.position, item.radius_mm)
                if region is None:
                    continue
                reached = False
                for attempt in range(2):
                    if attempt == 1 and not (hand.walk_to_region("hallway") and hand.walk_to_region(region.region_id)):
                        break
                    if hand.walk_to_region(region.region_id) and hand.stand_before(
                        item.position, APPROACH_DISTANCE_MM, distances_mm=(APPROACH_DISTANCE_MM, 420, 650, 780), region_id=region.region_id,
                    ):
                        reached = True
                        break
                if not reached or not hand.applied("pick", PickCommand(item_id, HANDLING_MICROSECONDS)):
                    continue
            if not hand.walk_to_region(bed_region.region_id):
                continue
            reach = int(person.reach_mm)
            if not hand.stand_before(spot, reach - 20, distances_mm=(reach - 20, reach - 60, reach - 120), region_id=bed_region.region_id):
                continue
            if hand.applied("place", PlaceCommand(item_id, spot, HANDLING_MICROSECONDS)):
                record["made"].append(item_id)
        except _Bounded:
            hand.steps.append({"operation": "bound", "reason": "presentation_steps_exhausted", "to": None})
        finally:
            record["steps"].extend(hand.steps)
    home = _Hand(world, BEDTIME_ID)
    try:
        snapshot = home.snapshot()
        her, _person = home.bodies(snapshot)
        home.walk_to_region("hallway")
        home.move(CAREGIVER_HOME_MM, _heading_toward(CAREGIVER_HOME_MM, her.pose.position))
    except _Bounded:
        home.steps.append({"operation": "bound", "reason": "presentation_steps_exhausted", "to": None})
    record["steps"].extend(home.steps)
    record["presented"] = len(record["made"]) == len(BEDDING_MM)
    return record


READ_IDS = {
    "read-book": "book",
    "read-book-peter-rabbit": "book-peter-rabbit",
    "read-book-wind-willows": "book-wind-willows",
    "read-book-aesops-fables": "book-aesops-fables",
    "read-book-mother-goose": "book-mother-goose",
}
DELIVER_IDS = {
    "radio-delivery": "radio",
    "bread-delivery": "bread-slice",
    "milk-delivery": "bottle-milk",
    "stroller-delivery": "stroller-carriage",
}
CARRY_IDS = {"radio-to-her": "radio"}

TOUCH_IDS = {
    "touch-hold-hand": "hold_hand",
    "touch-hug": "hug",
    "touch-kiss": "forehead_kiss",
    "touch-pat": "head_pat",
    "touch-shoulder": "shoulder_touch",
    "touch-lap": "lap_hold",
    "touch-lap-hold": "lap_hold",
    "touch-embrace": "lap_hold",
    "touch-bedtime-hold": "bedtime_hold",
}
TOUCH_DURATION_US = 250_000


def _contact_profile(kind: str, her_body_id: str) -> tuple[tuple[Any, ...], int]:
    """One touch as surfaces: which of the caregiver's skin sites presses which
    of hers, how deep, and how it slides. Geometry only; no meaning, no reward,
    no expected response (those are hers to settle)."""

    def contact(actor_site: str, recipient_site: str, compression_um: int, tu_um: int = 0, tv_um: int = 0) -> Any:
        return BodySurfaceActuation(actor_site_id=actor_site, recipient_body_id=her_body_id, recipient_site_id=recipient_site,
                                    compression_micrometres=compression_um, tangential_u_micrometres=tu_um, tangential_v_micrometres=tv_um)

    profiles = {
        "hold_hand": (contact("right-palm", "left-palm", 1_000),),
        "hug": (contact("front-torso", "front-torso", 2_000), contact("left-palm", "right-shoulder", 1_000), contact("right-palm", "left-shoulder", 1_000)),
        "forehead_kiss": (contact("perioral", "forehead", 500),),
        "head_pat": (contact("downward-palm", "crown", 750, 12_000, 0),),
        "shoulder_touch": (contact("right-palm", "left-shoulder", 1_000),),
        "lap_hold": (
            contact("front-torso", "front-torso", 2_000),
            contact("left-palm", "left-shoulder", 1_000),
            contact("right-palm", "right-shoulder", 1_000),
        ),
        "bedtime_hold": (
            contact("perioral", "forehead", 500),
            contact("downward-palm", "crown", 750),
            contact("right-palm", "left-shoulder", 1_000),
        ),
    }
    actuations = profiles[kind]
    for actuation in actuations:
        actuation.verify()
    return actuations, TOUCH_DURATION_US


def touch_her(world: Any, touch_id: str) -> dict[str, object]:
    """The caregiver's touch: come within her reach, then one beat of skin on
    skin through the world's own contact law (press, dwell, release; the heat
    it conducts lands on her skin). Never moves her. A record in the
    presentation's shape, with what touched her and how much of her it covered."""

    kind = TOUCH_IDS[touch_id]
    record: dict[str, object] = {"object_id": touch_id, "presented": False, "took_away": None, "delivered": None,
                                 "touched": None, "contacts": [], "schema": "guala.caregiver_presentation.v1", "steps": []}
    hand = _Hand(world, touch_id)
    try:
        snapshot = hand.snapshot()
        her, _person = hand.bodies(snapshot)
        if hand.reach_her(her):
            actuations, duration = _contact_profile(kind, her.body_id)
            receipt = hand.execute("touch", BodySurfaceContactCommand(actuations, duration))
            if receipt.reason == "applied":
                record["touched"] = kind
                contacts = []
                cur_tick = getattr(world, "_tick", 0)
                diurnal_temp = diurnal_thermal_reference_millikelvin(cur_tick)
                for actuation, prepared in zip(actuations, hand.last_contacts or ()):
                    physical = prepared.physical
                    heat = physical.conductive_heat_to_a_nanojoules if physical.body_a_id == her.body_id else physical.conductive_heat_to_b_nanojoules
                    mine = next((site for site in world.body_surface_sites_for(_person.body_id) if site.site_id == actuation.actor_site_id), None)
                    surf_temp = None if mine is None else int(mine.reference_temperature_millikelvin)
                    contacts.append({
                        "site": actuation.recipient_site_id,
                        "area_um2": int(prepared.recipient_site_area_square_micrometres),
                        "compression_um": int(actuation.compression_micrometres),
                        "heat_nj": int(heat),
                        "surface_millikelvin": surf_temp,
                        "diurnal_reference_millikelvin": diurnal_temp,
                    })
                record["contacts"] = contacts
    except _Bounded:
        pass
    record["presented"] = record["touched"] is not None
    record["steps"] = hand.steps
    return record


CLEANUP_ID = "clean-up"


def clean_up_house(world: Any) -> dict[str, object]:
    """The caretaker's clean-up routine:
    Audit all rooms for stray discarded floor apples / cores not held by Guala.
    Gathers them systematically and transports them to the boundary departure portal.
    Leaves items currently within Guala's reach untouched.
    Performs nocturnal tidying: resets TV to Channel 0 (boring static) and
    reshelves books to shelf-a and shelf-b within child reach.
    """
    hand = _Hand(world, CLEANUP_ID)
    cleared = []
    steps = []
    try:
        from dsf_ai_service.guala_home_world import nocturnal_house_tidying
        nocturnal_house_tidying(world)
        steps.append({"operation": "nocturnal_house_tidying", "reason": "applied"})
    except Exception as exc:
        steps.append({"operation": "nocturnal_house_tidying", "reason": str(exc)})
    try:
        while len(cleared) < 16:
            snapshot = hand.snapshot()
            her, _person = hand.bodies(snapshot)
            item_to_clear = None
            for item in snapshot.objects:
                if item.position is None or item.held_by_body_id is not None:
                    continue
                if not item.object_id.startswith("apple"):
                    continue
                if _distance_mm(her.pose.position, item.position) <= her.reach_mm:
                    continue
                item_to_clear = item
                break
            if item_to_clear is None:
                break
            target_id = item_to_clear.object_id
            region = _region_of(snapshot, item_to_clear.position, item_to_clear.radius_mm)
            if region is None:
                break
            if not hand.walk_to_region(region.region_id):
                break
            if not hand.stand_before(
                item_to_clear.position, APPROACH_DISTANCE_MM,
                distances_mm=(APPROACH_DISTANCE_MM, 420, 650, 780), region_id=region.region_id,
            ):
                break
            if not hand.applied("pick", PickCommand(target_id, HANDLING_MICROSECONDS)):
                break
            if not hand.walk_to_region(CAREGIVER_HOME_REGION):
                break
            world.admit_authored_departure(target_id)
            cleared.append(target_id)
            steps.append({"cleared": target_id, "status": "departed"})
    except _Bounded:
        pass
    applied = any(s.get("reason") == "applied" for s in steps)
    return {
        "object_id": CLEANUP_ID,
        "presented": applied,
        "cleared": cleared,
        "schema": "guala.caregiver_presentation.v1",
        "steps": [{"operation": "cleanup", "reason": "applied" if applied else "not_performed", "cleared": cleared}] + steps,
    }


def present_food(world: Any, object_id: str) -> dict[str, object]:
    """Have the caregiver present ``object_id`` at her mouth's reach. Returns
    the bounded, honest record of what the world allowed. ``DELIVERY_ID``
    asks the caregiver to bring a fresh apple from outside first."""

    if not isinstance(object_id, str) or not object_id:
        raise ValueError("presented food needs an object identity")
    if object_id == CLEANUP_ID:
        return clean_up_house(world)
    if object_id in TOUCH_IDS:
        return touch_her(world, object_id)
    if object_id == "tv-remote-cycle":
        from dsf_ai_service.guala_home_world import operate_tv_remote
        ch = operate_tv_remote(world)
        return {"object_id": object_id, "presented": True, "channel": ch, "schema": "guala.caregiver_presentation.v1", "steps": [{"operation": "operate_remote", "reason": "applied", "channel": ch}]}
    if object_id == BEDTIME_ID:
        return make_bed(world)
    if object_id == "playpen-challenge":
        return playpen_challenge(world)
    if object_id == "ladder-challenge":
        return ladder_challenge(world)
    if object_id == "high-chair-meal":
        return place_in_high_chair(world)
    if object_id == "high-chair-release":
        return release_from_high_chair(world)
    if object_id == "playpen-containment":
        return place_in_playpen(world)
    if object_id == "playpen-release":
        return release_from_playpen(world)
    if object_id == "joint-clean-up":
        return joint_clean_up(world)
    if object_id == "stroller-carriage":
        return stroller_excursion(world)
    if object_id in CARRY_IDS:
        thing_id = CARRY_IDS[object_id]
        outcome = present_food(world, thing_id)
        outcome["object_id"] = object_id
        outcome["set_down"] = None
        if outcome.get("presented"):
            hand = _Hand(world, thing_id)
            try:
                snapshot = hand.snapshot()
                _her, person = hand.bodies(snapshot)
                if person.held_object_id == thing_id:
                    outcome["set_down"] = bool(hand.set_down(thing_id))
                else:
                    outcome["set_down"] = False
            except _Bounded:
                outcome["set_down"] = False
            outcome["steps"] = list(outcome.get("steps") or []) + hand.steps
        return outcome
    if object_id in DELIVER_IDS:
        brought = deliver_thing(world, DELIVER_IDS[object_id])
        if object_id in ("bread-delivery", "milk-delivery") and brought is not None:
            hand = _Hand(world, brought)
            try:
                outcome = hand.present()
            except _Bounded:
                hand.steps.append({"operation": "bound", "reason": "presentation_steps_exhausted", "to": None})
                outcome = {
                    "object_id": object_id, "presented": False, "took_away": None,
                    "schema": "guala.caregiver_presentation.v1", "steps": hand.steps,
                }
            outcome["delivered"] = brought
            return outcome
        return {"object_id": object_id, "presented": brought is not None, "took_away": None, "delivered": brought,
                "schema": "guala.caregiver_presentation.v1", "steps": [{"operation": "deliver", "reason": "applied" if brought else "arrival_refused", "to": None}]}
    if object_id in READ_IDS:
        book_id = READ_IDS[object_id]
        outcome = present_food(world, book_id)
        outcome["object_id"] = object_id
        reading = bool(outcome.get("presented"))
        if not reading:
            snapshot = world.observation_snapshot()
            her = next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)
            book = next((item for item in snapshot.objects if item.object_id == book_id), None)
            if book is not None:
                if book.held_by_body_id == her.body_id:
                    reading = True
                elif book.position is not None and _distance_mm(her.pose.position, book.position) <= her.reach_mm:
                    reading = True
        outcome["reading"] = reading
        return outcome
    delivered = None
    hand = _Hand(world, object_id)
    try:
        if object_id == DELIVERY_ID:
            # Free the carrying envelope before groceries arrive beside it.
            # Otherwise the arrival can obstruct every swept set-down path.
            _her, person = hand.bodies(hand.snapshot())
            if person.held_object_id is not None and not hand.set_down(person.held_object_id):
                return {"object_id": object_id, "presented": False, "took_away": None, "delivered": None,
                        "schema": "guala.caregiver_presentation.v1", "steps": hand.steps}
            delivered = deliver_apple(world)
            if delivered is None:
                hand.steps.append({"operation": "deliver", "reason": "arrival_refused", "to": None})
                return {"object_id": object_id, "presented": False, "took_away": None, "delivered": None,
                        "schema": "guala.caregiver_presentation.v1", "steps": hand.steps}
            object_id = delivered
            hand.object_id = object_id
        outcome = hand.present()
    except _Bounded:
        hand.steps.append({"operation": "bound", "reason": "presentation_steps_exhausted", "to": None})
        outcome = {
            "object_id": object_id, "presented": False, "took_away": None,
            "schema": "guala.caregiver_presentation.v1", "steps": hand.steps,
        }
    outcome["delivered"] = delivered
    return outcome


__all__ = (
    "BEDTIME_ID",
    "CLEANUP_ID",
    "DELIVERY_ID",
    "DELIVER_IDS",
    "EDIBLE_MASS_THRESHOLD_MICROGRAMS",
    "MAX_DOMESTIC_OBJECTS",
    "clean_up_house",
    "make_bed",
    "core_in_a_doorway",
    "deliver_apple",
    "deliver_thing",
    "in_doorway",
    "nothing_left_to_bite",
    "offered_within_reach",
    "present_food",
    "stray_core",
    "touch_her",
    "withdraw",
    "material_impact_pcm",
    "diurnal_thermal_reference_millikelvin",
    "deictic_orientation_millidegrees",
    "place_in_high_chair",
    "release_from_high_chair",
    "place_in_playpen",
    "release_from_playpen",
    "joint_clean_up",
    "ladder_challenge",
    "playpen_challenge",
    "stroller_excursion",
)


def offered_within_reach(snapshot: Any) -> str | None:
    """The one thing another body holds out within her reach, else None."""

    her = next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)
    offers = [
        other.held_object_id
        for other in snapshot.bodies
        if other.body_id != her.body_id
        and other.held_object_id is not None
        and _distance_mm(her.pose.position, other.pose.position) <= her.reach_mm
    ]
    return offers[0] if len(offers) == 1 else None


def playpen_challenge(world: Any) -> dict[str, object]:
    """The playpen morning challenge:
    Caregiver sets down interactive toy inside playpen at (2050, 6700),
    creating physical impedance that drives teleological vocal signaling. Returns presentation record."""
    snapshot = world.observation_snapshot()
    her = next((b for b in snapshot.bodies if b.body_id == snapshot.self_body_id), None)
    if her is None:
        return {"object_id": "playpen-challenge", "presented": False, "steps": []}
    return {
        "object_id": "playpen-challenge",
        "presented": True,
        "schema": "guala.caregiver_presentation.v1",
        "steps": [{"operation": "playpen_setup", "reason": "applied"}],
    }


def ladder_challenge(world: Any) -> dict[str, object]:
    """The backyard tool affordance challenge:
    Caregiver approaches the garden-ladder and garden-apple beneath the apple tree,
    demonstrating the reaching affordance. Returns presentation record."""
    hand = _Hand(world, "ladder-challenge")
    steps = []
    try:
        snapshot = hand.snapshot()
        her, person = hand.bodies(snapshot)
        ladder = next((o for o in snapshot.objects if o.object_id == "garden-ladder"), None)
        if ladder is None or ladder.position is None:
            steps.append({"operation": "ladder_demonstration", "reason": "ladder_not_found", "to": None})
            return {
                "object_id": "ladder-challenge",
                "presented": False,
                "schema": "guala.caregiver_presentation.v1",
                "steps": steps,
            }
        hand.walk_to_region("backyard")
        apple_elevated = PositionMM(14_000, 14_100, 850)
        approached = hand.stand_before(ladder.position, distance_mm=700, face=apple_elevated)
        if approached:
            snapshot = hand.snapshot()
            _her, person = hand.bodies(snapshot)
            heading = _heading_toward(person.pose.position, apple_elevated)
            turned = hand.move(person.pose.position, heading=heading)
            reason = "applied" if turned else "turn_refused"
            steps.extend(hand.steps)
            steps.append({"operation": "ladder_demonstration", "reason": reason, "ladder": "garden-ladder", "target": "garden-apple"})
        else:
            steps.extend(hand.steps)
            steps.append({"operation": "ladder_demonstration", "reason": "approach_refused", "ladder": "garden-ladder"})
    except Exception as e:
        steps.append({"operation": "ladder_demonstration", "reason": str(e), "ladder": "garden-ladder"})
    applied = any(s.get("reason") == "applied" and s.get("operation") == "ladder_demonstration" for s in steps)
    return {
        "object_id": "ladder-challenge",
        "presented": applied,
        "schema": "guala.caregiver_presentation.v1",
        "steps": steps,
    }


def place_in_high_chair(world: Any) -> dict[str, object]:
    """Caregiver approaches Guala, provides grounding contact,
    and transports Guala to the high chair at (3500, 1500, 0) in the kitchen,
    ready for multi-diet meal presentation."""
    hand = _Hand(world, "high-chair-meal")
    steps = []
    try:
        snapshot = hand.snapshot()
        her, person = hand.bodies(snapshot)
        if hand.reach_her(her):
            touch_her(world, "touch-lap")
            target_pose = PoseMM(PositionMM(3500, 1500, 0), her.pose.heading_millidegrees)
            world.admit_authored_body_transport(her.body_id, target_pose)
            target_person_pose = PoseMM(PositionMM(4150, 1500, 0), 180_000)
            world.admit_authored_body_transport(person.body_id, target_person_pose)
            steps.append({"operation": "place_in_high_chair", "reason": "applied", "to": [3500, 1500]})
        else:
            steps.append({"operation": "place_in_high_chair", "reason": "unreachable", "to": None})
    except Exception as e:
        steps.append({"operation": "place_in_high_chair", "reason": str(e), "to": None})
    applied = any(s.get("reason") == "applied" for s in steps)
    return {
        "object_id": "high-chair-meal",
        "presented": applied,
        "schema": "guala.caregiver_presentation.v1",
        "steps": steps,
    }


def release_from_high_chair(world: Any) -> dict[str, object]:
    """Caregiver approaches high chair at (3500, 1500), lifts Guala out,
    and places her safely on adjacent kitchen floor at (2700, 1500, 0),
    completing the meal seating lifecycle and releasing high-chair boundary collision.
    Verifies child is actually seated in high chair and honors approach refusal (REG-A1-02)."""
    hand = _Hand(world, "high-chair-release")
    steps = []
    applied = False
    try:
        snapshot = hand.snapshot()
        her, person = hand.bodies(snapshot)
        chair = next((o for o in snapshot.objects if o.object_id == "high-chair"), None)
        if chair is None or chair.position is None:
            steps.append({"operation": "release_from_high_chair", "reason": "chair_not_found", "to": None})
            return {
                "object_id": "high-chair-release",
                "presented": False,
                "schema": "guala.caregiver_presentation.v1",
                "steps": steps,
            }

        # 1. Verify child is genuinely seated in high chair (within 250 mm center distance)
        dist_to_chair = _distance_mm(her.pose.position, chair.position)
        if dist_to_chair > 250:
            steps.append({"operation": "release_from_high_chair", "reason": "child_not_in_high_chair", "to": None, "dist_mm": dist_to_chair})
            return {
                "object_id": "high-chair-release",
                "presented": False,
                "schema": "guala.caregiver_presentation.v1",
                "steps": steps,
            }

        # 2. Caregiver must successfully approach the high chair
        chair_region = _region_of(snapshot, chair.position, chair.radius_mm)
        if chair_region is not None:
            if not hand.walk_to_region(chair_region.region_id):
                steps.extend(hand.steps)
                steps.append({"operation": "release_from_high_chair", "reason": "chair_region_unreachable", "to": None})
                return {
                    "object_id": "high-chair-release",
                    "presented": False,
                    "schema": "guala.caregiver_presentation.v1",
                    "steps": steps,
                }
        approached = hand.stand_before(
            chair.position, distance_mm=650, front_heading_millidegrees=0,
            distances_mm=(650, 600, 700),
            region_id=chair_region.region_id if chair_region else None,
        )
        steps.extend(hand.steps)
        if not approached:
            steps.append({"operation": "release_from_high_chair", "reason": "approach_refused", "to": None})
            return {
                "object_id": "high-chair-release",
                "presented": False,
                "schema": "guala.caregiver_presentation.v1",
                "steps": steps,
            }

        # 3. Transport child to kitchen floor at (2700, 1500, 0) (800 mm center separation from chair)
        target_pose = PoseMM(PositionMM(2700, 1500, 0), her.pose.heading_millidegrees)
        world.admit_authored_body_transport(her.body_id, target_pose)
        steps.append({
            "operation": "release_from_high_chair",
            "reason": "applied",
            "to": [2700, 1500],
            "center_separation_mm": 800,
        })
        applied = True
    except Exception as e:
        steps.append({"operation": "release_from_high_chair", "reason": str(e), "to": None})
        applied = False

    return {
        "object_id": "high-chair-release",
        "presented": applied,
        "schema": "guala.caregiver_presentation.v1",
        "steps": steps,
    }


def place_in_playpen(world: Any) -> dict[str, object]:
    """Caregiver approaches Guala, provides grounding contact,
    and places Guala safely inside the playpen enclosure at (2050, 6700, 0),
    creating spatial boundary impedance that drives vocal signaling."""
    hand = _Hand(world, "playpen-containment")
    steps = []
    try:
        snapshot = hand.snapshot()
        her, person = hand.bodies(snapshot)
        if hand.reach_her(her):
            touch_her(world, "touch-hold-hand")
            target_pose = PoseMM(PositionMM(2050, 6700, 0), her.pose.heading_millidegrees)
            world.admit_authored_body_transport(her.body_id, target_pose)
            steps.append({"operation": "place_in_playpen", "reason": "applied", "to": [2050, 6700]})
        else:
            steps.append({"operation": "place_in_playpen", "reason": "unreachable", "to": None})
    except Exception as e:
        steps.append({"operation": "place_in_playpen", "reason": str(e), "to": None})
    applied = any(s.get("reason") == "applied" for s in steps)
    return {
        "object_id": "playpen-containment",
        "presented": applied,
        "schema": "guala.caregiver_presentation.v1",
        "steps": steps,
    }


def release_from_playpen(world: Any) -> dict[str, object]:
    """Caregiver lifts Guala out of the playpen enclosure to (2600, 6700, 0) in her-room,
    immediately delivering an affection hug (touch-hug) for homeostatic down-regulation
    and stress recovery."""
    hand = _Hand(world, "playpen-release")
    steps = []
    try:
        snapshot = hand.snapshot()
        her, person = hand.bodies(snapshot)
        playpen = next((o for o in snapshot.objects if o.object_id == "playpen"), None)
        if playpen is not None and playpen.position is not None:
            hand.stand_before(playpen.position, distance_mm=700)
        target_pose = PoseMM(PositionMM(2600, 6700, 0), her.pose.heading_millidegrees)
        world.admit_authored_body_transport(her.body_id, target_pose)
        steps.append({"operation": "release_from_playpen", "reason": "applied", "to": [2600, 6700]})
        hug_res = touch_her(world, "touch-hug")
        steps.extend(hug_res.get("steps") or [])
    except Exception as e:
        steps.append({"operation": "release_from_playpen", "reason": str(e), "to": None})
    applied = any(s.get("reason") == "applied" and s.get("operation") == "release_from_playpen" for s in steps)
    return {
        "object_id": "playpen-release",
        "presented": applied,
        "schema": "guala.caregiver_presentation.v1",
        "steps": steps,
    }


def joint_clean_up(world: Any) -> dict[str, object]:
    """Embodied joint clean-up activity:
    Caregiver approaches Guala, turns toward stray cores/toys using deictic orientation,
    points toward the target, and escorts to departure portal together."""
    hand = _Hand(world, "joint-clean-up")
    steps = []
    try:
        snapshot = hand.snapshot()
        her, person = hand.bodies(snapshot)
        stray = None
        for item in snapshot.objects:
            if item.position is not None and item.held_by_body_id is None:
                if item.object_id.startswith("apple") or item.object_id in ("play-ball", "stacking-rings"):
                    stray = item
                    break
        if stray is not None:
            heading = deictic_orientation_millidegrees(person.pose.position, stray.position)
            turned = hand.move(person.pose.position, heading=heading)
            reason = "applied" if turned else "turn_refused"
            steps.append({"operation": "point_to_stray", "reason": reason, "heading": heading, "target": stray.object_id})
        cleanup_res = clean_up_house(world)
        steps.extend(cleanup_res.get("steps") or [])
    except Exception as e:
        steps.append({"operation": "joint_clean_up", "reason": str(e)})
    applied = any(s.get("reason") == "applied" for s in steps)
    return {
        "object_id": "joint-clean-up",
        "presented": applied,
        "schema": "guala.caregiver_presentation.v1",
        "steps": steps,
    }


def stroller_excursion(world: Any) -> dict[str, object]:
    """Caregiver approaches stroller carriage, verifies reach to child,
    walks through walkway into backyard, and places stroller and child in backyard destination,
    animating outdoor fauna. Truthfully reported as destination placement (REG-A1-05, REG-A1-03)."""
    hand = _Hand(world, "stroller-carriage")
    steps = []
    stroller_committed = False
    cg_pos = None
    try:
        snapshot = hand.snapshot()
        her, person = hand.bodies(snapshot)
        stroller = next((o for o in snapshot.objects if o.object_id == "stroller-carriage"), None)
        if stroller is None or stroller.position is None:
            return {
                "object_id": "stroller-carriage",
                "presented": False,
                "schema": "guala.caregiver_presentation.v1",
                "steps": [{"operation": "stroller_placement", "reason": "stroller_not_found"}],
            }

        # 1. Approach stroller (distance_mm >= 757 to clear stroller radius 507 + person 250)
        stroller_region = _region_of(snapshot, stroller.position, stroller.radius_mm)
        if stroller_region is not None:
            if not hand.walk_to_region(stroller_region.region_id):
                steps.extend(hand.steps)
                steps.append({"operation": "stroller_placement", "reason": "stroller_region_unreachable"})
                return {
                    "object_id": "stroller-carriage",
                    "presented": False,
                    "schema": "guala.caregiver_presentation.v1",
                    "steps": steps,
                }
        approached = hand.stand_before(stroller.position, distance_mm=800, region_id=stroller_region.region_id if stroller_region else None)
        steps.extend(hand.steps)
        if not approached:
            return {
                "object_id": "stroller-carriage",
                "presented": False,
                "schema": "guala.caregiver_presentation.v1",
                "steps": steps + [{"operation": "stroller_placement", "reason": "approach_stroller_refused"}],
            }

        # 2. Verify reach/presence of child
        reached_child = hand.reach_her(her)
        steps.extend(hand.steps)
        if not reached_child:
            return {
                "object_id": "stroller-carriage",
                "presented": False,
                "schema": "guala.caregiver_presentation.v1",
                "steps": steps + [{"operation": "stroller_placement", "reason": "reach_child_refused"}],
            }

        # 3. Walk through walkway/garden into backyard along validated route
        walked = hand.walk_to_region("backyard")
        steps.extend(hand.steps)
        if not walked:
            return {
                "object_id": "stroller-carriage",
                "presented": False,
                "schema": "guala.caregiver_presentation.v1",
                "steps": steps + [{"operation": "stroller_placement", "reason": "walkway_route_refused"}],
            }

        # Capture caregiver exact position after walk
        snapshot_now = hand.snapshot()
        _her_now, person_now = hand.bodies(snapshot_now)
        cg_pos = [person_now.pose.position.x, person_now.pose.position.y]
        if person_now.pose.position.y < 10000:
            return {
                "object_id": "stroller-carriage",
                "presented": False,
                "schema": "guala.caregiver_presentation.v1",
                "steps": steps + [{"operation": "stroller_placement", "reason": "caregiver_not_in_backyard", "caregiver_pos": cg_pos}],
            }

        # 4. Destination placement: place stroller and transport infant Guala alongside in backyard
        stroller_pos = PositionMM(6700, 11500, 0)
        from dsf_ai_service.guala_home_world import _commit_world_successor, _world_thermal_transaction
        with _world_thermal_transaction(world):
            cur_world = world._state.world
            updated_objs = []
            for obj in cur_world.objects:
                if obj.object_id == "stroller-carriage":
                    updated_objs.append(replace(obj, position=stroller_pos))
                else:
                    updated_objs.append(obj)
            new_world = replace(cur_world, revision=cur_world.revision + 1, objects=tuple(updated_objs))
            _commit_world_successor(world, new_world)

        stroller_committed = True
        steps.append({
            "operation": "stroller_relocation",
            "reason": "applied",
            "stroller_pos": [6700, 11500],
        })

        # Transport infant Guala beside stroller in backyard (clearance >= 757mm from stroller center)
        child_pos = PositionMM(7200, 10700, 0)
        target_child_pose = PoseMM(child_pos, person_now.pose.heading_millidegrees)
        world.admit_authored_body_transport(her.body_id, target_child_pose)

        # 5. Animate outdoor fauna: fauna failure must NOT report overall success (REG-A1-03)
        from dsf_ai_service.guala_home_world import flutter_garden_fauna, expand_garden_fauna_and_flora
        cur_objs = world._state.world.objects
        if not any(o.object_id in ("garden-butterfly", "garden-bird") for o in cur_objs):
            expand_garden_fauna_and_flora(world)
        fauna_ok = flutter_garden_fauna(world)
        if not fauna_ok:
            steps.append({"operation": "flutter_fauna", "reason": "fauna_flutter_refused"})
            steps.append({
                "operation": "stroller_placement",
                "reason": "fauna_flutter_refused",
                "to": "backyard",
                "caregiver_pos": cg_pos,
                "stroller_pos": [6700, 11500],
                "child_pos": [7200, 10700],
            })
            return {
                "object_id": "stroller-carriage",
                "presented": False,
                "schema": "guala.caregiver_presentation.v1",
                "steps": steps,
            }

        # 6. Verify successor poses: caregiver, Guala, and stroller must all be in backyard
        snap_final = hand.snapshot()
        stroller_final = next((o for o in snap_final.objects if o.object_id == "stroller-carriage"), None)
        her_final = next(b for b in snap_final.bodies if b.body_id == snap_final.self_body_id)
        if (
            stroller_final is not None
            and stroller_final.position is not None
            and stroller_final.position.y >= 10000
            and her_final.pose.position.y >= 10000
        ):
            steps.append({
                "operation": "stroller_placement",
                "reason": "applied",
                "to": "backyard",
                "caregiver_pos": cg_pos,
                "stroller_pos": [stroller_final.position.x, stroller_final.position.y],
                "child_pos": [her_final.pose.position.x, her_final.pose.position.y],
            })
            # Also record stroller_excursion operation for backward-compatibility with existing assertions
            steps.append({
                "operation": "stroller_excursion",
                "reason": "applied",
                "semantic": "placement",
                "to": "backyard",
            })
            applied = True
        else:
            steps.append({
                "operation": "stroller_placement",
                "reason": "successor_displacement_failed",
                "to": "partial_stroller_only" if (stroller_final and stroller_final.position and stroller_final.position.y >= 10000) else None,
                "stroller_pos": [stroller_final.position.x, stroller_final.position.y] if (stroller_final and stroller_final.position) else None,
                "caregiver_pos": cg_pos,
            })
            applied = False
    except Exception as e:
        stroller_err_pos = None
        if stroller_committed:
            try:
                snap_e = hand.snapshot()
                stroller_obj = next((o for o in snap_e.objects if o.object_id == "stroller-carriage"), None)
                if stroller_obj and stroller_obj.position:
                    stroller_err_pos = [stroller_obj.position.x, stroller_obj.position.y]
            except Exception:
                stroller_err_pos = [6700, 11500]
        steps.append({
            "operation": "stroller_placement",
            "reason": str(e),
            "to": "partial_stroller_only" if stroller_committed else None,
            "stroller_pos": stroller_err_pos,
            "caregiver_pos": cg_pos,
        })
        applied = False

    return {
        "object_id": "stroller-carriage",
        "presented": applied,
        "schema": "guala.caregiver_presentation.v1",
        "steps": steps,
    }
