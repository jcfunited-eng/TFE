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
import json
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
    import math

    return round(math.degrees(math.atan2(dy, dx)) * 1_000) % 360_000


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


def _is_core(her: Any, item: Any) -> bool:
    return item.material is None or nothing_left_to_bite(her, item)


def core_in_a_doorway(snapshot: Any, her: Any) -> Any | None:
    """A thing with nothing left to bite lying in a doorway's approach, if any."""

    for item in snapshot.objects:
        if item.position is None or not item.object_id.startswith("apple") or not _is_core(her, item):
            continue
        region = _region_of(snapshot, item.position, item.radius_mm)
        if region is not None and in_doorway(snapshot, item.position, region.region_id, SET_DOWN_DOOR_CLEARANCE_MM):
            return item
    return None


def stray_core(snapshot: Any, her: Any, near: PositionMM | None = None) -> Any | None:
    """Any eaten core lying on the floor: within reach of ``near`` first, then
    doorway approaches, then the rest."""

    cores = [item for item in snapshot.objects if item.position is not None and item.object_id.startswith("apple") and _is_core(her, item)]
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
            if held is not None and held_id.startswith("apple") and _is_core(her, held):
                # An eaten core goes out at the world's boundary: the bin.
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


class _Hand:
    def __init__(self, world: Any, object_id: str) -> None:
        self.world = world
        self.object_id = object_id
        self.steps: list[dict[str, object]] = []

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
        # Her last interval's physical return, if one is waiting, stays hers:
        # its content is untouched and only its binding follows the world the
        # caregiver just changed, so her next interval still consumes it.
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
        """Put what the caregiver carries on the floor beside it: the first
        spot around it, near first, that the world's place law accepts."""

        import math

        snapshot = self.snapshot()
        her, person = self.bodies(snapshot)
        origin = person.pose.position
        region = _region_of(snapshot, origin, person.radius_mm)
        spots = []
        for radius in (450, 600, 750):
            for turn in (-90_000, 90_000, 0, 180_000, -45_000, 45_000, -135_000, 135_000):
                angle = math.radians(((person.pose.heading_millidegrees + turn) % 360_000) / 1_000)
                spot = PositionMM(round(origin.x + radius * math.cos(angle)), round(origin.y + radius * math.sin(angle)), 0)
                # Never in a doorway's approach (a thing on the floor blocks a
                # walking body), and away from her rather than at her feet.
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

        import math

        snapshot = self.snapshot()
        _her, person = self.bodies(snapshot)
        origin = person.pose.position
        radii = distances_mm if distances_mm is not None else (distance_mm,)
        # The caregiver keeps out of doorways, except that it must be able to
        # reach her wherever she stands: when the target itself is in a
        # doorway's approach, the spots around it are allowed (it steps back
        # out afterwards).
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
            # Never reach a spot by walking through what is approached: the
            # step law would shove a light thing (an apple, the blanket) ahead
            # of the caregiver instead of it arriving beside it.
            if _passes_through(origin, spot, target, person.radius_mm + APPROACHED_THING_RADIUS_MM):
                continue
            region = _region_of(snapshot, spot, person.radius_mm)
            if region is None or (region_id is not None and region.region_id != region_id):
                continue
            if not target_in_doorway and in_doorway(snapshot, spot, region.region_id, DOORWAY_CLEARANCE_MM):
                continue  # the caregiver never lingers in a doorway
            heading = _heading_toward(spot, face if face is not None else target)
            # The first spots are worth a sidestep; the rest are tried straight.
            if self.move(spot, heading, detour=index < len(candidates) + 2):
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

        # An eaten core in her hand comes away before fresh food is offered;
        # it is carried off and set down where the food lies, never at her
        # feet or in a doorway she will walk through.
        held = by_id.get(her.held_object_id) if her.held_object_id is not None else None
        carried_core = None
        if held is not None and nothing_left_to_bite(her, held):
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
            raise RuntimeError("the caregiver cannot hold a core and the food at once")
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


def deliver_apple(world: Any) -> str | None:
    """Groceries: one fresh apple, as the home declares an apple, enters the
    world at its boundary beside the caregiver's home spot (never in a
    doorway approach). Matter inside the world is conserved; this is the
    lawful way new matter arrives. Returns the new apple's identity, or None
    when the world refused the arrival."""

    import math

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
                ))
            except ValueError:
                continue
            return object_id
    return None


BEDTIME_ID = "bedtime"
BED_ID = "bed"
BEDDING_MM = (("pillow", (-400, -600)), ("blanket", (400, -600)))  # where each lies on the bed, from its centre: side by side at the head, near the edge the room side reaches (the bed stands against the far wall; a hand reaches 800 mm)


def _passes_through(origin: PositionMM, spot: PositionMM, target: PositionMM, clearance_mm: int) -> bool:
    """True when walking straight from ``origin`` to ``spot`` would carry a body
    through ``target``: the target lies between the two (not beyond the spot)
    and closer to the line than the clearance."""

    import math

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
    # Nearest first from where the caregiver stands (it comes in from the
    # hallway door): the far item is fetched last, when the room is known.
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
                record["made"].append(item_id)  # already on the bed
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
            # Stand outside the bed within a hand's reach of the spot: the world
            # refuses the spots inside the bed, so the outward ones are taken.
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


def present_food(world: Any, object_id: str) -> dict[str, object]:
    """Have the caregiver present ``object_id`` at her mouth's reach. Returns
    the bounded, honest record of what the world allowed. ``DELIVERY_ID``
    asks the caregiver to bring a fresh apple from outside first."""

    if not isinstance(object_id, str) or not object_id:
        raise ValueError("presented food needs an object identity")
    if object_id == BEDTIME_ID:
        return make_bed(world)
    delivered = None
    if object_id == DELIVERY_ID:
        delivered = deliver_apple(world)
        if delivered is None:
            return {"object_id": object_id, "presented": False, "took_away": None, "delivered": None,
                    "schema": "guala.caregiver_presentation.v1", "steps": [{"operation": "deliver", "reason": "arrival_refused", "to": None}]}
        object_id = delivered
    hand = _Hand(world, object_id)
    try:
        outcome = hand.present()
    except _Bounded:
        hand.steps.append({"operation": "bound", "reason": "presentation_steps_exhausted", "to": None})
        outcome = {
            "object_id": object_id, "presented": False, "took_away": None,
            "schema": "guala.caregiver_presentation.v1", "steps": hand.steps,
        }
    outcome["delivered"] = delivered
    return outcome


__all__ = ("BEDTIME_ID", "DELIVERY_ID", "make_bed", "core_in_a_doorway", "deliver_apple", "in_doorway", "nothing_left_to_bite", "offered_within_reach", "present_food", "stray_core", "withdraw")


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
