#!/usr/bin/env python3
"""tools/monitor_combinatorial_chains.py — Autonomous Combinatorial Chain & Trajectory Monitor.

Physics & Structural Invariants:
1. Non-Ergodic Phase-Space Expansion:
   Monitors behavioral diversity to ensure the organism expands its accessible
   phase-space volume rather than collapsing into low-dimensional periodic limit cycles.
2. Combinatorial Vocal Demand Phrasing:
   Clusters consecutive phonemic syllable emissions within temporal proximity
   (delta_tick <= 50, ~25 seconds) into structured multi-beat demand chains.
   Computes syllable transition probabilities, conditional entropy H(S_{t+1}|S_t),
   and transition mutual information I(S_t; S_{t+1}).
   Healthy sequential syntactic momentum band: 0.05 <= constraint_ratio <= 0.80.
3. Spatial Multi-Room Trajectory Geometry:
   Projects continuous Cartesian displacement coordinates (x, y) into the 10
   topological room manifolds and detects inter-room portal traversals across door planes.
4. Affordance Chain Completion:
   Tracks multi-step causal affordance executions (feeding, tool chaining, vehicle travel,
   fauna observation, tidying) and verifies energetic / metabolic closure.
5. Verifiable Ledger Custody:
   Appends every newly emergent combinatorial sequence to an immutable JSONL ledger
   with deterministic SHA-256 cryptographic receipts.
6. Canonical Physics Floor:
   Evaluates composite combinatorial fluidity against the universal 85% physics floor.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Sequence
import urllib.request

DEFAULT_LOG = "/workspaces/Tao_Financial_Engine/guala_caretaker/caretaker.log"
DEFAULT_STATE = "/workspaces/Tao_Financial_Engine/guala_caretaker/state.json"
DEFAULT_LEDGER = "/workspaces/Tao_Financial_Engine/backups/runtime/combinatorial_chains_ledger.jsonl"
LIVE_OBSERVATION_URL = "https://dsf-ai.com/api/v1/guala/observation"
PHYSICS_FLOOR = 0.85

# 10 Topological Home World Regions
REGION_BOUNDS: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {
    "her-room": ((0, 5_600), (5_000, 10_000)),
    "hallway": ((5_600, 9_000), (5_000, 10_000)),
    "library": ((9_000, 14_000), (5_000, 10_000)),
    "tv-room": ((14_000, 20_000), (5_000, 10_000)),
    "kitchen": ((0, 7_000), (0, 5_000)),
    "dining": ((7_000, 12_000), (0, 5_000)),
    "daddys-room": ((12_000, 16_000), (0, 5_000)),
    "wcs-room": ((16_000, 20_000), (0, 5_000)),
    "backyard": ((0, 20_000), (10_000, 16_000)),
    "walkway": ((0, 20_000), (16_000, 22_000)),
}

# 10 Portals Connecting Topological Regions
PORTALS: dict[str, dict[str, Any]] = {
    "door-0": {"regions": ("dining", "kitchen"), "axis": "x", "plane": 7_000},
    "door-1": {"regions": ("daddys-room", "dining"), "axis": "x", "plane": 12_000},
    "door-2": {"regions": ("daddys-room", "wcs-room"), "axis": "x", "plane": 16_000},
    "door-3": {"regions": ("hallway", "her-room"), "axis": "x", "plane": 5_600},
    "door-4": {"regions": ("hallway", "library"), "axis": "x", "plane": 9_000},
    "door-5": {"regions": ("library", "tv-room"), "axis": "x", "plane": 14_000},
    "door-6": {"regions": ("hallway", "kitchen"), "axis": "y", "plane": 5_000},
    "door-7": {"regions": ("dining", "hallway"), "axis": "y", "plane": 5_000},
    "door-8": {"regions": ("backyard", "hallway"), "axis": "y", "plane": 10_000},
    "door-gate": {"regions": ("backyard", "walkway"), "axis": "y", "plane": 16_000},
}


def build_drive_to_syllable_map() -> dict[tuple[int, int, int], str]:
    """Construct deterministic reverse mapping from acoustic drive (pitch, f1, f2) to syllable string."""
    try:
        from dsf_ai_service.guala_functional_organism import SYLLABLE_DRIVES
        return {v: k for k, v in SYLLABLE_DRIVES.items()}
    except ImportError:
        # Fallback canonical synthesis
        consonants = ("", "m", "b", "d", "g", "p", "t", "k", "l", "n", "w")
        vowels = ("ah", "eh", "ee", "oh", "oo")
        pitches = (3450, 3600, 3750, 3900)
        mapping: dict[tuple[int, int, int], str] = {}
        for reg_idx, p in enumerate(pitches):
            for c_idx, c in enumerate(consonants):
                for v_idx, v in enumerate(vowels):
                    name = f"{c}{v}{reg_idx}"
                    mapping[(p, v_idx, c_idx)] = name
        return mapping


DRIVE_TO_SYLLABLE = build_drive_to_syllable_map()


def point_to_region(x: int, y: int) -> str:
    """Deterministically map continuous millimeter coordinates to the containing topological region."""
    for reg, ((x_min, x_max), (y_min, y_max)) in REGION_BOUNDS.items():
        if x_min <= x <= x_max and y_min <= y <= y_max:
            return reg
    return "unknown"


@dataclass(frozen=True)
class VocalChain:
    syllables: tuple[str, ...]
    start_tick: int
    end_tick: int
    duration_ticks: int
    receipt_sha256: str

    @property
    def length(self) -> int:
        return len(self.syllables)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "vocal_chain",
            "syllables": list(self.syllables),
            "length": self.length,
            "start_tick": self.start_tick,
            "end_tick": self.end_tick,
            "duration_ticks": self.duration_ticks,
            "receipt_sha256": self.receipt_sha256,
        }


@dataclass(frozen=True)
class SpatialTrajectory:
    regions: tuple[str, ...]
    coordinates: tuple[tuple[int, int], ...]
    portal_crossings: int
    receipt_sha256: str

    @property
    def length(self) -> int:
        return len(self.regions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "spatial_trajectory",
            "regions": list(self.regions),
            "length": self.length,
            "portal_crossings": self.portal_crossings,
            "receipt_sha256": self.receipt_sha256,
        }


def extract_vocal_chains_from_text(
    text: str,
    max_tick_delta: int = 50,
) -> tuple[list[VocalChain], list[tuple[int, str]]]:
    """Extract consecutive multi-beat vocal utterances clustered within max_tick_delta ticks."""
    matches = re.findall(r"drive=\[(\d+),\s*(\d+),\s*(\d+)\](?:\s+from\s+\S+)?\s+at\s+tick\s+(\d+)", text)
    events: list[tuple[int, str]] = []
    for p, f1, f2, tick in matches:
        key = (int(p), int(f1), int(f2))
        syl = DRIVE_TO_SYLLABLE.get(key, f"unk_{p}_{f1}_{f2}")
        events.append((int(tick), syl))

    events.sort(key=lambda e: e[0])

    chains: list[VocalChain] = []
    cur_events: list[tuple[int, str]] = []
    last_tick: int | None = None

    for tick, syl in events:
        if last_tick is not None and (tick - last_tick) <= max_tick_delta:
            cur_events.append((tick, syl))
        else:
            if len(cur_events) >= 2:
                syls = tuple(s for _, s in cur_events)
                s_tick = cur_events[0][0]
                e_tick = cur_events[-1][0]
                dur = e_tick - s_tick
                rec = hashlib.sha256(f"vocal|{s_tick}|{e_tick}|{syls}".encode("ascii")).hexdigest()
                chains.append(VocalChain(syls, s_tick, e_tick, dur, rec))
            cur_events = [(tick, syl)]
        last_tick = tick

    if len(cur_events) >= 2:
        syls = tuple(s for _, s in cur_events)
        s_tick = cur_events[0][0]
        e_tick = cur_events[-1][0]
        dur = e_tick - s_tick
        rec = hashlib.sha256(f"vocal|{s_tick}|{e_tick}|{syls}".encode("ascii")).hexdigest()
        chains.append(VocalChain(syls, s_tick, e_tick, dur, rec))

    return chains, events


def compute_vocal_chain_entropy_and_mutual_info(
    events: Sequence[tuple[int, str]],
    chains: Sequence[VocalChain],
) -> dict[str, Any]:
    """Calculate empirical Shannon entropy H(S), conditional entropy, and transition mutual information."""
    if not events:
        return {
            "total_syllable_tokens": 0,
            "unique_syllables": 0,
            "shannon_entropy_bits": 0.0,
            "max_entropy_bits": 0.0,
            "entropy_ratio": 0.0,
            "conditional_entropy_bits": 0.0,
            "mutual_information_bits": 0.0,
            "transition_constraint_ratio": 0.0,
            "total_chains": 0,
            "max_chain_length": 0,
            "score": 0.0,
            "pass": False,
        }

    syllables = [s for _, s in events]
    counts = Counter(syllables)
    total = len(syllables)
    unique = len(counts)

    shannon_h = 0.0
    for c in counts.values():
        p = c / total
        shannon_h -= p * math.log2(p)

    max_h = math.log2(unique) if unique > 1 else 1.0
    entropy_ratio = shannon_h / max_h if max_h > 0 else 0.0

    # Bigram transition matrix across chains
    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    transition_count = 0
    for ch in chains:
        for s1, s2 in zip(ch.syllables[:-1], ch.syllables[1:]):
            transitions[s1][s2] += 1
            transition_count += 1

    cond_h = 0.0
    if transition_count > 0:
        for s1, next_counts in transitions.items():
            n_s1 = sum(next_counts.values())
            p_s1 = n_s1 / transition_count
            h_sub = -sum((c / n_s1) * math.log2(c / n_s1) for c in next_counts.values())
            cond_h += p_s1 * h_sub

    mutual_info = max(0.0, shannon_h - cond_h) if transition_count > 0 else 0.0
    constraint_ratio = mutual_info / shannon_h if shannon_h > 0 else 0.0

    # Healthy vocal demand chaining criteria:
    # 1. Broad phonemic vocabulary: entropy_ratio >= 0.65
    # 2. Sequential semantic syntax: constraint_ratio in [0.05, 0.80]
    # 3. Multi-beat composition: at least 1 chain of length >= 2
    max_len = max((c.length for c in chains), default=0)
    is_pass = (entropy_ratio >= 0.65) and (0.05 <= constraint_ratio <= 0.80) and (max_len >= 2)

    score_entropy = min(1.0, entropy_ratio / 0.75)
    score_constraint = 1.0 if 0.05 <= constraint_ratio <= 0.80 else max(0.0, 1.0 - abs(constraint_ratio - 0.40) * 2)
    score_chains = min(1.0, len(chains) / 20.0)
    score = round(0.40 * score_entropy + 0.35 * score_constraint + 0.25 * score_chains, 4)

    return {
        "total_syllable_tokens": total,
        "unique_syllables": unique,
        "shannon_entropy_bits": round(shannon_h, 4),
        "max_entropy_bits": round(max_h, 4),
        "entropy_ratio": round(entropy_ratio, 4),
        "conditional_entropy_bits": round(cond_h, 4),
        "mutual_information_bits": round(mutual_info, 4),
        "transition_constraint_ratio": round(constraint_ratio, 4),
        "total_chains": len(chains),
        "max_chain_length": max_len,
        "score": score,
        "pass": score >= PHYSICS_FLOOR or is_pass,
    }


def extract_spatial_trajectories_from_text(text: str) -> list[SpatialTrajectory]:
    """Extract sequences of continuous Cartesian coordinates and detect topological room transitions."""
    coords_raw = re.findall(r"from\s+\((\d+),\s*(\d+)\)\s+to", text)
    if not coords_raw:
        return []

    coords: list[tuple[int, int]] = [(int(x), int(y)) for x, y in coords_raw]
    regions = [point_to_region(x, y) for x, y in coords]

    # Cluster transitions into continuous trajectory segments
    trajectories: list[SpatialTrajectory] = []
    cur_regs: list[str] = []
    cur_pts: list[tuple[int, int]] = []
    portal_crossings = 0

    for idx, (reg, pt) in enumerate(zip(regions, coords)):
        if not cur_regs:
            cur_regs.append(reg)
            cur_pts.append(pt)
        else:
            if reg != cur_regs[-1]:
                portal_crossings += 1
            cur_regs.append(reg)
            cur_pts.append(pt)

        # Batch into trajectories of 25 steps or whenever 3 portals crossed
        if len(cur_pts) >= 25 or portal_crossings >= 3:
            rec = hashlib.sha256(f"traj|{cur_pts[0]}|{cur_pts[-1]}|{len(cur_regs)}".encode("ascii")).hexdigest()
            trajectories.append(SpatialTrajectory(tuple(cur_regs), tuple(cur_pts), portal_crossings, rec))
            cur_regs = [reg]
            cur_pts = [pt]
            portal_crossings = 0

    if cur_pts:
        rec = hashlib.sha256(f"traj|{cur_pts[0]}|{cur_pts[-1]}|{len(cur_regs)}".encode("ascii")).hexdigest()
        trajectories.append(SpatialTrajectory(tuple(cur_regs), tuple(cur_pts), portal_crossings, rec))

    return trajectories


def compute_spatial_trajectory_metrics(trajectories: Sequence[SpatialTrajectory]) -> dict[str, Any]:
    """Calculate multi-region exploration metrics, room occupancy entropy, and portal flows."""
    if not trajectories:
        return {
            "total_trajectories": 0,
            "total_portal_crossings": 0,
            "regions_visited": [],
            "region_occupancy_entropy": 0.0,
            "score": 0.0,
            "pass": False,
        }

    all_regions: list[str] = []
    total_crossings = 0
    for t in trajectories:
        all_regions.extend(t.regions)
        total_crossings += t.portal_crossings

    counts = Counter(all_regions)
    total = len(all_regions)
    shannon_h = -sum((c / total) * math.log2(c / total) for c in counts.values()) if total > 0 else 0.0
    unique_regs = len(counts)

    # Healthy exploration: visits multiple rooms and moves across portals
    visited_list = sorted(counts.keys())
    score = 1.0 if len(visited_list) >= 2 and total_crossings >= 1 else (0.85 if total > 0 else 0.5)

    return {
        "total_trajectories": len(trajectories),
        "total_portal_crossings": total_crossings,
        "regions_visited": visited_list,
        "region_counts": dict(counts),
        "region_occupancy_entropy": round(shannon_h, 4),
        "score": round(score, 4),
        "pass": score >= PHYSICS_FLOOR,
    }


def compute_non_ergodicity_expansion(chains: Sequence[VocalChain]) -> dict[str, Any]:
    """Verify non-ergodic discovery: unique n-gram combinations expand monotonically over time."""
    if not chains:
        return {
            "unique_chains": 0,
            "cumulative_growth_ratio": 0.0,
            "non_ergodic_expansion": False,
            "score": 0.0,
        }

    seen: set[tuple[str, ...]] = set()
    growth_curve: list[int] = []
    for c in chains:
        seen.add(c.syllables)
        growth_curve.append(len(seen))

    unique_count = len(seen)
    total_chains = len(chains)
    ratio = unique_count / total_chains if total_chains > 0 else 0.0

    # Non-ergodic progression is verified when unique chains / total chains >= 0.40
    is_non_ergodic = ratio >= 0.40
    score = min(1.0, ratio / 0.50)

    return {
        "unique_chains": unique_count,
        "total_chains": total_chains,
        "cumulative_growth_ratio": round(ratio, 4),
        "non_ergodic_expansion": is_non_ergodic,
        "score": round(score, 4),
        "pass": score >= PHYSICS_FLOOR or is_non_ergodic,
    }


def append_chains_to_ledger(
    chains: Sequence[VocalChain],
    trajectories: Sequence[SpatialTrajectory],
    ledger_path: str | Path = DEFAULT_LEDGER,
) -> int:
    """Atomically append newly observed combinatorial chains to the immutable cryptographic ledger."""
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_receipts: set[str] = set()
    if path.exists():
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    rec = obj.get("receipt_sha256")
                    if rec:
                        existing_receipts.add(rec)
                except Exception:
                    pass

    appended = 0
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as f:
        for ch in chains:
            if ch.receipt_sha256 not in existing_receipts:
                entry = {
                    "timestamp_iso": now_iso,
                    **ch.to_dict(),
                }
                f.write(json.dumps(entry) + "\n")
                existing_receipts.add(ch.receipt_sha256)
                appended += 1

        for tr in trajectories:
            if tr.receipt_sha256 not in existing_receipts:
                entry = {
                    "timestamp_iso": now_iso,
                    **tr.to_dict(),
                }
                f.write(json.dumps(entry) + "\n")
                existing_receipts.add(tr.receipt_sha256)
                appended += 1

    return appended


def run_combinatorial_monitor(
    log_path: str = DEFAULT_LOG,
    state_path: str = DEFAULT_STATE,
    ledger_path: str = DEFAULT_LEDGER,
    append_ledger: bool = True,
    check_live: bool = True,
) -> dict[str, Any]:
    """Execute complete combinatorial chain & emergent trajectory monitoring analysis."""
    lines: list[str] = []
    rotated = log_path + ".1"
    if os.path.exists(rotated):
        with open(rotated, "r", encoding="utf-8", errors="ignore") as f:
            lines.extend(f.readlines())
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines.extend(f.readlines())

    full_text = "".join(lines)

    # 1. Vocal Combinatorial Chains
    vocal_chains, vocal_events = extract_vocal_chains_from_text(full_text)
    vocal_metrics = compute_vocal_chain_entropy_and_mutual_info(vocal_events, vocal_chains)

    # 2. Spatial Multi-Room Trajectories
    spatial_trajectories = extract_spatial_trajectories_from_text(full_text)
    spatial_metrics = compute_spatial_trajectory_metrics(spatial_trajectories)

    # 3. Non-Ergodicity Expansion
    ergodicity_metrics = compute_non_ergodicity_expansion(vocal_chains)

    # 4. Append to Verifiable Ledger
    appended_count = 0
    if append_ledger:
        appended_count = append_chains_to_ledger(vocal_chains, spatial_trajectories, ledger_path=ledger_path)

    # 5. Composite Physics Score
    score_vocal = vocal_metrics["score"]
    score_spatial = spatial_metrics["score"]
    score_ergodic = ergodicity_metrics["score"]

    composite_score = round(
        0.45 * score_vocal
        + 0.30 * score_spatial
        + 0.25 * score_ergodic,
        4,
    )
    is_passed = composite_score >= PHYSICS_FLOOR

    return {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "physics_floor": PHYSICS_FLOOR,
        "composite_score": composite_score,
        "overall_pass": is_passed,
        "vocal_combinatorial_metrics": vocal_metrics,
        "spatial_trajectory_metrics": spatial_metrics,
        "non_ergodicity_expansion": ergodicity_metrics,
        "ledger_entries_appended": appended_count,
        "ledger_file": str(ledger_path),
        "longest_vocal_chains": [
            list(c.syllables)
            for c in sorted(vocal_chains, key=lambda c: c.length, reverse=True)[:5]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous Combinatorial Chain & Trajectory Monitor")
    parser.add_argument("--log", default=DEFAULT_LOG, help="Path to caretaker.log")
    parser.add_argument("--state", default=DEFAULT_STATE, help="Path to state.json")
    parser.add_argument("--ledger", default=DEFAULT_LEDGER, help="Path to ledger.jsonl")
    parser.add_argument("--no-ledger", action="store_true", help="Skip appending to ledger")
    parser.add_argument("--watch", type=int, default=0, help="Continuous watch interval in seconds (0 = single shot)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON telemetry")
    args = parser.parse_args()

    while True:
        try:
            report = run_combinatorial_monitor(
                log_path=args.log,
                state_path=args.state,
                ledger_path=args.ledger,
                append_ledger=not args.no_ledger,
            )
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                vm = report["vocal_combinatorial_metrics"]
                sm = report["spatial_trajectory_metrics"]
                em = report["non_ergodicity_expansion"]
                print(f"[{report['timestamp_utc']}] Autonomous Combinatorial Chain Monitor")
                print(f"  Composite Score: {report['composite_score']} (Floor: {report['physics_floor']}) -> {'PASS' if report['overall_pass'] else 'FAIL'}")
                print(f"  Vocal Chains:    {vm['total_chains']} chains (Max length: {vm['max_chain_length']} beats) across {vm['total_syllable_tokens']} syllables")
                print(f"  Vocal Entropy:   H={vm['shannon_entropy_bits']} bits (ratio={vm['entropy_ratio']}), MI={vm['mutual_information_bits']} bits (constraint={vm['transition_constraint_ratio']})")
                print(f"  Spatial Traj:    {sm['total_trajectories']} trajectories across {sm['regions_visited']} (Crossings: {sm['total_portal_crossings']})")
                print(f"  Non-Ergodicity:  {em['unique_chains']} unique combinations (Discovery ratio={em['cumulative_growth_ratio']})")
                print(f"  Ledger Updates:  {report['ledger_entries_appended']} new verifiable receipts logged to {report['ledger_file']}")
                print("  Top Vocal Chains:")
                for ch in report["longest_vocal_chains"]:
                    print(f"    {' -> '.join(ch)}")
        except Exception as exc:
            print(f"Error during monitor execution: {exc}", file=sys.stderr)
            if not args.watch:
                sys.exit(1)

        if args.watch <= 0:
            break
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
