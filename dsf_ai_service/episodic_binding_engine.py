#!/usr/bin/env python3
"""dsf_ai_service/episodic_binding_engine.py — Cognitive Asset 1: Valence-Weighted Episodic Binding.

Formalization of the Pool Shock Principle:
High somatic deltas (intense hunger relief, near-fatal boundary collisions,
thermal/galvanic shock) trigger irreversible episodic crystallization into long-term
phase space without requiring arbitrary repetition counts.

Upon encountering similar sensory cues in the future, the stored consequence trajectory
is reactivated to anticipate physical outcomes prior to motor actuation.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any

# Salience Threshold for immediate single-trial consolidation
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
    visual_figure: str,
    acoustic_event: str,
    room: str,
    meanings: dict[str, Any],
    target_id: str | None = None,
    body_position: tuple[int, int, int] | None = None,
    conserved_objects: dict[str, Any] | None = None,
    somatic_deficit: float = 0.0,
) -> tuple[float, str | None]:
    """Anticipatory Trajectory Reactivation:
    Given current perceptual cues, candidate action, and spatial conserved objects,
    searches stored episodic meanings to anticipate somatic consequence before motor actuation.

    Returns:
      (expected_somatic_valence, projected_consequence_reason)
      - Positive valence (> 0.35): promotes action (e.g. food ingestion / approach toward nourishment)
      - Negative valence (< -0.35): vetoes action (e.g. pain / shock)
      - Zero valence: no anticipatory precedent
    """
    # 1. Direct sensory episode matching
    for key, entry in meanings.items():
        ep_fig = entry.get("figure") or entry.get("held", "none")
        ep_room = entry.get("room")

        match_visual = (visual_figure != "none" and (visual_figure == ep_fig or visual_figure in str(ep_fig)))
        match_acoustic = (acoustic_event != "none" and acoustic_event in str(entry.get("context", [])))
        match_room = (ep_room is None or ep_room == "unknown" or room is None or ep_room == room)

        if (match_visual or match_acoustic) and match_room:
            acts = entry.get("acts", {})
            if candidate_act in acts:
                tries, net_valence = acts[candidate_act]
                mean_valence = float(net_valence) / max(1, int(tries))
                if mean_valence < -0.35:
                    return mean_valence, f"vetoed by anticipated shock/harm ({mean_valence:+.2f}) from prior episode {key[:6]}"
                elif mean_valence > 0.35:
                    return mean_valence, f"promoted by anticipated satisfaction ({mean_valence:+.2f}) from prior episode {key[:6]}"

            if candidate_act == "bite" and entry.get("fed", 0) > 0:
                return 1.0, f"promoted by positive feeding consequence from prior episode {key[:6]}"

    # 2. Spatial Attractor Gradient Matching across Conserved Objects
    if conserved_objects and target_id and target_id in conserved_objects:
        c_entry = conserved_objects[target_id]
        c_pos = c_entry.get("position")
        c_fig = c_entry.get("figure_key")
        c_is_food = bool(c_entry.get("is_food"))

        for key, entry in meanings.items():
            ep_fig = entry.get("figure") or entry.get("held", "none")
            ep_room = entry.get("room")
            match_room = (ep_room is None or ep_room == "unknown" or room is None or ep_room == room)
            if not match_room:
                continue

            # Deterministic binding: entity visual figure matches episode, or entity is food and episode was fed
            has_figure_match = (c_fig is not None and c_fig != "none" and (c_fig == ep_fig or c_fig in str(ep_fig)))
            has_food_fed_match = (c_is_food and int(entry.get("fed", 0)) > 0)

            if has_figure_match or has_food_fed_match:
                # Terminal manipulation of the attractor entity
                if candidate_act in ("bite", "grasp", "take"):
                    if int(entry.get("fed", 0)) > 0 and somatic_deficit > 0:
                        return 1.0, f"promoted by terminal feeding consequence on {target_id} from prior episode {key[:6]}"
                    acts = entry.get("acts", {})
                    if candidate_act in acts:
                        tries, net_val = acts[candidate_act]
                        mv = float(net_val) / max(1, int(tries))
                        if mv > 0.35:
                            return mv, f"promoted by manipulation valence on {target_id} from prior episode {key[:6]}"

                # Spatial approach affordance toward the attractor entity
                if candidate_act in ("toward_food", "toward_thing", "toward_person", "step") and c_pos is not None and body_position is not None:
                    dx = float(c_pos[0] - body_position[0])
                    dy = float(c_pos[1] - body_position[1])
                    dz = float(c_pos[2] - body_position[2])
                    dist_mm = math.sqrt(dx * dx + dy * dy + dz * dz)
                    spatial_discount = 1.0 / (1.0 + dist_mm / 2000.0)
                    valence = round(float(somatic_deficit) * spatial_discount, 4)
                    if valence > 0.35:
                        return valence, f"promoted by spatial approach gradient toward {target_id} (D={int(dist_mm)}mm) from prior episode {key[:6]}"

    return 0.0, None
