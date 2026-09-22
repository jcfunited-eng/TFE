#!/usr/bin/env python3
"""dsf_ai_service/affordance_planner.py — Cognitive Asset 2: Multi-Step Predictive Affordance Planning.

Formalization of the Refrigerator Climbing Principle & Transport Tools:
When internal somatic drives (hunger, distress, exploration) cannot be satisfied by an immediate 1-step
motor action due to physical obstruction, vertical displacement (Delta z > Reach_z), multi-room portal
displacement, or extended travel requirements, the organism executes deterministic inverse affordance
chaining across intermediate environmental entities (tools, elevation supports, vehicles, portals).

Pure deterministic geometry: no statistical ML, no heuristic approximations, no random restarts.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

# Canonical Physical Limits
REACH_HORIZONTAL_MM = 450        # Maximum horizontal limb reach
REACH_VERTICAL_MM = 350          # Maximum upward reach from neutral body stance
STEP_MM = 300                    # Horizontal stride distance per beat
MAX_MANIPULATION_MASS_GRAMS = 10_000  # Objects lighter than 10kg can be pushed/carried


@dataclass(frozen=True)
class AffordanceField:
    """Physical affordance published by an environmental entity."""
    object_id: str
    movable: bool
    mass_grams: int
    support_surface: bool
    elevation_height_mm: int
    is_portal: bool
    is_food: bool
    position: tuple[int, int, int]
    region_id: str | None = None
    connects_regions: tuple[str, str] | None = None
    operates_target: str | None = None
    is_vehicle: bool = False
    can_transport: bool = False
    is_fauna: bool = False
    is_flora: bool = False
    can_emit_sound: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AffordanceField:
        return cls(
            object_id=str(data["object_id"]),
            movable=bool(data.get("movable", False)),
            mass_grams=int(data.get("mass_grams", 0)),
            support_surface=bool(data.get("support_surface", False)),
            elevation_height_mm=int(data.get("elevation_height_mm", 0)),
            is_portal=bool(data.get("is_portal", False)),
            is_food=bool(data.get("is_food", False)),
            position=tuple(data.get("position", (0, 0, 0))),
            region_id=data.get("region_id"),
            connects_regions=tuple(data["connects_regions"]) if data.get("connects_regions") else None,
            operates_target=data.get("operates_target"),
            is_vehicle=bool(data.get("is_vehicle", False)),
            can_transport=bool(data.get("can_transport", False)),
            is_fauna=bool(data.get("is_fauna", False)),
            is_flora=bool(data.get("is_flora", False)),
            can_emit_sound=bool(data.get("can_emit_sound", False)),
        )


@dataclass(frozen=True)
class PlanStep:
    """Atomic step in a multi-step affordance plan."""
    step_index: int
    action: str
    target_id: str | None
    precondition: str
    expected_postcondition: str
    somatic_delta_projected: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanStep:
        return cls(
            step_index=int(data["step_index"]),
            action=str(data["action"]),
            target_id=str(data["target_id"]) if data.get("target_id") is not None else None,
            precondition=str(data.get("precondition", "")),
            expected_postcondition=str(data.get("expected_postcondition", "")),
            somatic_delta_projected=float(data.get("somatic_delta_projected", 0.0)),
        )


@dataclass
class AffordancePlan:
    """Deterministic Multi-Step Affordance Plan Manifold."""
    plan_id: str
    goal: str
    target_object_id: str
    steps: tuple[PlanStep, ...]
    created_tick: int
    terminal_valence: float
    refusal_reason: str | None = None
    status: str = "active"
    current_step_index: int = 0

    @property
    def is_refused(self) -> bool:
        return self.refusal_reason is not None or self.status == "refused"

    @property
    def is_complete(self) -> bool:
        return self.status == "completed" or (len(self.steps) > 0 and self.current_step_index >= len(self.steps))

    def next_step(self) -> PlanStep | None:
        if self.is_refused or self.is_complete or self.current_step_index >= len(self.steps):
            return None
        return self.steps[self.current_step_index]

    def advance_step(self) -> None:
        if self.current_step_index < len(self.steps):
            self.current_step_index += 1
            if self.current_step_index >= len(self.steps):
                self.status = "completed"

    def abort(self, reason: str) -> None:
        self.status = "aborted"
        self.refusal_reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "target_object_id": self.target_object_id,
            "steps": [s.to_dict() for s in self.steps],
            "created_tick": self.created_tick,
            "terminal_valence": self.terminal_valence,
            "refusal_reason": self.refusal_reason,
            "status": self.status,
            "current_step_index": self.current_step_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AffordancePlan:
        return cls(
            plan_id=str(data["plan_id"]),
            goal=str(data["goal"]),
            target_object_id=str(data["target_object_id"]),
            steps=tuple(PlanStep.from_dict(s) for s in data.get("steps", [])),
            created_tick=int(data.get("created_tick", 0)),
            terminal_valence=float(data.get("terminal_valence", 0.0)),
            refusal_reason=data.get("refusal_reason"),
            status=str(data.get("status", "active")),
            current_step_index=int(data.get("current_step_index", 0)),
        )


def evaluate_reachability(
    self_pos: tuple[int, int, int],
    target_pos: tuple[int, int, int],
    reach_h_mm: int = REACH_HORIZONTAL_MM,
    reach_z_mm: int = REACH_VERTICAL_MM,
) -> tuple[bool, float, float]:
    """Evaluates 3D reachability against physical limb bounds.

    Returns:
      (is_reachable, horizontal_distance_mm, vertical_delta_mm)
    """
    dx = target_pos[0] - self_pos[0]
    dy = target_pos[1] - self_pos[1]
    dz = target_pos[2] - self_pos[2]

    horiz_dist = math.hypot(dx, dy)
    is_reachable = (horiz_dist <= reach_h_mm) and (0 <= dz <= reach_z_mm)
    return is_reachable, round(horiz_dist, 2), round(dz, 2)


def extract_affordances(
    objects: Sequence[Any],
    portals: Sequence[Any] = (),
    self_body: Any = None,
    regions: Sequence[Any] = (),
) -> list[AffordanceField]:
    """Extracts physical affordance fields deterministically from world entities."""
    affordances: list[AffordanceField] = []

    for obj in objects:
        pos = (0, 0, 0)
        if hasattr(obj, "position") and obj.position is not None:
            z_val = int(getattr(obj.position, "z", 0))
            if z_val == 0 and getattr(obj, "elevation_mm", 0) > 0:
                z_val = int(getattr(obj, "elevation_mm", 0))
            pos = (int(obj.position.x), int(obj.position.y), z_val)

        mass = int(getattr(obj, "mass_grams", 0))
        obj_id = str(getattr(obj, "object_id", ""))
        radius = int(getattr(obj, "radius_mm", 0))

        # Food affordance: object starts with apple or contains apple/fruit/bread/milk (excluding trees) or declared tastant
        is_food = (
            (obj_id.startswith("apple") or any(token in obj_id.lower() for token in ("apple", "fruit", "bread", "milk", "berry", "biscuit")))
            and not obj_id.startswith("tree")
        ) or getattr(obj, "is_food", False)

        # Vehicle transport affordance: stroller, carriage, wagon, pram
        is_vehicle = any(token in obj_id.lower() for token in ("stroller", "carriage", "wagon", "pram"))
        can_transport = is_vehicle

        # Support surface affordance: chairs, stools, boxes, benches, tables, steps, beds, ladders, vehicle seats
        is_support = any(token in obj_id.lower() for token in ("chair", "stool", "box", "bench", "table", "step", "bed", "ladder")) or is_vehicle
        if "ladder" in obj_id.lower():
            elevation_h = 550
        elif "stool" in obj_id.lower():
            elevation_h = 300
        elif "chair" in obj_id.lower():
            elevation_h = 450
        elif is_vehicle:
            elevation_h = 300
        else:
            elevation_h = radius * 2 if is_support else 0

        # Tool operation affordance: remote operates television
        operates_target = "television" if "remote" in obj_id.lower() else None

        # Living fauna & flora affordances:
        is_fauna = any(token in obj_id.lower() for token in ("bird", "butterfly", "cat", "dog", "squirrel", "rabbit"))
        is_flora = any(token in obj_id.lower() for token in ("flower", "plant", "tree", "bush", "grass"))
        can_emit_sound = any(token in obj_id.lower() for token in ("bird", "television", "radio", "speaker", "bell"))

        # Movability affordance: within mass limit or rollable vehicle, and not fixed structure
        movable = ((mass <= MAX_MANIPULATION_MASS_GRAMS) or is_vehicle) and not any(token in obj_id.lower() for token in ("bed", "table", "wall", "mailbox", "shelf", "tub", "stove", "counter"))

        # Region inference: from object or from enclosing regions bounds
        region_id = getattr(obj, "region_id", None)
        if region_id is None and regions and hasattr(obj, "position") and obj.position is not None:
            for reg in regions:
                if hasattr(reg, "bounds") and reg.bounds.contains_floor_disc(obj.position, getattr(obj, "radius_mm", 0)):
                    region_id = reg.region_id
                    break

        affordances.append(AffordanceField(
            object_id=obj_id,
            movable=movable,
            mass_grams=mass,
            support_surface=is_support,
            elevation_height_mm=elevation_h,
            is_portal=False,
            is_food=is_food,
            position=pos,
            region_id=region_id,
            operates_target=operates_target,
            is_vehicle=is_vehicle,
            can_transport=can_transport,
            is_fauna=is_fauna,
            is_flora=is_flora,
            can_emit_sound=can_emit_sound,
        ))

    # Portals / Doorways
    for portal in portals:
        p_id = str(getattr(portal, "portal_id", ""))
        regions_pair = tuple(getattr(portal, "region_ids", ()))
        affordances.append(AffordanceField(
            object_id=p_id,
            movable=False,
            mass_grams=999_999,
            support_surface=False,
            elevation_height_mm=0,
            is_portal=True,
            is_food=False,
            position=(0, 0, 0),
            connects_regions=regions_pair if len(regions_pair) == 2 else None,
        ))

    return affordances


def plan_tool_operation(
    affordances: Sequence[AffordanceField],
    self_pos: tuple[int, int, int],
    target_tool_id: str = "tv-remote",
    tick: int = 0,
) -> AffordancePlan:
    """Plan tool retrieval and manipulation to operate an environmental appliance (e.g. TV)."""
    tools = [a for a in affordances if a.object_id == target_tool_id or target_tool_id in a.object_id]
    plan_id = hashlib.sha256(f"tool|{self_pos}|{target_tool_id}|{tick}".encode("ascii")).hexdigest()[:12]
    if not tools:
        return AffordancePlan(
            plan_id=plan_id,
            goal=f"operate_{target_tool_id}",
            target_object_id=target_tool_id,
            steps=(),
            created_tick=tick,
            terminal_valence=0.0,
            refusal_reason=f"tool_{target_tool_id}_not_found",
            status="refused",
        )
    tool = tools[0]
    reachable, horiz_dist, dz = evaluate_reachability(self_pos, tool.position)
    if reachable:
        steps = (
            PlanStep(0, "grasp", tool.object_id, "tool_in_reach", "holding_tool"),
            PlanStep(1, "manipulate", tool.object_id, "holding_tool", f"operated_{tool.operates_target or 'target'}", somatic_delta_projected=0.75),
        )
    else:
        steps = (
            PlanStep(0, "toward_thing", tool.object_id, "approach_tool", "near_tool"),
            PlanStep(1, "grasp", tool.object_id, "near_tool", "holding_tool"),
            PlanStep(2, "manipulate", tool.object_id, "holding_tool", f"operated_{tool.operates_target or 'target'}", somatic_delta_projected=0.75),
        )
    return AffordancePlan(
        plan_id=plan_id,
        goal=f"operate_{target_tool_id}",
        target_object_id=tool.object_id,
        steps=steps,
        created_tick=tick,
        terminal_valence=0.75,
        status="active",
    )


def plan_vehicle_journey(
    affordances: Sequence[AffordanceField],
    self_pos: tuple[int, int, int],
    self_region: str | None,
    destination_region: str,
    target_vehicle_id: str = "stroller-carriage",
    tick: int = 0,
) -> AffordancePlan:
    """Plan a mobile journey using a transport vehicle (e.g. stroller) across environmental regions."""
    plan_id = hashlib.sha256(f"vehicle|{self_pos}|{self_region}|{destination_region}|{target_vehicle_id}|{tick}".encode("ascii")).hexdigest()[:12]
    vehicles = [a for a in affordances if a.is_vehicle and (a.object_id == target_vehicle_id or target_vehicle_id in a.object_id)]
    if not vehicles:
        return AffordancePlan(
            plan_id=plan_id,
            goal=f"travel_to_{destination_region}",
            target_object_id=target_vehicle_id,
            steps=(),
            created_tick=tick,
            terminal_valence=0.0,
            refusal_reason=f"vehicle_{target_vehicle_id}_not_found",
            status="refused",
        )
    vehicle = vehicles[0]
    steps: list[PlanStep] = []
    step_idx = 0

    # Phase 1: Transit to vehicle region if organism is in a different region
    vehicle_region = vehicle.region_id or self_region
    if self_region and vehicle_region and self_region != vehicle_region:
        portals = [a for a in affordances if a.is_portal and a.connects_regions]
        queue: deque[tuple[str, list[AffordanceField]]] = deque([(self_region, [])])
        visited = {self_region}
        path_to_vehicle: list[AffordanceField] | None = None
        while queue:
            curr_r, path = queue.popleft()
            if curr_r == vehicle_region:
                path_to_vehicle = path
                break
            for p in portals:
                if not p.connects_regions:
                    continue
                r1, r2 = p.connects_regions
                next_r = r2 if curr_r == r1 else r1 if curr_r == r2 else None
                if next_r and next_r not in visited:
                    visited.add(next_r)
                    queue.append((next_r, path + [p]))
        if not path_to_vehicle:
            return AffordancePlan(
                plan_id=plan_id,
                goal=f"travel_to_{destination_region}",
                target_object_id=vehicle.object_id,
                steps=(),
                created_tick=tick,
                terminal_valence=0.0,
                refusal_reason=f"no_portal_path_connecting_{self_region}_to_vehicle_region_{vehicle_region}",
                status="refused",
            )
        curr_loc = self_region
        for p in path_to_vehicle:
            r1, r2 = p.connects_regions
            dest_loc = r2 if curr_loc == r1 else r1
            steps.append(PlanStep(
                step_index=step_idx,
                action="toward_door",
                target_id=p.object_id,
                precondition=f"in_region_{curr_loc}",
                expected_postcondition=f"in_region_{dest_loc}",
            ))
            step_idx += 1
            curr_loc = dest_loc

    # Phase 2: Approach and mount vehicle
    reachable, horiz_dist, dz = evaluate_reachability(self_pos, vehicle.position)
    if not reachable or (self_region and vehicle_region and self_region != vehicle_region):
        steps.append(PlanStep(
            step_index=step_idx,
            action="toward_vehicle",
            target_id=vehicle.object_id,
            precondition=f"in_region_{vehicle_region}",
            expected_postcondition="near_vehicle",
        ))
        step_idx += 1

    steps.append(PlanStep(
        step_index=step_idx,
        action="mount_vehicle",
        target_id=vehicle.object_id,
        precondition="near_vehicle",
        expected_postcondition="seated_in_vehicle",
        somatic_delta_projected=0.20,
    ))
    step_idx += 1

    # Phase 3: Roll vehicle across portal graph to destination
    if vehicle_region and destination_region and vehicle_region != destination_region:
        portals = [a for a in affordances if a.is_portal and a.connects_regions]
        queue = deque([(vehicle_region, [])])
        visited = {vehicle_region}
        path_to_dest: list[AffordanceField] | None = None
        while queue:
            curr_r, path = queue.popleft()
            if curr_r == destination_region:
                path_to_dest = path
                break
            for p in portals:
                if not p.connects_regions:
                    continue
                r1, r2 = p.connects_regions
                next_r = r2 if curr_r == r1 else r1 if curr_r == r2 else None
                if next_r and next_r not in visited:
                    visited.add(next_r)
                    queue.append((next_r, path + [p]))
        if not path_to_dest:
            return AffordancePlan(
                plan_id=plan_id,
                goal=f"travel_to_{destination_region}",
                target_object_id=vehicle.object_id,
                steps=(),
                created_tick=tick,
                terminal_valence=0.0,
                refusal_reason=f"no_portal_path_connecting_{vehicle_region}_to_{destination_region}",
                status="refused",
            )
        curr_loc = vehicle_region
        for p in path_to_dest:
            r1, r2 = p.connects_regions
            dest_loc = r2 if curr_loc == r1 else r1
            steps.append(PlanStep(
                step_index=step_idx,
                action="traverse_portal_in_vehicle",
                target_id=p.object_id,
                precondition=f"seated_in_region_{curr_loc}",
                expected_postcondition=f"seated_in_region_{dest_loc}",
            ))
            step_idx += 1
            curr_loc = dest_loc

    # Phase 4: Dismount at destination
    steps.append(PlanStep(
        step_index=step_idx,
        action="dismount_vehicle",
        target_id=vehicle.object_id,
        precondition=f"seated_in_region_{destination_region}",
        expected_postcondition=f"arrived_at_{destination_region}",
        somatic_delta_projected=0.70,
    ))

    return AffordancePlan(
        plan_id=plan_id,
        goal=f"travel_to_{destination_region}",
        target_object_id=vehicle.object_id,
        steps=tuple(steps),
        created_tick=tick,
        terminal_valence=0.90,
        status="active",
    )


def plan_need_fulfillment(
    affordances: Sequence[AffordanceField],
    self_pos: tuple[int, int, int],
    self_region: str | None = None,
    hunger_deficit: float = 0.5,
    tick: int = 0,
) -> AffordancePlan:
    """Backward Causal Affordance Planner for somatic need fulfillment.

    Resolves multi-step actions across intermediate elevation tools and portal links.
    """
    plan_id = hashlib.sha256(f"{self_pos}|{self_region}|{hunger_deficit}|{tick}".encode("ascii")).hexdigest()[:12]

    # Step 1: Identify targets that satisfy hunger
    food_candidates = [a for a in affordances if a.is_food]
    if not food_candidates:
        return AffordancePlan(
            plan_id=plan_id,
            goal="quench_hunger",
            target_object_id="none",
            steps=(),
            created_tick=tick,
            terminal_valence=0.0,
            refusal_reason="no_food_entities_available",
            status="refused",
        )

    # Sort food by spatial proximity to organism
    def _dist_to_self(a: AffordanceField) -> float:
        return math.dist(self_pos, a.position)

    food_candidates.sort(key=_dist_to_self)
    target = food_candidates[0]

    # Step 2: Check reachability
    reachable, horiz_dist, dz = evaluate_reachability(self_pos, target.position)

    # Case A: Immediate 1-step reach
    if reachable and (self_region is None or target.region_id is None or target.region_id == self_region):
        steps = (
            PlanStep(0, "grasp", target.object_id, "food_in_reach", "held"),
            PlanStep(1, "bite", target.object_id, "held", "fed", somatic_delta_projected=0.80),
        )
        return AffordancePlan(
            plan_id=plan_id,
            goal="quench_hunger",
            target_object_id=target.object_id,
            steps=steps,
            created_tick=tick,
            terminal_valence=0.80,
            status="active",
        )

    # Case B: Elevated Target (The Refrigerator Problem: dz > REACH_VERTICAL_MM)
    if dz > REACH_VERTICAL_MM:
        # Search for intermediate climbing tool
        support_tools = [
            a for a in affordances
            if a.support_surface and (a.elevation_height_mm + REACH_VERTICAL_MM >= dz)
        ]

        if not support_tools:
            return AffordancePlan(
                plan_id=plan_id,
                goal="quench_hunger",
                target_object_id=target.object_id,
                steps=(),
                created_tick=tick,
                terminal_valence=0.0,
                refusal_reason=f"unreachable_elevation_height_{dz}mm_exceeds_max_support",
                status="refused",
            )

        # Select closest movable tool (or best elevation)
        support_tools.sort(key=lambda t: (not t.movable, math.dist(self_pos, t.position)))
        tool = support_tools[0]

        tool_to_target_dist = math.hypot(tool.position[0] - target.position[0], tool.position[1] - target.position[1])

        # If tool is already adjacent to target (< 500mm):
        if tool_to_target_dist <= 500:
            steps = (
                PlanStep(0, "toward_thing", tool.object_id, "approach_support", "near_support"),
                PlanStep(1, "mount_tool", tool.object_id, "near_support", "elevated_on_support"),
                PlanStep(2, "grasp", target.object_id, "elevated_on_support", "held"),
                PlanStep(3, "bite", target.object_id, "held", "fed", somatic_delta_projected=0.80),
            )
        else:
            # Multi-step manipulation chain: approach tool -> grasp tool -> move tool to target -> release tool -> mount -> grasp -> bite
            if not tool.movable:
                return AffordancePlan(
                    plan_id=plan_id,
                    goal="quench_hunger",
                    target_object_id=target.object_id,
                    steps=(),
                    created_tick=tick,
                    terminal_valence=0.0,
                    refusal_reason=f"support_tool_{tool.object_id}_is_immobile_and_not_adjacent_to_target",
                    status="refused",
                )

            steps = (
                PlanStep(0, "toward_thing", tool.object_id, "approach_tool", "near_tool"),
                PlanStep(1, "grasp", tool.object_id, "near_tool", "holding_tool"),
                PlanStep(2, "toward_food", target.object_id, "holding_tool", "tool_positioned_at_target"),
                PlanStep(3, "release", tool.object_id, "tool_positioned_at_target", "tool_placed"),
                PlanStep(4, "mount_tool", tool.object_id, "tool_placed", "elevated_on_tool"),
                PlanStep(5, "grasp", target.object_id, "elevated_on_tool", "held"),
                PlanStep(6, "bite", target.object_id, "held", "fed", somatic_delta_projected=0.80),
            )

        return AffordancePlan(
            plan_id=plan_id,
            goal="quench_hunger",
            target_object_id=target.object_id,
            steps=steps,
            created_tick=tick,
            terminal_valence=0.80,
            status="active",
        )

    # Case C: Inter-Room Target (Target in different region)
    if self_region and target.region_id and self_region != target.region_id:
        # Search portal graph
        portals = [a for a in affordances if a.is_portal and a.connects_regions]
        # BFS over portals
        queue_portal: deque[tuple[str, list[AffordanceField]]] = deque([(self_region, [])])
        visited_portals = {self_region}
        path_portals: list[AffordanceField] | None = None

        while queue_portal:
            current_r, path = queue_portal.popleft()
            if current_r == target.region_id:
                path_portals = path
                break

            for p in portals:
                if not p.connects_regions:
                    continue
                r1, r2 = p.connects_regions
                next_r = r2 if current_r == r1 else r1 if current_r == r2 else None
                if next_r and next_r not in visited_portals:
                    visited_portals.add(next_r)
                    queue_portal.append((next_r, path + [p]))

        if not path_portals:
            return AffordancePlan(
                plan_id=plan_id,
                goal="quench_hunger",
                target_object_id=target.object_id,
                steps=(),
                created_tick=tick,
                terminal_valence=0.0,
                refusal_reason=f"no_portal_path_connecting_{self_region}_to_{target.region_id}",
                status="refused",
            )

        portal_steps: list[PlanStep] = []
        s_idx = 0
        curr_loc = self_region
        for p in path_portals:
            r1, r2 = p.connects_regions
            dest_loc = r2 if curr_loc == r1 else r1
            portal_steps.append(PlanStep(
                s_idx, "toward_door", p.object_id,
                precondition=f"in_region_{curr_loc}",
                expected_postcondition=f"in_region_{dest_loc}",
            ))
            s_idx += 1
            curr_loc = dest_loc

        portal_steps.append(PlanStep(s_idx, "toward_food", target.object_id, f"in_region_{target.region_id}", "near_food"))
        s_idx += 1
        portal_steps.append(PlanStep(s_idx, "grasp", target.object_id, "near_food", "held"))
        s_idx += 1
        portal_steps.append(PlanStep(s_idx, "bite", target.object_id, "held", "fed", somatic_delta_projected=0.80))

        return AffordancePlan(
            plan_id=plan_id,
            goal="quench_hunger",
            target_object_id=target.object_id,
            steps=tuple(portal_steps),
            created_tick=tick,
            terminal_valence=0.80,
            status="active",
        )

    # Case D: Standard floor navigation (horizontal distance > REACH_HORIZONTAL_MM)
    steps = (
        PlanStep(0, "toward_food", target.object_id, "approach_food", "near_food"),
        PlanStep(1, "grasp", target.object_id, "near_food", "held"),
        PlanStep(2, "bite", target.object_id, "held", "fed", somatic_delta_projected=0.80),
    )
    return AffordancePlan(
        plan_id=plan_id,
        goal="quench_hunger",
        target_object_id=target.object_id,
        steps=steps,
        created_tick=tick,
        terminal_valence=0.80,
        status="active",
    )


__all__ = (
    "AffordanceField",
    "AffordancePlan",
    "PlanStep",
    "evaluate_reachability",
    "extract_affordances",
    "plan_need_fulfillment",
    "plan_tool_operation",
    "plan_vehicle_journey",
    "REACH_HORIZONTAL_MM",
    "REACH_VERTICAL_MM",
    "STEP_MM",
)



def plan_fauna_observation_approach(
    current_pose: tuple[int, int, int],
    target_fauna_id: str,
    affordances: Sequence[AffordanceField],
    current_tick: int = 0,
    observation_distance_mm: int = 1_000,
) -> AffordancePlan:
    """Plan a deterministic multi-step gentle approach to quietly observe garden fauna (bird, butterfly).

    Physics Principle:
    Living fauna startle if approached too rapidly or within flight distance (< 500 mm).
    The organism plans a trajectory that terminates at the gentle observation perimeter (observation_distance_mm),
    orienting toward the fauna's 3D coordinates to allow visual foveation and acoustic recording.
    """
    target = next((a for a in affordances if a.object_id == target_fauna_id), None)
    if target is None:
        return AffordancePlan(
            plan_id=f"plan_fauna_{target_fauna_id}_{current_tick}",
            goal=f"observe_{target_fauna_id}",
            target_object_id=target_fauna_id,
            steps=(),
            created_tick=current_tick,
            terminal_valence=0.0,
            refusal_reason=f"Target fauna {target_fauna_id} not found in affordance field",
            status="refused",
        )

    # Compute Euclidean vector to target
    dx = target.position[0] - current_pose[0]
    dy = target.position[1] - current_pose[1]
    dist_2d = math.hypot(dx, dy)

    steps: list[PlanStep] = []
    step_idx = 0

    # Step 1: orient towards fauna
    heading_deg = int(math.degrees(math.atan2(dy, dx)))
    steps.append(
        PlanStep(
            step_index=step_idx,
            action="orient_toward",
            target_id=target_fauna_id,
            precondition="target_in_visual_horizon",
            expected_postcondition=f"facing_angle_{heading_deg}",
            somatic_delta_projected=0.10,
        )
    )
    step_idx += 1

    # Step 2: walk towards observation boundary if further than observation_distance_mm
    if dist_2d > observation_distance_mm:
        steps.append(
            PlanStep(
                step_index=step_idx,
                action="gentle_approach",
                target_id=target_fauna_id,
                precondition=f"distance_{int(dist_2d)}_mm",
                expected_postcondition=f"at_observation_perimeter_{observation_distance_mm}_mm",
                somatic_delta_projected=0.40,
            )
        )
        step_idx += 1

    # Step 3: quiet observation stance
    steps.append(
        PlanStep(
            step_index=step_idx,
            action="quiet_observe",
            target_id=target_fauna_id,
            precondition="at_observation_perimeter",
            expected_postcondition="foveal_fixation_and_acoustic_capture",
            somatic_delta_projected=0.90,
        )
    )

    return AffordancePlan(
        plan_id=f"plan_fauna_{target_fauna_id}_{current_tick}",
        goal=f"observe_{target_fauna_id}",
        target_object_id=target_fauna_id,
        steps=tuple(steps),
        created_tick=current_tick,
        terminal_valence=0.90,
        status="active",
    )
