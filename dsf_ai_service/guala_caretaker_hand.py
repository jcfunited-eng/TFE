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
from dsf_ai_service.substrate.exact_lattice_rotation import rotate_lattice_offset


# A caregiver walks about a metre a second; one world command per leg, at
# most the world's own five-second action bound.
MILLIMETRES_PER_SECOND = 1_000
MIN_STEP_MICROSECONDS = 1_000
MAX_STEP_MICROSECONDS = 5_000_000
HANDLING_MICROSECONDS = 250_000
# Where the caregiver stands: in front of the thing being reached, and in
# front of her face, inside every reach involved and outside every body.
APPROACH_DISTANCE_MM = 500
OFFER_DISTANCE_MM = 600
PORTAL_MARGIN_MM = 600
MAX_STEPS = 24


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


def _portal_waypoints(portal: Any, from_region: str, snapshot: Any) -> tuple[PositionMM, PositionMM]:
    """Two floor points: just before the doorway inside ``from_region`` and
    just past it inside the other region, both on the doorway's centre."""

    centre = (portal.aperture_min_mm + portal.aperture_max_mm) // 2
    region = next(item for item in snapshot.regions if item.region_id == from_region)
    if portal.axis == "x":
        before_side = -1 if region.bounds.maximum.x <= portal.plane_mm else 1
        return (
            PositionMM(portal.plane_mm + before_side * PORTAL_MARGIN_MM, centre, 0),
            PositionMM(portal.plane_mm - before_side * PORTAL_MARGIN_MM, centre, 0),
        )
    before_side = -1 if region.bounds.maximum.y <= portal.plane_mm else 1
    return (
        PositionMM(centre, portal.plane_mm + before_side * PORTAL_MARGIN_MM, 0),
        PositionMM(centre, portal.plane_mm - before_side * PORTAL_MARGIN_MM, 0),
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
        if len(self.steps) >= MAX_STEPS:
            raise RuntimeError("caregiver presentation exceeded its bounded steps")
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
        if isinstance(prepared, ActionExecutionReceipt):
            self.steps.append({"operation": operation, "reason": prepared.reason})
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
        self.steps.append({"operation": operation, "reason": receipt.reason})
        return receipt

    def applied(self, operation: str, command: Any) -> bool:
        return self.execute(operation, command).reason == "applied"

    def move(self, target: PositionMM, heading: int | None = None) -> bool:
        snapshot = self.snapshot()
        _her, person = self.bodies(snapshot)
        origin = person.pose.position
        if (origin.x, origin.y) == (target.x, target.y) and heading is None:
            return True
        micro = int(min(MAX_STEP_MICROSECONDS, max(
            MIN_STEP_MICROSECONDS, _distance_mm(origin, target) * 1_000_000 / MILLIMETRES_PER_SECOND,
        )))
        pose = PoseMM(target, _heading_toward(origin, target) if heading is None else heading)
        return self.applied("move", MoveCommand(pose, micro))

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
            before_door, past_door = _portal_waypoints(portal, current, snapshot)
            if not self.move(before_door) or not self.move(past_door):
                return False
            current = portal.region_ids[0] if portal.region_ids[1] == current else portal.region_ids[1]
        return True

    def stand_before(self, target: PositionMM, distance_mm: int, face: PositionMM | None = None) -> bool:
        snapshot = self.snapshot()
        _her, person = self.bodies(snapshot)
        spot = _approach_point(person.pose.position, target, distance_mm)
        heading = _heading_toward(spot, face if face is not None else target)
        return self.move(spot, heading)

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
            dx, dy = rotate_lattice_offset(person.radius_mm + 200, 0, person.pose.heading_millidegrees)
            down = PositionMM(person.pose.position.x + dx, person.pose.position.y + dy, 0)
            if not self.applied("place", PlaceCommand(person.held_object_id, down, HANDLING_MICROSECONDS)):
                return outcome

        # An eaten core in her hand comes away before fresh food is offered.
        held = by_id.get(her.held_object_id) if her.held_object_id is not None else None
        if held is not None and nothing_left_to_bite(her, held):
            if not self.walk_to_region(her_region.region_id):
                return outcome
            if not self.stand_before(her.pose.position, OFFER_DISTANCE_MM):
                return outcome
            if not self.applied("take", TakeContactHeldObjectCommand(HANDLING_MICROSECONDS)):
                return outcome
            snapshot = self.snapshot()
            _her, person = self.bodies(snapshot)
            dx, dy = rotate_lattice_offset(0, -(person.radius_mm + 200), person.pose.heading_millidegrees)
            down = PositionMM(person.pose.position.x + dx, person.pose.position.y + dy, 0)
            if not self.applied("place", PlaceCommand(held.object_id, down, HANDLING_MICROSECONDS)):
                return outcome
            outcome["took_away"] = held.object_id

        # Fetch the food.
        snapshot = self.snapshot()
        food = next(item for item in snapshot.objects if item.object_id == self.object_id)
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
            if not self.stand_before(food.position, APPROACH_DISTANCE_MM):
                return outcome
            if not self.applied("pick", PickCommand(self.object_id, HANDLING_MICROSECONDS)):
                return outcome

        # Bring it to her and hold it out, facing her.
        if not self.walk_to_region(her_region.region_id):
            return outcome
        snapshot = self.snapshot()
        her, _person = self.bodies(snapshot)
        if not self.stand_before(her.pose.position, OFFER_DISTANCE_MM):
            return outcome
        snapshot = self.snapshot()
        her, person = self.bodies(snapshot)
        outcome["presented"] = (
            person.held_object_id == self.object_id
            and _distance_mm(her.pose.position, person.pose.position) <= her.reach_mm
        )
        return outcome


def present_food(world: Any, object_id: str) -> dict[str, object]:
    """Have the caregiver present ``object_id`` at her mouth's reach. Returns
    the bounded, honest record of what the world allowed."""

    if not isinstance(object_id, str) or not object_id:
        raise ValueError("presented food needs an object identity")
    return _Hand(world, object_id).present()


__all__ = ("nothing_left_to_bite", "offered_within_reach", "present_food")


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
