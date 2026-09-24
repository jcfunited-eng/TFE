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


def find_supported_continuation(
    current_sensory_key: str,
    active_demand: str,
    meanings: dict[str, Any],
    available_candidates: Sequence[tuple[str, str, Any, str | None, Any]],
    *,
    current_figure: str | None = None,
    current_held: str | None = None,
    body_position: tuple[int, int, int] | None = None,
    target_positions: dict[str, tuple[int, int, int]] | None = None,
    target_figures: dict[str, str] | None = None,
) -> tuple[str, str, Any, str | None, Any] | None:
    """Learned Closed-Loop Continuation Selector:
    Finds which available motor candidate belongs to a sequence actually experienced,
    whose consequence addressed active_demand.

    Returns the unique executable candidate tuple if exactly one is supported and feasible.
    Returns None if zero or multiple conflicting candidates are supported (abstains).
    """
    if not meanings or not available_candidates:
        return None

    # 1. Identify goal states in meanings that relieved active_demand
    goal_keys: set[str] = set()
    for m_key, m_entry in meanings.items():
        consequences = m_entry.get("consequences", {})
        if active_demand == "feeding":
            if int(m_entry.get("fed", 0)) > 0:
                goal_keys.add(m_key)
            elif any(c.get("relief") == "feeding" or int(c.get("intake", 0)) > 0 for c in consequences.values()):
                goal_keys.add(m_key)
        else:
            if any(c.get("relief") == active_demand for c in consequences.values()):
                goal_keys.add(m_key)

    if not goal_keys:
        return None

    # 2. Build predecessor transition graph: S_next -> list of (S_pre, action, target_id)
    predecessors: dict[str, list[tuple[str, str, str | None]]] = {}
    for m_key, m_entry in meanings.items():
        transitions = m_entry.get("transitions", {})
        for act_name, succ_map in transitions.items():
            for succ_key, info in succ_map.items():
                tgt_id = info.get("target_id") if isinstance(info, dict) else None
                predecessors.setdefault(succ_key, []).append((m_key, act_name, tgt_id))

    # Helper to check if a meaning state matches current sensory condition
    def _state_matches_current(s_key: str) -> bool:
        if current_sensory_key:
            return current_sensory_key == s_key
        return False

    supported_from_current: list[tuple[str, str | None]] = []

    # If current state itself is a goal state, terminal action (like bite) may be directly afforded
    for g_key in goal_keys:
        if _state_matches_current(g_key):
            m_entry = meanings.get(g_key, {})
            consequences = m_entry.get("consequences", {})
            for act_name, c_info in consequences.items():
                if active_demand == "feeding" and (c_info.get("relief") == "feeding" or int(c_info.get("intake", 0)) > 0):
                    supported_from_current.append((act_name, c_info.get("target_id")))
            if active_demand == "feeding" and int(m_entry.get("fed", 0)) > 0:
                supported_from_current.append(("bite", None))

    # Backward search from all goals to current_sensory_key
    queue = list(goal_keys)
    visited_nodes: set[str] = set(goal_keys)
    visited_edges: set[tuple[str, str, str | None, str]] = set()

    leads_to_goal: dict[str, set[tuple[str, str | None]]] = {}

    while queue:
        curr = queue.pop(0)
        for pre_key, act, tgt in predecessors.get(curr, []):
            edge = (pre_key, act, tgt, curr)
            if edge in visited_edges:
                continue
            visited_edges.add(edge)
            leads_to_goal.setdefault(pre_key, set()).add((act, tgt))
            if pre_key not in visited_nodes:
                visited_nodes.add(pre_key)
                queue.append(pre_key)

    # 3. Match current sensory condition against predecessor states that lead to goal
    for state_key, act_set in leads_to_goal.items():
        if _state_matches_current(state_key):
            for act, tgt in act_set:
                supported_from_current.append((act, tgt))

    if not supported_from_current:
        return None

    unique_supported = list(dict.fromkeys(supported_from_current))

    # 4. Intersect with physically available motor candidates
    viable_candidates: list[tuple[str, str, Any, str | None, Any]] = []

    for cand in available_candidates:
        c_act = cand[0]
        c_tgt = cand[3]
        for sup_act, sup_tgt in unique_supported:
            if c_act == sup_act:
                # Target identity verification (Grounded in visual appearance / entity type)
                if c_tgt is not None and sup_tgt is not None and c_tgt != sup_tgt:
                    # Must be same entity category (e.g. apple)
                    if not (c_tgt.startswith("apple") and sup_tgt.startswith("apple")):
                        continue

                # Physical feasibility check:
                # Finite displacement condition 2(v . d) > ||v||^2
                if body_position and target_positions and c_tgt and c_tgt in target_positions:
                    t_pos = target_positions[c_tgt]
                    dx = float(t_pos[0] - body_position[0])
                    dy = float(t_pos[1] - body_position[1])
                    dz = float(t_pos[2] - body_position[2])
                    d_sq = dx * dx + dy * dy + dz * dz
                    if d_sq > 0 and c_act in ("toward_food", "step", "toward_thing"):
                        d_norm = math.sqrt(d_sq)
                        v_step = min(300.0, d_norm)
                        vx = (dx / d_norm) * v_step
                        vy = (dy / d_norm) * v_step
                        vz = (dz / d_norm) * v_step
                        v_sq = vx * vx + vy * vy + vz * vz
                        two_v_dot_d = 2.0 * (vx * dx + vy * dy + vz * dz)
                        if two_v_dot_d <= v_sq:
                            continue

                viable_candidates.append(cand)

    deduped: list[tuple[str, str, Any, str | None, Any]] = []
    seen_sigs = set()
    for c in viable_candidates:
        sig = (c[0], c[1], c[3])
        if sig not in seen_sigs:
            seen_sigs.add(sig)
            deduped.append(c)

    if len(deduped) == 1:
        return deduped[0]

    return None
