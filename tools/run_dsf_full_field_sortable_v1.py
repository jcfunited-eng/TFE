#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
SNAPSHOT_CSV = BACKUPS / "canonical_real_snapshot_production_fixed_snapshot_latest_20260321T013943Z.csv"
NOTE_PATH = REPO_ROOT / "DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V1.md"
PRESSURE_SCRIPT = REPO_ROOT / "web" / "scripts" / "run_uf_dynamic_decision_pressure_test.mjs"
SLACK_SCRIPT = REPO_ROOT / "tools" / "codex_notify_slack.sh"
TIE_EPS = 1e-12
BASELINE_COUNTS = {"Accumulate": 133, "Hold": 1132, "Avoid": 4148}
REQUIRED_FIELDS = [
    "symbol",
    "decision_timestamp",
    "bar_count",
    "S_UF",
    "R_UF",
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
]
ANCHORS = [
    ("AGO", "Accumulate"),
    ("TXRH", "Accumulate"),
    ("DHI", "Accumulate"),
    ("AAT", "Hold"),
    ("ACGL", "Hold"),
    ("ADC", "Hold"),
    ("AA", "Avoid"),
    ("AAPL", "Avoid"),
    ("ACLS", "Avoid"),
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = (len(ordered) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    frac = idx - lo
    return float(ordered[lo] * (1.0 - frac) + ordered[hi] * frac)


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def ranges(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for field in ["D_k", "M_k", "R_rev_k", "B_k"]:
        vals = [float(row[field]) for row in rows]
        out[field] = {"min": float(min(vals)), "max": float(max(vals))}
    return out


def load_rows() -> list[dict[str, Any]]:
    if not SNAPSHOT_CSV.exists():
        raise SystemExit(f"missing snapshot csv: {SNAPSHOT_CSV}")
    with SNAPSHOT_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in REQUIRED_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"missing required fields: {missing}")
        rows = list(reader)
    return rows


def classify_geometry_bucket(row: dict[str, Any]) -> str:
    rupture = float(row["rupture"])
    covered_edge = float(row["covered_edge"])
    covered_core = float(row["covered_core"])
    break_agreement = float(row["break_agreement"])
    forward_agreement = float(row["forward_agreement"])
    load = float(row["load"])

    if rupture > TIE_EPS:
        return "rupture"

    if covered_edge > TIE_EPS:
        hold_edge = covered_edge * (1.0 - break_agreement)
        break_edge = covered_edge * break_agreement
        if break_edge > hold_edge + TIE_EPS:
            return "one_sided_break"
        return "one_sided_hold"

    if covered_core > TIE_EPS:
        covered_forward = forward_agreement * (1.0 - break_agreement) * (1.0 - load)
        covered_burdened = (1.0 - forward_agreement) * (1.0 - break_agreement) + forward_agreement * load
        covered_break = break_agreement
        best = max(covered_forward, covered_burdened, covered_break)
        near = {
            "covered_forward": best - covered_forward <= TIE_EPS,
            "covered_burdened": best - covered_burdened <= TIE_EPS,
            "covered_break": best - covered_break <= TIE_EPS,
        }
        if sum(1 for v in near.values() if v) >= 2:
            return "covered_burdened"
        if near["covered_forward"]:
            return "covered_forward"
        if near["covered_break"]:
            return "covered_break"
        return "covered_burdened"

    return "rupture"


def decide(accumulate: float, hold: float, avoid: float) -> str:
    basins = {
        "Accumulate": accumulate,
        "Hold": hold,
        "Avoid": avoid,
    }
    best = max(basins.values())
    near_winners = [name for name, value in basins.items() if best - value <= TIE_EPS]
    if len(near_winners) >= 2:
        return "Hold"
    return near_winners[0]


def smoke_anchor_results(row_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for symbol, expected in ANCHORS:
        row = row_map.get(symbol)
        if row is None:
            results.append({"symbol": symbol, "expected": expected, "status": "missing"})
            continue
        actual = row["final_decision"]
        results.append(
            {
                "symbol": symbol,
                "expected": expected,
                "actual": actual,
                "match": actual == expected,
                "status": "ok",
            }
        )
    return results


def verdict_for_counts(decision_counts: dict[str, int]) -> str:
    if decision_counts == BASELINE_COUNTS:
        return "sortable candidate is coherent and baseline-like"
    return "sortable candidate is coherent but diverges from baseline"


def main() -> int:
    rows = load_rows()
    raw_ranges = ranges(rows)

    if raw_ranges["D_k"]["min"] < -1.0 or raw_ranges["D_k"]["max"] > 1.0:
        raise SystemExit(f"D_k range blocker: {raw_ranges['D_k']}")
    if raw_ranges["R_rev_k"]["min"] < 0.0 or raw_ranges["R_rev_k"]["max"] > 1.0:
        raise SystemExit(f"R_rev_k range blocker: {raw_ranges['R_rev_k']}")
    if raw_ranges["B_k"]["min"] < -1.0 or raw_ranges["B_k"]["max"] > 1.0:
        raise SystemExit(f"B_k range blocker: {raw_ranges['B_k']}")

    row_audit: list[dict[str, Any]] = []
    decision_counts: Counter[str] = Counter()
    geometry_counts: Counter[str] = Counter()
    reversal_avoid_counts: Counter[str] = Counter()
    edge_decision_counts: Counter[str] = Counter()
    alt_decision_counts: Counter[str] = Counter()
    carry_break_winner_change = 0
    rev_blocked_accumulate = 0
    rev_drove_avoid = 0

    accumulate_forward: list[float] = []
    accumulate_load: list[float] = []
    accumulate_break: list[float] = []
    accumulate_core: list[float] = []
    accumulate_carry: list[float] = []
    avoid_bucket_counts: Counter[str] = Counter()
    hold_bucket_counts: Counter[str] = Counter()

    for raw in rows:
        symbol = str(raw["symbol"])
        decision_timestamp = str(raw["decision_timestamp"])
        bar_count = int(raw["bar_count"])
        s_uf = float(raw["S_UF"])
        r_uf = float(raw["R_UF"])
        d_k = float(raw["D_k"])
        m_k = float(raw["M_k"])
        r_rev_k = float(raw["R_rev_k"])
        u_star_k = float(raw["U_star_k"])
        c_k = float(raw["C_k"])
        p_k = float(raw["P_k"])
        b_k = float(raw["B_k"])

        m_hat = clip(m_k, -1.0, 1.0)
        s = s_uf - u_star_k
        r = r_uf - u_star_k
        covered_core = max(min(s, r), 0.0)
        covered_edge = max(max(s, r), 0.0) - covered_core
        rupture = max(-max(s, r), 0.0)
        d_pos = max(d_k, 0.0)
        d_neg = max(-d_k, 0.0)
        m_cont = (1.0 + m_hat) / 2.0
        m_bend = (1.0 - m_hat) / 2.0
        rev = r_rev_k
        load = (c_k + p_k) / (1.0 + c_k + p_k)
        carry_mag = -b_k
        forward_agreement = min(d_pos, m_cont)
        break_seed = max(rev, min(d_neg, m_bend))
        carry_break = carry_mag * max(rev, d_neg, m_bend)
        break_agreement = max(break_seed, carry_break)

        accumulate_basin = covered_core * forward_agreement * (1.0 - break_agreement) * (1.0 - load)
        hold_basin = covered_edge * (1.0 - break_agreement) + covered_core * (
            (1.0 - forward_agreement) * (1.0 - break_agreement) + forward_agreement * load
        )
        avoid_basin = rupture + (covered_core + covered_edge) * break_agreement

        final_decision = decide(accumulate_basin, hold_basin, avoid_basin)

        alt_accumulate = covered_core * forward_agreement * (1.0 - break_seed) * (1.0 - load)
        alt_hold = covered_edge * (1.0 - break_seed) + covered_core * (
            (1.0 - forward_agreement) * (1.0 - break_seed) + forward_agreement * load
        )
        alt_avoid = rupture + (covered_core + covered_edge) * break_seed
        alt_decision = decide(alt_accumulate, alt_hold, alt_avoid)

        geometry_bucket = classify_geometry_bucket(
            {
                "covered_core": covered_core,
                "covered_edge": covered_edge,
                "rupture": rupture,
                "break_agreement": break_agreement,
                "forward_agreement": forward_agreement,
                "load": load,
            }
        )

        rev_material_avoid = final_decision == "Avoid" and rev > TIE_EPS and rev >= break_seed - TIE_EPS
        reversal_avoid_counts["reversal_material_to_avoid" if rev_material_avoid else "reversal_not_material_to_avoid"] += 1

        if covered_edge > TIE_EPS:
            edge_decision_counts[final_decision] += 1

        if alt_decision != final_decision:
            carry_break_winner_change += 1
        alt_decision_counts[alt_decision] += 1

        if covered_core > TIE_EPS and forward_agreement > TIE_EPS and rev > TIE_EPS and final_decision != "Accumulate":
            rev_blocked_accumulate += 1
        if rev_material_avoid:
            rev_drove_avoid += 1

        decision_counts[final_decision] += 1
        geometry_counts[geometry_bucket] += 1

        if final_decision == "Accumulate":
            accumulate_forward.append(forward_agreement)
            accumulate_load.append(load)
            accumulate_break.append(break_agreement)
            accumulate_core.append(covered_core)
            accumulate_carry.append(carry_break)
        elif final_decision == "Avoid":
            avoid_bucket_counts[geometry_bucket] += 1
        elif final_decision == "Hold":
            hold_bucket_counts[geometry_bucket] += 1

        row_audit.append(
            {
                "symbol": symbol,
                "decision_timestamp": decision_timestamp,
                "bar_count": bar_count,
                "final_decision": final_decision,
                "s": s,
                "r": r,
                "covered_core": covered_core,
                "covered_edge": covered_edge,
                "rupture": rupture,
                "D_k": d_k,
                "M_k": m_k,
                "M_hat": m_hat,
                "R_rev_k": r_rev_k,
                "U_star_k": u_star_k,
                "C_k": c_k,
                "P_k": p_k,
                "B_k": b_k,
                "D_pos": d_pos,
                "D_neg": d_neg,
                "M_cont": m_cont,
                "M_bend": m_bend,
                "load": load,
                "carry_mag": carry_mag,
                "forward_agreement": forward_agreement,
                "break_seed": break_seed,
                "carry_break": carry_break,
                "break_agreement": break_agreement,
                "Accumulate_basin": accumulate_basin,
                "Hold_basin": hold_basin,
                "Avoid_basin": avoid_basin,
                "geometry_bucket": geometry_bucket,
                "reversal_material_to_avoid": rev_material_avoid,
                "carry_break_changed_winner": alt_decision != final_decision,
                "break_seed_only_decision": alt_decision,
            }
        )

    stamp = utc_stamp()
    row_csv = BACKUPS / f"dsf_full_field_sortable_v1_rows_{stamp}.csv"
    row_json = BACKUPS / f"dsf_full_field_sortable_v1_rows_{stamp}.json"
    summary_json = BACKUPS / f"dsf_full_field_sortable_v1_summary_{stamp}.json"

    with row_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "symbol",
            "decision_timestamp",
            "bar_count",
            "final_decision",
            "s",
            "r",
            "covered_core",
            "covered_edge",
            "rupture",
            "D_k",
            "M_k",
            "M_hat",
            "R_rev_k",
            "U_star_k",
            "C_k",
            "P_k",
            "B_k",
            "D_pos",
            "D_neg",
            "M_cont",
            "M_bend",
            "load",
            "carry_mag",
            "forward_agreement",
            "break_seed",
            "carry_break",
            "break_agreement",
            "Accumulate_basin",
            "Hold_basin",
            "Avoid_basin",
            "geometry_bucket",
            "reversal_material_to_avoid",
            "carry_break_changed_winner",
            "break_seed_only_decision",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(row_audit)

    with row_json.open("w", encoding="utf-8") as handle:
        json.dump(row_audit, handle, indent=2)

    row_map = {row["symbol"]: row for row in row_audit if row["symbol"] not in {"AGO", "TXRH", "DHI", "AAT", "ACGL", "ADC", "AA", "AAPL", "ACLS"}}
    for row in row_audit:
        if row["symbol"] in {item[0] for item in ANCHORS}:
            row_map[row["symbol"]] = row

    accumulate_pattern = {
        "count": decision_counts["Accumulate"],
        "median_forward_agreement": quantile(accumulate_forward, 0.5),
        "median_load": quantile(accumulate_load, 0.5),
        "median_break_agreement": quantile(accumulate_break, 0.5),
        "median_covered_core": quantile(accumulate_core, 0.5),
        "median_carry_break": quantile(accumulate_carry, 0.5),
    }

    if rev_drove_avoid > rev_blocked_accumulate:
        reversal_summary = "reversal mainly drove Avoid"
    elif rev_blocked_accumulate > rev_drove_avoid:
        reversal_summary = "reversal mainly blocked Accumulate"
    else:
        reversal_summary = "reversal affected blocking and Avoid equally"

    edge_hold = edge_decision_counts["Hold"]
    edge_avoid = edge_decision_counts["Avoid"]
    if edge_hold > edge_avoid:
        covered_edge_summary = "covered_edge mostly stayed Hold"
    elif edge_avoid > edge_hold:
        covered_edge_summary = "covered_edge mostly decayed to Avoid"
    else:
        covered_edge_summary = "covered_edge split evenly between Hold and Avoid"

    if carry_break_winner_change == 0:
        b_k_summary = "B_k affected sorting only through carry_break and did not change any winner versus break_seed alone"
    else:
        b_k_summary = (
            f"B_k affected sorting only through carry_break and changed the winner on {carry_break_winner_change} rows "
            f"out of {len(row_audit)}"
        )

    summary = {
        "generated_at_utc": utc_iso(),
        "note_path": str(NOTE_PATH),
        "snapshot_csv": str(SNAPSHOT_CSV),
        "tie_eps": TIE_EPS,
        "raw_ranges": raw_ranges,
        "baseline_reference_counts": BASELINE_COUNTS,
        "decision_counts": dict(decision_counts),
        "geometry_bucket_counts": dict(geometry_counts),
        "reversal_material_to_avoid_counts": dict(reversal_avoid_counts),
        "covered_edge_decision_counts": dict(edge_decision_counts),
        "carry_break_changed_winner_count": carry_break_winner_change,
        "break_seed_only_decision_counts": dict(alt_decision_counts),
        "top_geometry_buckets_for_avoid": avoid_bucket_counts.most_common(),
        "top_geometry_buckets_for_hold": hold_bucket_counts.most_common(),
        "accumulate_common_pattern": accumulate_pattern,
        "reversal_blocked_accumulate_count": rev_blocked_accumulate,
        "reversal_drove_avoid_count": rev_drove_avoid,
        "reversal_summary": reversal_summary,
        "covered_edge_summary": covered_edge_summary,
        "b_k_sorting_summary": b_k_summary,
        "anchor_smoke_tests": smoke_anchor_results(row_map) if PRESSURE_SCRIPT.exists() else [],
        "verdict": verdict_for_counts(dict(decision_counts)),
        "row_level_audit_csv": str(row_csv),
        "row_level_audit_json": str(row_json),
    }

    with summary_json.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    payload = {
        "text": (
            "Codex completed DSF sortable full-field v1 audit. "
            f"Decision counts={dict(decision_counts)} "
            f"verdict={summary['verdict']} "
            f"summary={summary_json.name}"
        )
    }
    if SLACK_SCRIPT.exists():
        import subprocess

        subprocess.run(
            ["bash", "-lc", f"printf '%s\\n' {json.dumps(json.dumps(payload))} | {SLACK_SCRIPT}"],
            cwd=str(REPO_ROOT),
            check=True,
        )

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
