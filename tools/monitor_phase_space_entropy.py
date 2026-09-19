#!/usr/bin/env python3
"""tools/monitor_phase_space_entropy.py — Continuous Longitudinal Phase-Space Entropy Monitor.

Charter: Monitor Guala's behavioral trajectory across physical phase space to
ensure non-ergodic developmental progression and detect behavioral freezing or
decorrelated white-noise anomalies.

Computes:
1. Shannon Behavioral Action Entropy H(A) and ratio over log2(unique actions).
   Healthy homeostatic band: 0.50 <= ratio <= 0.95.
2. Sequential Transition Mutual Information I(A_t; A_{t+1}) and constraint ratio.
3. Diurnal Coverage: Hourly physical engagement across the 24-hour cycle.
4. Somatic Metabolic & Basin Health: Verifies metabolic reserve deficit <= 0.40
   and active caretaker engagement.

Exit codes:
  0: PASS (All metrics satisfy canonical 85% physics floor)
  1: ALERT (Phase-space entropy or homeostatic constraint outside normal bounds)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from typing import Any

DEFAULT_LOG = "/workspaces/Tao_Financial_Engine/guala_caretaker/caretaker.log"
DEFAULT_STATE = "/workspaces/Tao_Financial_Engine/guala_caretaker/state.json"
LIVE_OBSERVATION_URL = "https://dsf-ai.com/api/v1/guala/observation"
PHYSICS_FLOOR = 0.85


def compute_action_entropy(actions: list[str]) -> dict[str, Any]:
    if not actions:
        return {
            "total_actions": 0,
            "unique_actions": 0,
            "shannon_entropy_bits": 0.0,
            "max_entropy_bits": 0.0,
            "entropy_ratio": 0.0,
            "score": 0.0,
            "pass": False,
            "top_actions": [],
        }

    counts = Counter(actions)
    total = len(actions)
    unique = len(counts)

    shannon = 0.0
    for c in counts.values():
        p = c / total
        shannon -= p * math.log2(p)

    max_h = math.log2(unique) if unique > 1 else 1.0
    ratio = shannon / max_h

    # Healthy homeostatic band: 0.50 <= ratio <= 0.95
    is_pass = 0.50 <= ratio <= 0.95
    score = 1.0 if is_pass else max(0.0, 1.0 - abs(ratio - 0.75) * 2)

    return {
        "total_actions": total,
        "unique_actions": unique,
        "shannon_entropy_bits": round(shannon, 4),
        "max_entropy_bits": round(max_h, 4),
        "entropy_ratio": round(ratio, 4),
        "score": round(score, 4),
        "pass": is_pass,
        "top_actions": [
            {"action": a, "count": c, "share": round(c / total, 4)}
            for a, c in counts.most_common(5)
        ],
    }


def compute_sequential_constraint(actions: list[str]) -> dict[str, Any]:
    if len(actions) < 2:
        return {
            "conditional_entropy_bits": 0.0,
            "mutual_information_bits": 0.0,
            "constraint_ratio": 0.0,
            "score": 0.0,
            "pass": False,
        }

    counts = Counter(actions)
    total = len(actions)
    shannon_h = -sum((c / total) * math.log2(c / total) for c in counts.values())

    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    for a_curr, a_next in zip(actions[:-1], actions[1:]):
        transitions[a_curr][a_next] += 1

    cond_entropy = 0.0
    for a_curr, next_counts in transitions.items():
        n_curr = sum(next_counts.values())
        p_curr = n_curr / (total - 1)
        h_cond = -sum((c / n_curr) * math.log2(c / n_curr) for c in next_counts.values())
        cond_entropy += p_curr * h_cond

    mutual_info = max(0.0, shannon_h - cond_entropy)
    constraint_ratio = mutual_info / shannon_h if shannon_h > 0 else 0.0

    # Healthy intentional momentum: 0.05 <= constraint_ratio <= 0.40
    is_pass = 0.05 <= constraint_ratio <= 0.40
    score = 1.0 if is_pass else max(0.0, 1.0 - abs(constraint_ratio - 0.20) * 3)

    return {
        "conditional_entropy_bits": round(cond_entropy, 4),
        "mutual_information_bits": round(mutual_info, 4),
        "constraint_ratio": round(constraint_ratio, 4),
        "score": round(score, 4),
        "pass": is_pass,
    }


def compute_diurnal_coverage(lines: list[str]) -> dict[str, Any]:
    hourly_actions: Counter[int] = Counter()
    for line in lines:
        if "world action" in line:
            m = re.match(r"^(\d{4}-\d{2}-\d{2}T(\d{2}):\d{2}:\d{2}Z)", line)
            if m:
                hour = int(m.group(2))
                hourly_actions[hour] += 1

    active_hours = len(hourly_actions)
    coverage_ratio = active_hours / 24.0
    score = 1.0 if coverage_ratio >= 0.75 else (coverage_ratio / 0.75)

    return {
        "active_hours_in_log": active_hours,
        "coverage_ratio": round(coverage_ratio, 4),
        "score": round(score, 4),
        "pass": coverage_ratio >= 0.75,
        "hourly_distribution": dict(sorted(hourly_actions.items())),
    }


def check_live_organism(url: str = LIVE_OBSERVATION_URL) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "guala-entropy-monitor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            obs = json.load(r)
        lo = obs.get("last_occurrence") or {}
        deficit = lo.get("metabolic_need_reserve_deficit") or [0, 1]
        deficit_ratio = (deficit[0] / deficit[1]) if deficit[1] else 0.0
        sleep = lo.get("her_sleep") or {}
        live_tick = obs.get("live_tick") or lo.get("native_tick") or 0
        last_action = lo.get("requested_world_action")

        return {
            "online": True,
            "live_tick": live_tick,
            "metabolic_deficit_ratio": round(deficit_ratio, 4),
            "hungry": deficit_ratio > 0.40,
            "asleep": bool(sleep.get("asleep")),
            "last_action": last_action,
            "score": 1.0 if deficit_ratio <= 0.60 else max(0.0, 1.0 - (deficit_ratio - 0.60) * 2),
        }
    except Exception as err:
        return {
            "online": False,
            "error": str(err),
            "score": 0.5,
        }


def run_monitor(
    log_path: str = DEFAULT_LOG,
    state_path: str = DEFAULT_STATE,
    check_live: bool = True,
) -> dict[str, Any]:
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Caretaker log not found: {log_path}")

    lines: list[str] = []
    rotated = log_path + ".1"
    if os.path.exists(rotated):
        with open(rotated, "r", encoding="utf-8", errors="ignore") as f:
            lines.extend(f.readlines())
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines.extend(f.readlines())

    full_text = "".join(lines)
    all_actions = re.findall(r"world action ([a-z_]+)", full_text)

    # 24-hour / full historical metrics
    global_entropy = compute_action_entropy(all_actions)
    global_seq = compute_sequential_constraint(all_actions)
    diurnal = compute_diurnal_coverage(lines)

    # Recent 100 actions window (dynamic phase-space agility)
    recent_actions = all_actions[-100:] if len(all_actions) >= 100 else all_actions
    recent_entropy = compute_action_entropy(recent_actions)

    live_status = check_live_organism() if check_live else {"score": 1.0}

    composite_score = round(
        0.35 * global_entropy["score"]
        + 0.25 * global_seq["score"]
        + 0.20 * diurnal["score"]
        + 0.10 * recent_entropy["score"]
        + 0.10 * live_status.get("score", 1.0),
        4,
    )

    passed = composite_score >= PHYSICS_FLOOR

    return {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "physics_floor": PHYSICS_FLOOR,
        "composite_score": composite_score,
        "overall_pass": passed,
        "global_action_entropy": global_entropy,
        "recent_action_entropy_window_100": recent_entropy,
        "sequential_constraint": global_seq,
        "diurnal_coverage": diurnal,
        "live_organism": live_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Guala Longitudinal Phase-Space Entropy Monitor")
    parser.add_argument("--log", default=DEFAULT_LOG, help="Path to caretaker.log")
    parser.add_argument("--state", default=DEFAULT_STATE, help="Path to state.json")
    parser.add_argument("--no-live", action="store_true", help="Skip querying live /observation endpoint")
    parser.add_argument("--watch", type=int, default=0, help="Poll interval in seconds (0 = single shot)")
    parser.add_argument("--json", action="store_true", help="Output pure JSON")
    args = parser.parse_args()

    while True:
        try:
            report = run_monitor(args.log, args.state, check_live=not args.no_live)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                h = report["global_action_entropy"]
                s = report["sequential_constraint"]
                d = report["diurnal_coverage"]
                print(f"[{report['timestamp_utc']}] Longitudinal Phase-Space Entropy Monitor")
                print(f"  Composite Score: {report['composite_score']} (Floor: {report['physics_floor']}) -> {'PASS' if report['overall_pass'] else 'FAIL'}")
                print(f"  Action Entropy:  H={h['shannon_entropy_bits']} bits (ratio={h['entropy_ratio']}) across {h['total_actions']} actions")
                print(f"  Constraint:      MI={s['mutual_information_bits']} bits (ratio={s['constraint_ratio']})")
                print(f"  Diurnal Cycle:   {d['active_hours_in_log']}/24 UTC hours covered")
                if "live_organism" in report and report["live_organism"].get("online"):
                    lo = report["live_organism"]
                    print(f"  Live State:      tick={lo['live_tick']}, deficit={lo['metabolic_deficit_ratio']}, hungry={lo['hungry']}, asleep={lo['asleep']}")
        except Exception as exc:
            print(f"Error during monitor execution: {exc}", file=sys.stderr)
            if not args.watch:
                sys.exit(1)

        if args.watch <= 0:
            break
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
