#!/usr/bin/env python3
from __future__ import annotations

import csv
import glob
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
WEB_ROOT = REPO_ROOT / "web"
RUNTIME_SOURCE = WEB_ROOT / "src" / "lib" / "uf-dynamic-decision.ts"

ROW_COLUMNS = [
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

DECISION_ORDER = {"Avoid": 0, "Hold": 1, "Accumulate": 2}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def write_markdown(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def git_head() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def git_dirty() -> bool | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None
    return bool(result.stdout.strip())


def latest_artifacts() -> tuple[Path, Path]:
    csv_paths = sorted(glob.glob(str(BACKUPS / "canonical_real_rowtrace_production_fixed_snapshot_*.csv")))
    meta_paths = sorted(glob.glob(str(BACKUPS / "canonical_real_rowtrace_production_fixed_snapshot_metadata_*.json")))
    if not csv_paths or not meta_paths:
        raise SystemExit("canonical fixed-snapshot production artifact not found")
    return Path(csv_paths[-1]), Path(meta_paths[-1])


def parse_float(value: str | None) -> float:
    if value is None or value == "":
        return float("nan")
    return float(value)


def derive_latest_rows(source_csv: Path) -> dict[str, dict[str, str]]:
    latest_by_symbol: dict[str, dict[str, str]] = {}
    with source_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ROW_COLUMNS:
            raise SystemExit(
                f"unexpected source schema: {reader.fieldnames} != {ROW_COLUMNS}"
            )
        for row in reader:
            symbol = row["symbol"]
            current = latest_by_symbol.get(symbol)
            if current is None or row["decision_timestamp"] > current["decision_timestamp"]:
                latest_by_symbol[symbol] = row
    return latest_by_symbol


def run_runtime(rows: list[dict[str, str]], stamp: str, min_bars: int) -> list[dict[str, Any]]:
    input_path = BACKUPS / f"tmp_latest_snapshot_runtime_input_{stamp}.json"
    output_path = BACKUPS / f"tmp_latest_snapshot_runtime_output_{stamp}.json"
    write_json(input_path, rows)
    node_code = f"""
const fs = require("fs");
const path = require("path");
const ts = require("typescript");
const runtimePath = {json.dumps(str(RUNTIME_SOURCE))};
const inputPath = {json.dumps(str(input_path))};
const outputPath = {json.dumps(str(output_path))};
const source = fs.readFileSync(runtimePath, "utf8");
const transpiled = ts.transpileModule(source, {{
  compilerOptions: {{
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  }},
}}).outputText;
const tempDir = fs.mkdtempSync(path.join(require("os").tmpdir(), "uf-dynamic-latest-"));
const tempModulePath = path.join(tempDir, "uf-dynamic-decision.cjs");
fs.writeFileSync(tempModulePath, transpiled);
const mod = require(tempModulePath);
const rows = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const profile = {{
  profileId: "production_latest_fixed_snapshot_runtime_v1",
  generatedAtUtc: {json.dumps(utc_iso())},
  minBars: {min_bars},
}};
function toNumber(value) {{
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}}
const results = rows.map((row) => {{
  const input = {{
    symbol: row.symbol,
    barCount: Number(row.bar_count),
    S_UF: toNumber(row.S_UF),
    R_UF: toNumber(row.R_UF),
    D_k: toNumber(row.D_k),
    M_k: toNumber(row.M_k),
    R_rev_k: toNumber(row.R_rev_k),
    U_star_k: toNumber(row.U_star_k),
    C_k: toNumber(row.C_k),
    P_k: toNumber(row.P_k),
    B_k: toNumber(row.B_k),
  }};
  const result = mod.computePrimitiveDynamicDecision(input, profile);
  return {{
    row,
    result,
  }};
}});
fs.writeFileSync(outputPath, JSON.stringify(results));
"""
    try:
        subprocess.run(
            ["node", "-e", node_code],
            cwd=WEB_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"runtime evaluation failed: {exc.stderr or exc.stdout or exc}"
        ) from exc
    finally:
        if input_path.exists():
            input_path.unlink()
    payload = load_json(output_path)
    output_path.unlink(missing_ok=True)
    return payload


def topology(rel: dict[str, Any]) -> str:
    w = float(rel["weak_coverage"])
    w2 = float(rel["secondary_coverage"])
    if w > 0:
        return "covered"
    if w2 > 0:
        return "one_sided"
    return "double_sided"


def trajectory_family(rel: dict[str, Any]) -> str:
    fwd = float(rel["trajectory_forward"])
    contest = float(rel["trajectory_contest"])
    rupture = float(rel["trajectory_rupture"])
    if fwd == 0 and rupture == 0:
        return "still"
    if fwd > contest and fwd > rupture:
        return "constructive"
    if rupture > fwd and rupture > contest:
        return "rupture_like"
    return "contested"


def state_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[col] for col in ROW_COLUMNS[3:])


def seam_bucket(result_row: dict[str, Any]) -> bool:
    rel = result_row["result"]["termBreakdown"]["relationalFieldState"]
    decision = result_row["result"]["decision"]
    return (
        float(rel["weak_coverage"]) > 0
        and float(rel["secondary_coverage"]) > 0
        and abs(float(rel["weak_coverage"])) <= 0.03
        and float(rel["trajectory_forward"]) > float(rel["trajectory_rupture"])
        and decision in {"Accumulate", "Hold"}
    )


def covered_rupture_bucket(result_row: dict[str, Any]) -> bool:
    rel = result_row["result"]["termBreakdown"]["relationalFieldState"]
    return topology(rel) == "covered" and trajectory_family(rel) == "rupture_like"


def covered_rupture_ownership(result_rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter()
    symbols = defaultdict(int)
    for item in result_rows:
        if not covered_rupture_bucket(item):
            continue
        rel = item["result"]["termBreakdown"]["relationalFieldState"]
        decision = item["result"]["decision"]
        if decision == "Hold":
            if float(rel["hold_tendency"]) > 0:
                bucket = "hold_positive"
            elif (
                float(rel["hold_tendency"]) == 0
                and float(rel["avoid_tendency"]) == 0
                and float(rel["accumulate_tendency"]) == 0
            ):
                bucket = "hold_zero_basin_fallback"
            else:
                bucket = "hold_other"
        elif decision == "Accumulate":
            bucket = "accumulate"
        else:
            bucket = "avoid"
        counts[bucket] += 1
        symbols[f"{bucket}|{item['row']['symbol']}"] += 1
    top = {}
    for bucket in counts:
        bucket_symbols = [
            {"symbol": key.split("|", 1)[1], "count": value}
            for key, value in symbols.items()
            if key.startswith(bucket + "|")
        ]
        bucket_symbols.sort(key=lambda x: (-x["count"], x["symbol"]))
        top[bucket] = bucket_symbols[:10]
    total = sum(counts.values())
    shares = {k: (v / total if total else 0.0) for k, v in counts.items()}
    return {"counts": dict(counts), "shares": shares, "top_symbols": top}


def histogram(values: list[float], *, bins: list[float]) -> list[dict[str, Any]]:
    counts = [0 for _ in range(len(bins) - 1)]
    for value in values:
        placed = False
        for idx in range(len(bins) - 1):
            low = bins[idx]
            high = bins[idx + 1]
            if idx == len(bins) - 2:
                if low <= value <= high:
                    counts[idx] += 1
                    placed = True
                    break
            elif low <= value < high:
                counts[idx] += 1
                placed = True
                break
        if not placed and value < bins[0]:
            counts[0] += 1
        elif not placed and value > bins[-1]:
            counts[-1] += 1
    total = sum(counts)
    out = []
    for idx, count in enumerate(counts):
        out.append(
            {
                "bin_start": bins[idx],
                "bin_end": bins[idx + 1],
                "count": count,
                "share": (count / total if total else 0.0),
            }
        )
    return out


def finite_population_sample_size(n_population: int) -> int:
    z = 1.96
    p = 0.5
    e = 0.05
    numerator = n_population * (z ** 2) * p * (1 - p)
    denominator = ((n_population - 1) * (e ** 2)) + (z ** 2) * p * (1 - p)
    return math.ceil(numerator / denominator)


def geometry_expected_lean(result_row: dict[str, Any]) -> str:
    rel = result_row["result"]["termBreakdown"]["relationalFieldState"]
    topo = topology(rel)
    traj = trajectory_family(rel)
    load = float(rel["load"])
    hold_t = float(rel["hold_tendency"])
    acc_t = float(rel["accumulate_tendency"])
    avoid_t = float(rel["avoid_tendency"])

    if topo == "double_sided":
        return "Avoid"
    if topo == "covered" and traj == "constructive" and float(rel["trajectory_rupture"]) <= float(rel["trajectory_forward"]) and load <= 0.625:
        return "Accumulate"
    if traj == "still":
        return "Hold"
    if traj == "contested":
        return "Hold"
    if topo == "covered" and traj == "rupture_like" and hold_t > 0:
        return "Hold"
    if topo == "one_sided" and traj == "constructive" and acc_t > 0:
        return "Accumulate"
    if avoid_t > 0 and topo != "covered":
        return "Avoid"
    return "Hold"


def plausibility_classification(result_row: dict[str, Any]) -> dict[str, str]:
    rel = result_row["result"]["termBreakdown"]["relationalFieldState"]
    decision = result_row["result"]["decision"]
    if (
        decision == "Hold"
        and float(rel["hold_tendency"]) == 0
        and float(rel["avoid_tendency"]) == 0
        and float(rel["accumulate_tendency"]) == 0
    ):
        return {
            "expected_lean": geometry_expected_lean(result_row),
            "classification": "zero_basin_fallback",
        }
    expected = geometry_expected_lean(result_row)
    if decision == expected:
        return {"expected_lean": expected, "classification": "rational_match"}
    if expected == "Accumulate" and decision == "Hold":
        return {"expected_lean": expected, "classification": "conservative_but_plausible"}
    if expected == "Hold" and decision == "Avoid":
        return {"expected_lean": expected, "classification": "conservative_but_plausible"}
    return {"expected_lean": expected, "classification": "suspicious_mismatch"}


def weighted_summary(review_rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(float(row["sample_weight"]) for row in review_rows)
    counts = Counter()
    for row in review_rows:
        counts[row["classification"]] += float(row["sample_weight"])
    return {
        "total_weight": total,
        "weighted_counts": dict(counts),
        "weighted_shares": {k: (v / total if total else 0.0) for k, v in counts.items()},
    }


def unweighted_summary(review_rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(review_rows)
    counts = Counter(row["classification"] for row in review_rows)
    return {
        "count": total,
        "counts": dict(counts),
        "shares": {k: (v / total if total else 0.0) for k, v in counts.items()},
    }


def main() -> int:
    started = utc_now()
    stamp = utc_stamp(started)
    source_csv, source_meta_path = latest_artifacts()
    source_meta = load_json(source_meta_path)
    if int(source_meta["coverage"]["evaluation_rows"]) <= 0:
        raise SystemExit("canonical fixed-snapshot production CSV metadata reports zero rows")

    latest_by_symbol = derive_latest_rows(source_csv)
    latest_rows = [latest_by_symbol[symbol] for symbol in sorted(latest_by_symbol)]
    latest_csv = BACKUPS / f"canonical_real_snapshot_production_fixed_snapshot_latest_{stamp}.csv"
    with latest_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ROW_COLUMNS)
        writer.writeheader()
        writer.writerows(latest_rows)

    latest_csv_sha = sha256_file(latest_csv)
    source_csv_sha = sha256_file(source_csv)
    min_bars = int(source_meta["config"]["required_history_before_decision"])
    runtime_rows = run_runtime(latest_rows, stamp, min_bars)

    frozen_snapshot = source_meta.get("frozen_upstream_snapshot", {})
    artifact_identity = source_meta.get("artifact_identity", {})

    latest_metadata = {
        "generated_at_utc": utc_iso(),
        "source_mode": "derived_from_canonical_csv",
        "source_artifact_path": str(source_csv),
        "source_artifact_sha256": source_csv_sha,
        "row_count": len(latest_rows),
        "symbol_count": len(latest_by_symbol),
        "frozen_snapshot_identity": str(frozen_snapshot.get("history_cache_path", "")),
        "frozen_snapshot_sha256": frozen_snapshot.get("history_cache_sha256"),
        "runtime_git_head": artifact_identity.get("git_head") or git_head(),
        "runtime_git_worktree_dirty": artifact_identity.get("git_worktree_dirty"),
        "snapshot_csv_path": str(latest_csv),
        "snapshot_csv_sha256": latest_csv_sha,
        "source_metadata_path": str(source_meta_path),
    }
    latest_meta_path = BACKUPS / f"canonical_real_snapshot_production_fixed_snapshot_latest_metadata_{stamp}.json"
    write_json(latest_meta_path, latest_metadata)

    decision_counts = Counter()
    topology_counts = Counter()
    trajectory_counts = Counter()
    topology_trajectory_counts = Counter()
    symbol_decisions = []
    repeated = Counter()
    seam_rows = []
    non_seam_hold = 0

    w_values: list[float] = []
    w2_values: list[float] = []

    for item in runtime_rows:
        decision = item["result"]["decision"]
        rel = item["result"]["termBreakdown"]["relationalFieldState"]
        topo = topology(rel)
        traj = trajectory_family(rel)
        decision_counts[decision] += 1
        topology_counts[topo] += 1
        trajectory_counts[traj] += 1
        topology_trajectory_counts[f"{topo}|{traj}"] += 1
        symbol_decisions.append(
            {
                "symbol": item["row"]["symbol"],
                "decision_timestamp": item["row"]["decision_timestamp"],
                "decision": decision,
                "topology": topo,
                "trajectory_family": traj,
            }
        )
        repeated[state_key(item["row"])] += 1
        if seam_bucket(item):
            seam_rows.append(item)
        if decision == "Hold" and not seam_bucket(item):
            non_seam_hold += 1
        w_values.append(float(rel["weak_coverage"]))
        w2_values.append(float(rel["secondary_coverage"]))

    total = len(runtime_rows)
    repeated_rows = sum(count for count in repeated.values() if count > 1)
    top_repeated = []
    for key, count in repeated.most_common(10):
        if count <= 1:
            continue
        sample = {ROW_COLUMNS[idx + 3]: key[idx] for idx in range(len(key))}
        top_repeated.append({"count": count, "share": count / total, "state": sample})

    seam_symbol_counts = Counter(item["row"]["symbol"] for item in seam_rows)
    seam_month_counts = Counter(item["row"]["decision_timestamp"][:7] for item in seam_rows)
    seam_total = len(seam_rows)
    seam_concentration = {
        "count": seam_total,
        "share_of_latest_snapshot": (seam_total / total if total else 0.0),
        "symbol_concentration": {
            "top_symbol_share": (max(seam_symbol_counts.values()) / seam_total if seam_total else 0.0),
            "top_symbols": [
                {
                    "symbol": symbol,
                    "count": count,
                    "share": (count / seam_total if seam_total else 0.0),
                }
                for symbol, count in seam_symbol_counts.most_common(15)
            ],
        },
        "month_concentration": {
            "top_month_share": (max(seam_month_counts.values()) / seam_total if seam_total else 0.0),
            "top_months": [
                {
                    "month": month,
                    "count": count,
                    "share": (count / seam_total if seam_total else 0.0),
                }
                for month, count in seam_month_counts.most_common(12)
            ],
        },
    }

    covered_rupture = covered_rupture_ownership(runtime_rows)

    distribution_payload = {
        "generated_at_utc": utc_iso(),
        "source_snapshot_csv": str(latest_csv),
        "source_snapshot_csv_sha256": latest_csv_sha,
        "source_full_csv": str(source_csv),
        "source_full_csv_sha256": source_csv_sha,
        "total_rows": total,
        "decision_counts": dict(decision_counts),
        "decision_shares": {k: (v / total if total else 0.0) for k, v in decision_counts.items()},
        "per_symbol_decisions": symbol_decisions,
        "topology_counts": dict(topology_counts),
        "topology_shares": {k: (v / total if total else 0.0) for k, v in topology_counts.items()},
        "trajectory_family_counts": dict(trajectory_counts),
        "trajectory_family_shares": {k: (v / total if total else 0.0) for k, v in trajectory_counts.items()},
        "topology_trajectory_counts": dict(topology_trajectory_counts),
        "topology_trajectory_shares": {
            k: (v / total if total else 0.0) for k, v in topology_trajectory_counts.items()
        },
        "repeated_state_concentration": {
            "state_key": ROW_COLUMNS[3:],
            "unique_state_count": len(repeated),
            "rows_in_repeated_states": repeated_rows,
            "share_in_repeated_states": (repeated_rows / total if total else 0.0),
            "top_repeated_states": top_repeated,
        },
        "top_symbols_by_decision": {
            decision: [
                {"symbol": row["symbol"], "decision_timestamp": row["decision_timestamp"]}
                for row in symbol_decisions
                if row["decision"] == decision
            ][:25]
            for decision in ["Accumulate", "Hold", "Avoid"]
        },
        "coverage_histogram_w": histogram(w_values, bins=[-1.0, -0.25, -0.05, 0.0, 0.03, 0.1, 0.25, 1.0]),
        "coverage_histogram_w2": histogram(w2_values, bins=[-1.0, -0.25, -0.05, 0.0, 0.03, 0.1, 0.25, 1.0]),
        "seam_bucket": seam_concentration,
        "covered_rupture_like_ownership": covered_rupture,
        "non_seam_hold_majority": {
            "count": non_seam_hold,
            "share_of_all_hold": (non_seam_hold / decision_counts["Hold"] if decision_counts["Hold"] else 0.0),
        },
    }
    distribution_json = BACKUPS / f"dsf_primitive_production_latest_distribution_fixed_snapshot_{stamp}.json"
    write_json(distribution_json, distribution_payload)
    distribution_md = BACKUPS / f"dsf_primitive_production_latest_distribution_fixed_snapshot_{stamp}.md"
    write_markdown(
        distribution_md,
        f"""# Production Primitive Latest Distribution

- generated_at_utc: `{distribution_payload["generated_at_utc"]}`
- source_snapshot_csv: `{latest_csv}`
- source_snapshot_csv_sha256: `{latest_csv_sha}`
- total_rows: `{total}`
- decision_counts: `{dict(decision_counts)}`
- topology_counts: `{dict(topology_counts)}`
- trajectory_family_counts: `{dict(trajectory_counts)}`
- seam_bucket_count: `{seam_total}`
- seam_bucket_share: `{seam_concentration["share_of_latest_snapshot"]:.6f}`
- covered_rupture_like_ownership: `{covered_rupture["counts"]}`
- non_seam_hold_majority_share_of_all_hold: `{distribution_payload["non_seam_hold_majority"]["share_of_all_hold"]:.6f}`
""",
    )

    population_n = total
    sample_size = finite_population_sample_size(population_n)
    random.seed(20260321)
    global_indices = sorted(random.sample(range(total), sample_size))
    global_sample = [runtime_rows[idx] for idx in global_indices]

    strata = defaultdict(list)
    for item in runtime_rows:
        rel = item["result"]["termBreakdown"]["relationalFieldState"]
        strata[f"{item['result']['decision']}|{topology(rel)}|{trajectory_family(rel)}"].append(item)

    diagnostic_sample: list[dict[str, Any]] = []
    for stratum_key, items in sorted(strata.items()):
        decision, topo, traj = stratum_key.split("|")
        target = 0
        if decision == "Accumulate":
            target = min(len(items), max(12, math.ceil(len(items) * 0.25)))
        elif topo == "covered" and traj == "rupture_like":
            target = min(len(items), max(12, math.ceil(len(items) * 0.2)))
        elif topo == "covered" and traj == "constructive":
            target = min(len(items), max(8, math.ceil(len(items) * 0.1)))
        elif len(items) <= 8:
            target = len(items)
        elif len(items) <= 20:
            target = 6
        if target > 0:
            diagnostic_sample.extend(random.sample(items, target))

    global_weights = population_n / sample_size if sample_size else 0.0
    diagnostic_weights: dict[str, float] = {}
    for stratum_key, items in strata.items():
        sampled = [x for x in diagnostic_sample if (
            f"{x['result']['decision']}|{topology(x['result']['termBreakdown']['relationalFieldState'])}|{trajectory_family(x['result']['termBreakdown']['relationalFieldState'])}" == stratum_key
        )]
        if sampled:
            diagnostic_weights[stratum_key] = len(items) / len(sampled)

    sample_csv = BACKUPS / f"dsf_primitive_production_latest_95conf_sample_{stamp}.csv"
    sample_rows_for_csv: list[dict[str, Any]] = []
    for item in global_sample:
        rel = item["result"]["termBreakdown"]["relationalFieldState"]
        stratum_key = f"{item['result']['decision']}|{topology(rel)}|{trajectory_family(rel)}"
        sample_rows_for_csv.append(
            {
                "sample_set": "global",
                "sample_weight": global_weights,
                "stratum_key": stratum_key,
                "symbol": item["row"]["symbol"],
                "decision_timestamp": item["row"]["decision_timestamp"],
                "decision": item["result"]["decision"],
                "topology": topology(rel),
                "trajectory_family": trajectory_family(rel),
                **{col: item["row"][col] for col in ROW_COLUMNS[2:]},
            }
        )
    for item in diagnostic_sample:
        rel = item["result"]["termBreakdown"]["relationalFieldState"]
        stratum_key = f"{item['result']['decision']}|{topology(rel)}|{trajectory_family(rel)}"
        sample_rows_for_csv.append(
            {
                "sample_set": "diagnostic",
                "sample_weight": diagnostic_weights[stratum_key],
                "stratum_key": stratum_key,
                "symbol": item["row"]["symbol"],
                "decision_timestamp": item["row"]["decision_timestamp"],
                "decision": item["result"]["decision"],
                "topology": topology(rel),
                "trajectory_family": trajectory_family(rel),
                **{col: item["row"][col] for col in ROW_COLUMNS[2:]},
            }
        )
    with sample_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(sample_rows_for_csv[0].keys()))
        writer.writeheader()
        writer.writerows(sample_rows_for_csv)

    sample_report = {
        "generated_at_utc": utc_iso(),
        "population_n": population_n,
        "sample_size_formula": {
            "confidence": 0.95,
            "z": 1.96,
            "p": 0.5,
            "margin_of_error": 0.05,
            "finite_population_corrected_sample_size": sample_size,
        },
        "global_sample": {
            "count": len(global_sample),
            "weight_per_row": global_weights,
        },
        "diagnostic_sample": {
            "count": len(diagnostic_sample),
            "strata_sampled": len(diagnostic_weights),
            "weights_by_stratum": diagnostic_weights,
        },
        "sample_csv_path": str(sample_csv),
    }
    sample_report_json = BACKUPS / f"dsf_primitive_production_latest_95conf_sample_report_{stamp}.json"
    write_json(sample_report_json, sample_report)

    sampled_lookup = {
        (row["sample_set"], row["symbol"], row["decision_timestamp"]): row
        for row in sample_rows_for_csv
    }
    review_rows = []
    for sample_set, sample_items in (("global", global_sample), ("diagnostic", diagnostic_sample)):
        for item in sample_items:
            rel = item["result"]["termBreakdown"]["relationalFieldState"]
            csv_row = sampled_lookup[(sample_set, item["row"]["symbol"], item["row"]["decision_timestamp"])]
            review = plausibility_classification(item)
            review_rows.append(
                {
                    "sample_set": sample_set,
                    "sample_weight": csv_row["sample_weight"],
                    "symbol": item["row"]["symbol"],
                    "decision_timestamp": item["row"]["decision_timestamp"],
                    "runtime_decision": item["result"]["decision"],
                    "expected_lean": review["expected_lean"],
                    "classification": review["classification"],
                    "topology": topology(rel),
                    "trajectory_family": trajectory_family(rel),
                    "weak_coverage": rel["weak_coverage"],
                    "secondary_coverage": rel["secondary_coverage"],
                    "trajectory_forward": rel["trajectory_forward"],
                    "trajectory_contest": rel["trajectory_contest"],
                    "trajectory_rupture": rel["trajectory_rupture"],
                    "load": rel["load"],
                    "hold_tendency": rel["hold_tendency"],
                    "accumulate_tendency": rel["accumulate_tendency"],
                    "avoid_tendency": rel["avoid_tendency"],
                }
            )

    weighted_global = weighted_summary([row for row in review_rows if row["sample_set"] == "global"])
    unweighted_all = unweighted_summary(review_rows)
    plausibility_payload = {
        "generated_at_utc": utc_iso(),
        "review_type": "production-plausible primitive sorting review",
        "source_snapshot_csv": str(latest_csv),
        "source_snapshot_csv_sha256": latest_csv_sha,
        "weighted_global_summary": weighted_global,
        "unweighted_all_summary": unweighted_all,
        "rows": review_rows,
    }
    plausibility_json = BACKUPS / f"dsf_primitive_production_latest_95conf_plausibility_review_{stamp}.json"
    write_json(plausibility_json, plausibility_payload)
    plausibility_md = BACKUPS / f"dsf_primitive_production_latest_95conf_plausibility_review_{stamp}.md"
    write_markdown(
        plausibility_md,
        f"""# Production-Plausible Primitive Sorting Review

- generated_at_utc: `{plausibility_payload["generated_at_utc"]}`
- source_snapshot_csv: `{latest_csv}`
- weighted_global_summary: `{weighted_global}`
- unweighted_all_summary: `{unweighted_all}`
""",
    )

    weighted_ok = (
        weighted_global["weighted_shares"].get("suspicious_mismatch", 0.0) < 0.2
        and weighted_global["weighted_shares"].get("zero_basin_fallback", 0.0) < 0.1
    )
    top_symbol_counts = Counter(item["row"]["symbol"] for item in runtime_rows if item["result"]["decision"] == "Hold")
    dominant_symbol = top_symbol_counts.most_common(1)[0] if top_symbol_counts else (None, 0)
    final_payload = {
        "generated_at_utc": utc_iso(),
        "frozen_source_identity": {
            "full_csv": str(source_csv),
            "full_csv_sha256": source_csv_sha,
            "latest_snapshot_csv": str(latest_csv),
            "latest_snapshot_csv_sha256": latest_csv_sha,
            "metadata": latest_metadata,
        },
        "latest_snapshot_decision_distribution": {
            "counts": dict(decision_counts),
            "shares": {k: (v / total if total else 0.0) for k, v in decision_counts.items()},
        },
        "sample_method": sample_report["sample_size_formula"],
        "weighted_plausibility_summary": weighted_global,
        "unweighted_plausibility_summary": unweighted_all,
        "dominant_symbol_concentrations": {
            "top_hold_symbol": {
                "symbol": dominant_symbol[0],
                "count": dominant_symbol[1],
                "share_of_hold": (dominant_symbol[1] / decision_counts["Hold"] if decision_counts["Hold"] else 0.0),
            },
            "seam_top_symbol_share": seam_concentration["symbol_concentration"]["top_symbol_share"],
        },
        "sorting_decision": {
            "appears_to_reasonably_sort_latest_fixed_snapshot_universe": weighted_ok,
            "wording": (
                "production-plausible primitive sorting review supports reasonable latest fixed-snapshot sorting"
                if weighted_ok
                else "production-plausible primitive sorting review does not yet support reasonable latest fixed-snapshot sorting"
            ),
        },
    }
    final_json = BACKUPS / f"dsf_primitive_production_latest_snapshot_decision_{stamp}.json"
    write_json(final_json, final_payload)
    final_md = BACKUPS / f"dsf_primitive_production_latest_snapshot_decision_{stamp}.md"
    write_markdown(
        final_md,
        f"""# Latest Fixed-Snapshot Primitive Sorting Decision

- frozen_source_identity.full_csv: `{source_csv}`
- frozen_source_identity.full_csv_sha256: `{source_csv_sha}`
- latest_snapshot_csv: `{latest_csv}`
- latest_snapshot_csv_sha256: `{latest_csv_sha}`
- latest_snapshot_decision_distribution: `{final_payload["latest_snapshot_decision_distribution"]}`
- sample_method: `{sample_report["sample_size_formula"]}`
- weighted_plausibility_summary: `{weighted_global}`
- unweighted_plausibility_summary: `{unweighted_all}`
- dominant_symbol_concentrations: `{final_payload["dominant_symbol_concentrations"]}`
- sorting_decision: `{final_payload["sorting_decision"]}`
""",
    )

    summary = {
        "latest_snapshot_csv": str(latest_csv),
        "latest_snapshot_metadata": str(latest_meta_path),
        "distribution_json": str(distribution_json),
        "distribution_md": str(distribution_md),
        "sample_csv": str(sample_csv),
        "sample_report_json": str(sample_report_json),
        "plausibility_json": str(plausibility_json),
        "plausibility_md": str(plausibility_md),
        "final_json": str(final_json),
        "final_md": str(final_md),
        "elapsed_seconds": round((utc_now() - started).total_seconds(), 3),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
