#!/usr/bin/env python3
"""dsf_ai_service/episodic_binding_engine.py — Cognitive Asset 1: Learned Closed-Loop Continuation Engine.

Engineered Episodic Continuation Controller (Level 2/3 Spatiotemporal Memory):
Retains genuinely experienced transitions:
  Sensed Condition Before (S_pre) -> Applied Motor Action (A) -> Sensed Condition After (S_post) -> Consequence (C)
without scalar reward ranking, Bellman value equations, discount factors, or hardcoded action priorities.

When an internal bodily demand is active (e.g. feeding):
1. Identifies remembered states whose consequences relieved that demand.
2. Traverses retained predecessor transitions backward (finite traversal, visiting each edge at most once).
3. Connects current sensory evidence to supported paths.
4. Intersects with currently available, physically feasible motor candidates.
5. If exactly one distinct candidate is supported, issues it; otherwise abstains (no pursuit command).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Sequence

# Salience Threshold for immediate single-trial consolidation (The Pool Shock Principle)
SALIENCE_THRESHOLD = 0.65

# Coupling constants for somatic salience computation
K_RESERVE = 0.50      # Weight for significant reserve intake/loss (e.g. 50,000 ug meal)
K_SHOCK = 1.00        # Acute motor inhibition or external trauma
K_BOUNDARY = 0.70     # Physical limit / collision impact
K_PAIN = 1.00         # Nociceptive thermal or mechanical damage
K_SLEEP = 0.30        # Sudden sleep deprivation / restorative collapse


@dataclass(frozen=True)
class EpisodicFrame:
    """Atomic 6-field spatiotemporal episodic manifold."""
    key: str
    tick: int
    room: str
    pose: tuple[int, int]
    visual_figure: str
    acoustic_event: str
    tactile: str
    somatic_delta: float
    action: str
    consequence: str
    salience: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpisodicFrame:
        return cls(
            key=data["key"],
            tick=data["tick"],
            room=data.get("room", "unknown"),
            pose=tuple(data.get("pose", (0, 0))),
            visual_figure=data.get("visual_figure", "none"),
            acoustic_event=data.get("acoustic_event", "none"),
            tactile=data.get("tactile", "none"),
            somatic_delta=float(data.get("somatic_delta", 0.0)),
            action=data.get("action", "rest"),
            consequence=data.get("consequence", "none"),
            salience=float(data.get("salience", 0.0)),
        )


def compute_somatic_salience(
    reserve_delta_ug: int = 0,
    shock_magnitude: float = 0.0,
    boundary_collision: bool = False,
    pain_signal: bool = False,
    sleep_pressure_delta: int = 0,
) -> float:
    """Computes Gamma_salience from internal somatic deltas."""
    # Normalized reserve delta: 100,000 ug (full meal) = 1.0
    norm_reserve = min(1.0, abs(reserve_delta_ug) / 100_000.0)
    norm_sleep = min(1.0, abs(sleep_pressure_delta) / 10_000.0)
    b_val = 1.0 if boundary_collision else 0.0
    p_val = 1.0 if pain_signal else 0.0

    raw = (
        K_RESERVE * norm_reserve
        + K_SHOCK * min(1.0, max(0.0, shock_magnitude))
        + K_BOUNDARY * b_val
        + K_PAIN * p_val
        + K_SLEEP * norm_sleep
    )
    return round(min(1.0, raw), 4)


def create_episodic_key(
    visual_figure: str,
    acoustic_event: str,
    tactile: str,
    room: str,
) -> str:
    """Generates an invariant deterministic content hash for the episode."""
    payload = f"{visual_figure}|{acoustic_event}|{tactile}|{room}"
    return hashlib.sha256(payload.encode("ascii")).hexdigest()[:16]


def should_consolidate(salience: float, count: int = 1) -> bool:
    """Consolidation Law: High-salience events consolidate immediately (trial count = 1).
    Low-salience background events require repetition (count >= 2).
    """
    if salience >= SALIENCE_THRESHOLD:
        return True
    return count >= 2


def evaluate_anticipatory_consequence(
    candidate_act: str,
    *,
    visual_figure: str = "none",
    acoustic_event: str = "none",
    room: str = "unknown",
    meanings: dict[str, Any] | None = None,
    target_id: str | None = None,
    body_position: tuple[int, int, int] | None = None,
    conserved_objects: dict[str, Any] | None = None,
    somatic_deficit: float = 0.0,
) -> tuple[float, str | None]:
    """Anticipatory Trajectory Reactivation:
    Given current perceptual cues and a candidate action, searches stored episodic
    meanings to anticipate somatic consequence before motor actuation.

    Returns:
      (expected_somatic_valence, projected_consequence_reason)
      - Positive valence (> 0.35): promotes action (e.g. food ingestion / comfort)
      - Negative valence (< -0.35): vetoes action (e.g. pain / shock)
      - Zero valence: no anticipatory precedent
    """
    if not meanings:
        return 0.0, None

    for key, entry in meanings.items():
        ep_fig = entry.get("figure") or entry.get("held", "none")
        ep_room = entry.get("room")
        match_visual = (visual_figure != "none" and (visual_figure == ep_fig or visual_figure in str(ep_fig)))
        match_acoustic = (acoustic_event != "none" and (acoustic_event == entry.get("source") or acoustic_event in key or acoustic_event in str(entry.get("context", []))))
        match_room = (ep_room is None or ep_room == "unknown" or room is None or ep_room == room)
        if (match_visual or match_acoustic) and match_room:
            acts = entry.get("acts", {})
            if candidate_act in acts:
                tries, net_valence = acts[candidate_act]
                mean_valence = float(net_valence) / max(1, int(tries))
                if mean_valence < -0.35:
                    return mean_valence, f"vetoed by anticipated trauma ({mean_valence:+.2f}) from prior episode {key[:6]}"
                elif mean_valence > 0.35:
                    return mean_valence, f"promoted by anticipated satisfaction ({mean_valence:+.2f}) from prior episode {key[:6]}"

            if candidate_act == "bite" and entry.get("fed", 0) > 0:
                return 1.0, f"promoted by positive feeding consequence from prior episode {key[:6]}"

    return 0.0, None


def qualifies_for_retention(entry: dict[str, Any]) -> bool:
    """Actual intake is retainable without manufacturing salience or recurrence.

    This is the ratified engineered retention law, not neuronal plasticity.
    Other observations retain their existing recurrence/salience qualification.
    """
    trial = entry.get("motor_transition")
    return (
        isinstance(trial, dict)
        and trial.get("refusal") is None
        and int(trial.get("intake", 0)) > 0
    ) or should_consolidate(float(entry.get("salience", 0.0)), int(entry["count"]))


def consecutive_motor_trials(predecessor: Any, successor: Any) -> bool:
    """A witnessed successful route edge, independent of waypoint names.

    A refusal is not an executable route. Actual intake ends the prior relief
    episode, preventing repeated meals from becoming one unbounded component.
    Exact sensory and chronological continuity remain mandatory.
    """
    return (
        isinstance(predecessor, dict) and isinstance(successor, dict)
        and predecessor.get("refusal") is None
        and successor.get("refusal") is None
        and int(predecessor.get("intake", 0)) == 0
        and predecessor["end_tick"] == successor["start_tick"]
        and predecessor["post"] == successor["pre"]
    )


def retained_episode_keys(moments: dict[str, Any], root: str) -> tuple[str, ...]:
    """A qualifying outcome and its available actually witnessed support.

    Missing historical records end traversal. They are never reconstructed.
    """
    entry = moments[root]
    if not qualifies_for_retention(entry):
        return ()
    keys = [root]
    visited = {root}
    successor = entry.get("motor_transition")
    tail = successor.get("previous") if isinstance(successor, dict) else entry.get("episode_tail")
    while tail in moments and tail not in visited:
        trial = moments[tail].get("motor_transition")
        if not isinstance(trial, dict) or trial.get("refusal") is not None:
            break
        if successor is not None and not consecutive_motor_trials(trial, successor):
            break
        visited.add(tail)
        keys.append(tail)
        successor = trial
        tail = trial.get("previous")
    return tuple(keys)


def bound_waking_moments(
    moments: dict[str, Any], capacity: int, admitted_keys: set[str],
) -> dict[str, Any]:
    """Enforce existing waking storage without tearing a qualified route.

    Actual newly created keys precede old evidence; refreshing an old record
    does not make it new. Qualified episodes precede raw observations.
    Existing count/tick/key order resolves equal storage classes,
    never motor choice. An oversized component is rejected whole, not truncated
    into a purported complete episode or retained beyond capacity.
    """
    if len(moments) <= capacity:
        return moments
    adjacent: dict[str, set[str]] = {key: set() for key in moments}
    roots: set[str] = set()
    for root in moments:
        keys = retained_episode_keys(moments, root)
        if not keys:
            continue
        roots.add(root)
        for left, right in zip(keys, keys[1:]):
            adjacent[left].add(right)
            adjacent[right].add(left)
    groups: list[set[str]] = []
    remaining = set(moments)
    for seed in sorted(moments):
        if seed not in remaining:
            continue
        group: set[str] = set()
        frontier = [seed]
        while frontier:
            key = frontier.pop()
            if key in group:
                continue
            group.add(key)
            frontier.extend(adjacent[key] - group)
        remaining.difference_update(group)
        groups.append(group)
    groups.sort(key=lambda group: (
        bool(group & admitted_keys), bool(group & roots),
        min(int(moments[k]["count"]) for k in group),
        min(int(moments[k]["tick"]) for k in group), min(group),
    ))
    result = dict(moments)
    # Reject impossible groups first so they cannot displace every smaller
    # qualified episode only to be refused themselves.
    for group in groups:
        if len(group) > capacity:
            for key in group:
                result.pop(key, None)
    for group in groups:
        if len(result) <= capacity:
            break
        for key in group:
            result.pop(key, None)
    return result


def bound_retained_episode(
    candidate: dict[str, Any], protected: set[str], capacity: int,
) -> dict[str, Any] | None:
    """Prepare bounded retention without tearing a retained episode apart.

    Eviction changes storage only, never observation counts or action worth.
    The new episode is admitted as a whole or the caller retains its predecessor.
    """
    if len(candidate) <= capacity:
        return candidate
    adjacent: dict[str, set[str]] = {key: set() for key in candidate}
    for key, entry in candidate.items():
        previous = entry.get("motor_transition", {}).get("previous")
        for linked in (entry.get("episode_tail"), previous):
            if linked in adjacent:
                adjacent[key].add(linked)
                adjacent[linked].add(key)
    components: list[set[str]] = []
    remaining = set(candidate)
    for seed in sorted(candidate):
        if seed not in remaining:
            continue
        frontier = [seed]
        component: set[str] = set()
        while frontier:
            key = frontier.pop()
            if key in component:
                continue
            component.add(key)
            frontier.extend(adjacent[key] - component)
        remaining.difference_update(component)
        components.append(component)
    protected_size = sum(len(group) for group in components if group & protected)
    if protected_size > capacity:
        return None
    removable = sorted(
        (group for group in components if not group & protected),
        key=lambda group: (
            min(int(candidate[k].get("count", 1)) for k in group),
            min(int(candidate[k].get("tick", 0)) for k in group),
            min(group),
        ),
    )
    result = dict(candidate)
    for group in removable:
        if len(result) <= capacity:
            break
        for key in group:
            del result[key]
    return result


def find_supported_continuation(
    current_sensory_key: str,
    active_demand: str,
    meanings: dict[str, Any],
    available_candidates: Sequence[tuple[str, str, Any, str | None, Any]],
    *,
    current_target_id: str | None = None,
    current_figure: str | None = None,
    current_held: str | None = None,
    body_position: tuple[int, int, int] | None = None,
    target_positions: dict[str, tuple[int, int, int]] | None = None,
    target_figures: dict[str, str] | None = None,
) -> tuple[str, str, Any, str | None, Any] | None:
    """Read actual retained trials, never invent a terminal act from 'fed'.

    This bounded engineered controller is not full joint-field evaluation.
    Exact available sensory evidence is required; missing vision is not identity.
    Progress checks constrain proposed motion; world settlement remains authority
    for collisions and actual execution.
    """
    if active_demand != "feeding" or not current_sensory_key:
        return None
    # A room/reach category alone cannot recognize the target of an experience.
    if current_figure in (None, "none") and current_held != "held" and not current_target_id:
        return None
    supported: set[str] = set()
    visited: set[str] = set()
    for entry in meanings.values():
        trial = entry.get("motor_transition")
        if not isinstance(trial, dict) or trial.get("refusal") is not None or int(trial["intake"]) <= 0:
            continue
        while isinstance(trial, dict):
            trial_key = trial["key"]
            if trial_key in visited:
                break
            visited.add(trial_key)
            if trial.get("refusal") is not None:
                break
            if (trial["pre"] == current_sensory_key
                    and trial.get("observed_subject") == trial["target"]
                    and trial.get("observed_subject") is not None):
                supported.add(trial["action"])
            previous = trial.get("previous")
            predecessor = meanings.get(previous, {}).get("motor_transition")
            if not isinstance(predecessor, dict):
                break
            if not consecutive_motor_trials(predecessor, trial):
                break
            trial = predecessor

    viable = []
    for candidate in available_candidates:
        act, _detail, commands, target, _drive = candidate
        if act not in supported:
            continue
        # Candidate must concern the current sensory subject, not another object
        # that happens to afford the same verb. IDs bind current custody only.
        if target is not None and target != current_target_id:
            continue
        # Commands are alternatives, not a sequence that must all execute.
        # Keep original payloads/order; the world still accepts or refuses each.
        retained_commands = []
        for command in commands:
            pose = getattr(command, "target_pose", None)
            if pose is not None:
                if body_position is None or not target_positions or target not in target_positions:
                    continue  # no physical displacement evidence for this move
                displacement = tuple(int(t) - int(p) for t, p in zip(target_positions[target], body_position))
                position = pose.position
                step = tuple(int(t) - int(p) for t, p in zip((position.x, position.y, position.z), body_position))
                if 2 * sum(v * d for v, d in zip(step, displacement)) <= sum(v * v for v in step):
                    continue
            retained_commands.append(command)
        if commands and not retained_commands:
            continue
        if len(retained_commands) != len(commands):
            candidate = (act, _detail, tuple(retained_commands), target, _drive)
        if candidate not in viable:
            viable.append(candidate)
    return viable[0] if len(viable) == 1 else None

