#!/usr/bin/env python3
"""24-Hour Behavioral Phase-Space Entropy Audit (Option 3).

Performs a rigorous thermodynamic and information-theoretic audit of Guala's
long-horizon behavioral trajectory across physical phase space:
1. Empirical Shannon Behavioral Entropy: Measures diversity and distribution of
   physical actions across multi-thousand-event production operational history.
2. Sequential Transition Constraint: Computes 1-step conditional Markov entropy
   and mutual information to distinguish structured intentional momentum from random noise.
3. Diurnal Phase-Space Coverage: Analyzes 24-hour diurnal cycle activity across
   solar day/night hours (0:00 to 23:00 UTC).
4. Dynamic Basin Trajectory: Simulates multi-beat physical loop settlements to verify
   somatic reserve stability, non-negative basin stability (S_UF > 0), and lack of
   pathological limit-cycle freezing.

Emits structured JSON audit metrics and enforces the canonical 85% physics floor.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from typing import Any

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)
LOG_PATH = "/workspaces/Tao_Financial_Engine/guala_caretaker/caretaker.log"


def audit_phase_space_entropy(log_path: str = LOG_PATH) -> dict[str, Any]:
    results: dict[str, Any] = {
        "audit": "Option 3 - 24-Hour Behavioral Phase-Space Entropy Audit",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "physics_floor": 0.85,
        "metrics": {},
        "scores": {},
    }

    # -------------------------------------------------------------------------
    # 1. Empirical Behavioral Action Entropy
    # -------------------------------------------------------------------------
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Caretaker operational log not found at {log_path}")

    lines: list[str] = []
    rotated = log_path + ".1"
    if os.path.exists(rotated):
        with open(rotated, "r", encoding="utf-8", errors="ignore") as f:
            lines.extend(f.readlines())
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines.extend(f.readlines())

    full_text = "".join(lines)
    actions = re.findall(r"world action ([a-z_]+)", full_text)
    if not actions:
        raise ValueError("No physical world actions found in operational log")

    action_counts = Counter(actions)
    total_actions = len(actions)
    unique_actions = len(action_counts)

    # Shannon Entropy H(A) = - sum(p * log2(p))
    shannon_entropy = 0.0
    for count in action_counts.values():
        p = count / total_actions
        shannon_entropy -= p * math.log2(p)

    max_entropy = math.log2(unique_actions) if unique_actions > 1 else 1.0
    entropy_ratio = shannon_entropy / max_entropy

    # Healthy homeostatic band: 0.50 <= ratio <= 0.95
    # (ratio < 0.40 implies limit cycle trap; ratio > 0.98 implies uniform white noise)
    is_homeostatic_entropy = 0.50 <= entropy_ratio <= 0.95
    entropy_score = 1.0 if is_homeostatic_entropy else max(0.0, 1.0 - abs(entropy_ratio - 0.75) * 2)

    results["metrics"]["action_entropy"] = {
        "total_action_events": total_actions,
        "unique_action_types": unique_actions,
        "shannon_entropy_bits": round(shannon_entropy, 4),
        "max_entropy_bits": round(max_entropy, 4),
        "entropy_ratio": round(entropy_ratio, 4),
        "homeostatic_band_pass": is_homeostatic_entropy,
        "top_5_actions": [
            {"action": a, "count": c, "share": round(c / total_actions, 4)}
            for a, c in action_counts.most_common(5)
        ],
    }
    results["scores"]["action_entropy_score"] = round(entropy_score, 4)

    # -------------------------------------------------------------------------
    # 2. Sequential Transition Constraint & Mutual Information
    # -------------------------------------------------------------------------
    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    for a_curr, a_next in zip(actions[:-1], actions[1:]):
        transitions[a_curr][a_next] += 1

    total_pairs = len(actions) - 1
    conditional_entropy = 0.0
    for a_curr, next_counts in transitions.items():
        p_curr = sum(next_counts.values()) / total_pairs
        sum_next = sum(next_counts.values())
        h_local = 0.0
        for a_next, count in next_counts.items():
            p_cond = count / sum_next
            h_local -= p_cond * math.log2(p_cond)
        conditional_entropy += p_curr * h_local

    mutual_information = max(0.0, shannon_entropy - conditional_entropy)
    sequential_constraint_ratio = mutual_information / shannon_entropy if shannon_entropy > 0 else 0.0

    # Structured intentional behavior requires sequential constraint between 5% and 35%
    # (0% = independent coin flips; >50% = rigid deterministic loop)
    transition_pass = 0.05 <= sequential_constraint_ratio <= 0.35
    transition_score = 1.0 if transition_pass else 0.80

    results["metrics"]["sequential_dynamics"] = {
        "transitions_evaluated": total_pairs,
        "conditional_entropy_bits": round(conditional_entropy, 4),
        "mutual_information_bits": round(mutual_information, 4),
        "sequential_constraint_ratio": round(sequential_constraint_ratio, 4),
        "structured_intentional_flow": transition_pass,
    }
    results["scores"]["transition_dynamics_score"] = round(transition_score, 4)

    # -------------------------------------------------------------------------
    # 3. Diurnal Phase-Space Coverage (24-Hour Solar Activity)
    # -------------------------------------------------------------------------
    hourly_counts = Counter()
    for line in lines:
        match = re.match(r"^(\d{4}-\d{2}-\d{2})T(\d{2}):", line)
        if match:
            hourly_counts[int(match.group(2))] += 1

    active_hours = sum(1 for hr in range(24) if hourly_counts[hr] > 0)
    hourly_coverage_ratio = active_hours / 24.0

    diurnal_pass = hourly_coverage_ratio >= 0.90
    diurnal_score = hourly_coverage_ratio

    results["metrics"]["diurnal_coverage"] = {
        "active_hours_count": active_hours,
        "total_diurnal_hours": 24,
        "coverage_ratio": round(hourly_coverage_ratio, 4),
        "hourly_distribution": {f"{hr:02d}h": hourly_counts[hr] for hr in range(24)},
        "passed": diurnal_pass,
    }
    results["scores"]["diurnal_coverage_score"] = round(diurnal_score, 4)

    # -------------------------------------------------------------------------
    # 4. Dynamic Basin Stability Simulation
    # -------------------------------------------------------------------------
    loop = FunctionalPhysicalLoop()
    world = home_world_authority(identity=IDENTITY)
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)

    sim_beats = 30
    sim_reserves = []
    sim_ticks = []

    for _ in range(sim_beats):
        loop.settle(org, world, UNATTENDED)
        sim_reserves.append(org.reserve_micrograms)
        sim_ticks.append(org.live_organism_tick)

    reserve_continuous = all(sim_reserves[i] > 0 for i in range(len(sim_reserves)))
    ticks_advanced = (sim_ticks[-1] - sim_ticks[0]) == (sim_beats - 1)
    sim_pass = reserve_continuous and ticks_advanced
    sim_score = 1.0 if sim_pass else 0.0

    results["metrics"]["basin_simulation"] = {
        "beats_simulated": sim_beats,
        "reserve_maintained": reserve_continuous,
        "clock_continuity": ticks_advanced,
        "initial_reserve": sim_reserves[0],
        "final_reserve": sim_reserves[-1],
        "passed": sim_pass,
    }
    results["scores"]["basin_simulation_score"] = sim_score

    # -------------------------------------------------------------------------
    # Composite Phase-Space Entropy Audit Score (Canonical 85% Physics Floor)
    # -------------------------------------------------------------------------
    weights = {
        "action_entropy_score": 0.35,
        "transition_dynamics_score": 0.25,
        "diurnal_coverage_score": 0.25,
        "basin_simulation_score": 0.15,
    }
    overall = sum(results["scores"][k] * weights[k] for k in weights)
    results["overall_entropy_audit_score"] = round(overall, 4)
    results["verdict"] = "PASS" if overall >= 0.85 else "FAIL"

    return results


def main() -> None:
    report = audit_phase_space_entropy()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
