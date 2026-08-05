#!/usr/bin/env python3
from __future__ import annotations

import glob
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
WEB_ROOT = REPO_ROOT / "web"
RUNTIME_SOURCE = WEB_ROOT / "src" / "lib" / "uf-dynamic-decision.ts"
PRESSURE_SOURCE = WEB_ROOT / "src" / "lib" / "uf-dynamic-decision-pressure-test.ts"
DOC_SOURCE = REPO_ROOT / "DSF_PRIMITIVE_INTERPRETATION_RECOVERY.md"

EXPECTED_COLUMNS = [
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


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def write_markdown(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def latest_paths() -> tuple[Path, Path]:
    csv_paths = sorted(glob.glob(str(BACKUPS / "canonical_real_rowtrace_production_fixed_snapshot_*.csv")))
    meta_paths = sorted(glob.glob(str(BACKUPS / "canonical_real_rowtrace_production_fixed_snapshot_metadata_*.json")))
    if not csv_paths or not meta_paths:
        raise SystemExit("canonical production fixed-snapshot artifact not found")
    return Path(csv_paths[-1]), Path(meta_paths[-1])


def run_runtime_behavior_tests() -> dict:
    node_script = f"""
const fs = require("fs");
const os = require("os");
const path = require("path");
const ts = require("typescript");

const runtimePath = {json.dumps(str(RUNTIME_SOURCE))};
const source = fs.readFileSync(runtimePath, "utf8");
const transpiled = ts.transpileModule(source, {{
  compilerOptions: {{
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  }},
}}).outputText;

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "uf-dynamic-runtime-audit-"));
const tempModulePath = path.join(tempDir, "uf-dynamic-decision.cjs");
fs.writeFileSync(tempModulePath, transpiled);
const mod = require(tempModulePath);

const profile = {{
  profileId: "production_fixed_snapshot_gate_profile_v1",
  generatedAtUtc: "2026-03-21T00:00:00Z",
  minBars: 252,
}};

const validInput = {{
  symbol: "TEST",
  barCount: 300,
  S_UF: 0.9,
  R_UF: 0.8,
  D_k: 1,
  M_k: 0,
  R_rev_k: 0,
  U_star_k: 0.2,
  C_k: 3,
  P_k: 0,
  B_k: 0,
}};

function runCase(name, input, expect) {{
  const result = mod.computePrimitiveDynamicDecision(input, profile);
  return {{
    name,
    ok: expect(result),
    blockerCode: result.blockerCode,
    blockerActive: result.blockerActive,
    decision: result.decision
  }};
}}

const cases = [];
cases.push(runCase("row_not_found_blocks", null, (result) =>
  result.blockerCode === "ROW_NOT_FOUND" && result.blockerActive === true
));
cases.push(runCase("insufficient_bars_blocks", {{ ...validInput, barCount: 100 }}, (result) =>
  result.blockerCode === "INSUFFICIENT_BARS" && result.blockerActive === true
));
cases.push(runCase("valid_row_unblocked", validInput, (result) =>
  result.blockerCode === "NONE" && result.blockerActive === false
));
process.stdout.write(JSON.stringify({{
  all_passed: cases.every((item) => item.ok),
  cases
}}));
"""
    proc = subprocess.run(
        ["node", "-e", node_script],
        cwd=str(WEB_ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return {
            "all_passed": False,
            "execution_failed": True,
            "stdout_tail": proc.stdout.splitlines()[-40:],
            "stderr_tail": proc.stderr.splitlines()[-40:],
            "cases": [],
        }
    payload = json.loads(proc.stdout)
    payload["execution_failed"] = False
    return payload


def main() -> int:
    started = utc_now()
    stamp = utc_stamp(started)
    source_csv, source_meta_path = latest_paths()
    source_meta = load_json(source_meta_path)
    source_csv_sha = sha256_file(source_csv)

    summary_path = BACKUPS / f"tmp_full_gate_distribution_summary_{stamp}.json"
    state_keys_path = BACKUPS / f"tmp_full_gate_distribution_state_keys_{stamp}.txt"

    node_script = f"""
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");
const ts = require("typescript");

const sourceCsv = {json.dumps(str(source_csv))};
const summaryPath = {json.dumps(str(summary_path))};
const stateKeysPath = {json.dumps(str(state_keys_path))};
const runtimePath = {json.dumps(str(RUNTIME_SOURCE))};

const runtimeSource = fs.readFileSync(runtimePath, "utf8");
const transpiled = ts.transpileModule(runtimeSource, {{
  compilerOptions: {{
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  }},
}}).outputText;
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "uf-dynamic-full-pass-"));
const tempModulePath = path.join(tempDir, "uf-dynamic-decision.cjs");
fs.writeFileSync(tempModulePath, transpiled);
const mod = require(tempModulePath);

const EXPECTED_COLUMNS = {json.dumps(EXPECTED_COLUMNS)};
const profile = {{
  profileId: "production_fixed_snapshot_full_distribution_v1",
  generatedAtUtc: {json.dumps(utc_iso())},
  minBars: 252,
}};

function toNumber(value) {{
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}}

function splitCsv(line) {{
  return line.split(",");
}}

function incCounter(map, key, delta = 1) {{
  map[key] = (map[key] || 0) + delta;
}}

const rl = readline.createInterface({{
  input: fs.createReadStream(sourceCsv),
  crlfDelay: Infinity,
}});

const stateKeyStream = fs.createWriteStream(stateKeysPath, {{ encoding: "utf8" }});

let lineIndex = 0;
let header = null;
let rowCount = 0;
let rowViolationCount = 0;
let blockerBehaviorStatus = "pass";
let schemaExact = false;
let fieldOrderExact = false;
const decisionCounts = {{}};
const blockerCounts = {{}};
const topologyCounts = {{}};
const trajectoryCounts = {{}};
const topologyTrajectoryCounts = {{}};
const symbolCounts = {{}};
const symbolDecisionCounts = {{}};
const seamSymbolCounts = {{}};
const seamMonthCounts = {{}};
const coveredRuptureOwnership = {{}};
let seamCount = 0;
let nonSeamHoldCount = 0;

function topology(rel) {{
  const w = Number(rel.weak_coverage);
  const w2 = Number(rel.secondary_coverage);
  if (w > 0) return "covered";
  if (w2 > 0) return "one_sided";
  return "double_sided";
}}

function trajectoryFamily(rel) {{
  const f = Number(rel.trajectory_forward);
  const c = Number(rel.trajectory_contest);
  const r = Number(rel.trajectory_rupture);
  if (f === 0 && r === 0) return "still";
  if (f > c && f > r) return "constructive";
  if (r > f && r > c) return "rupture_like";
  return "contested";
}}

function isSeam(result) {{
  const rel = result.termBreakdown.relationalFieldState;
  return Number(rel.weak_coverage) > 0 &&
    Number(rel.secondary_coverage) > 0 &&
    Math.abs(Number(rel.weak_coverage)) <= 0.03 &&
    Number(rel.trajectory_forward) > Number(rel.trajectory_rupture) &&
    (result.decision === "Accumulate" || result.decision === "Hold");
}}

rl.on("line", (line) => {{
  lineIndex += 1;
  if (lineIndex === 1) {{
    header = splitCsv(line);
    schemaExact = JSON.stringify(header) === JSON.stringify(EXPECTED_COLUMNS);
    fieldOrderExact = schemaExact;
    return;
  }}
  if (!line) return;
  const parts = splitCsv(line);
  if (parts.length !== EXPECTED_COLUMNS.length) {{
    rowViolationCount += 1;
    return;
  }}
  const row = Object.fromEntries(EXPECTED_COLUMNS.map((col, i) => [col, parts[i]]));
  rowCount += 1;

  const barCount = Number(row.bar_count);
  const numericCols = ["S_UF","R_UF","D_k","M_k","R_rev_k","U_star_k","C_k","P_k","B_k"];
  let valid = Number.isFinite(barCount) && Number.isInteger(barCount) && barCount >= 252;
  for (const col of numericCols) {{
    if (!Number.isFinite(Number(row[col]))) valid = false;
  }}
  if (!valid) rowViolationCount += 1;

  const input = {{
    symbol: row.symbol,
    barCount,
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
  if (result.blockerActive) blockerBehaviorStatus = "failed";
  incCounter(decisionCounts, result.decision);
  incCounter(blockerCounts, result.blockerCode);
  incCounter(symbolCounts, row.symbol);
  incCounter(symbolDecisionCounts, `${{result.decision}}|${{row.symbol}}`);

  const rel = result.termBreakdown.relationalFieldState;
  const topo = topology(rel);
  const traj = trajectoryFamily(rel);
  incCounter(topologyCounts, topo);
  incCounter(trajectoryCounts, traj);
  incCounter(topologyTrajectoryCounts, `${{topo}}|${{traj}}`);

  if (isSeam(result)) {{
    seamCount += 1;
    incCounter(seamSymbolCounts, row.symbol);
    incCounter(seamMonthCounts, row.decision_timestamp.slice(0, 7));
  }}
  if (result.decision === "Hold" && !isSeam(result)) {{
    nonSeamHoldCount += 1;
  }}

  if (topo === "covered" && traj === "rupture_like") {{
    const h = Number(rel.hold_tendency);
    const a = Number(rel.accumulate_tendency);
    const av = Number(rel.avoid_tendency);
    let bucket = result.decision.toLowerCase();
    if (result.decision === "Hold") {{
      if (h > 0) bucket = "hold_positive";
      else if (h === 0 && a === 0 && av === 0) bucket = "hold_zero_basin_fallback";
      else bucket = "hold_other";
    }}
    incCounter(coveredRuptureOwnership, bucket);
  }}

  stateKeyStream.write([
    row.S_UF,row.R_UF,row.D_k,row.M_k,row.R_rev_k,row.U_star_k,row.C_k,row.P_k,row.B_k
  ].join("|") + "\\n");
}});

rl.on("close", () => {{
  stateKeyStream.end();
  const payload = {{
    generated_at_utc: {json.dumps(utc_iso())},
    source_csv: sourceCsv,
    row_count: rowCount,
    schema_exact: schemaExact,
    field_order_exact: fieldOrderExact,
    blocker_behavior_status: blockerBehaviorStatus,
    row_violation_count: rowViolationCount,
    decision_counts: decisionCounts,
    blocker_counts: blockerCounts,
    topology_counts: topologyCounts,
    trajectory_counts: trajectoryCounts,
    topology_trajectory_counts: topologyTrajectoryCounts,
    symbol_counts: symbolCounts,
    symbol_decision_counts: symbolDecisionCounts,
    seam_count: seamCount,
    seam_symbol_counts: seamSymbolCounts,
    seam_month_counts: seamMonthCounts,
    non_seam_hold_count: nonSeamHoldCount,
    covered_rupture_ownership: coveredRuptureOwnership,
    state_keys_path: stateKeysPath,
  }};
  fs.writeFileSync(summaryPath, JSON.stringify(payload));
}});
"""

    proc = subprocess.run(
        ["node", "-e", node_script],
        cwd=str(WEB_ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr or proc.stdout or "node full-pass failed")

    summary = load_json(summary_path)

    sorted_states_path = BACKUPS / f"tmp_full_gate_distribution_state_counts_{stamp}.txt"
    sort_proc = subprocess.run(
        f"LC_ALL=C sort {state_keys_path} | uniq -c > {sorted_states_path}",
        cwd=str(REPO_ROOT),
        shell=True,
        capture_output=True,
        text=True,
    )
    if sort_proc.returncode != 0:
        raise SystemExit(sort_proc.stderr or sort_proc.stdout or "state count sort failed")

    unique_state_count = 0
    rows_in_repeated_states = 0
    top_repeated_states: list[dict] = []
    with sorted_states_path.open("r", encoding="utf-8") as f:
        for line in f:
            count_str, key = line.lstrip().split(" ", 1)
            count = int(count_str)
            key = key.rstrip("\n")
            unique_state_count += 1
            if count > 1:
                rows_in_repeated_states += count
                state = key.split("|")
                top_repeated_states.append(
                    {
                        "count": count,
                        "state": {
                            "S_UF": state[0],
                            "R_UF": state[1],
                            "D_k": state[2],
                            "M_k": state[3],
                            "R_rev_k": state[4],
                            "U_star_k": state[5],
                            "C_k": state[6],
                            "P_k": state[7],
                            "B_k": state[8],
                        },
                    }
                )
    top_repeated_states.sort(key=lambda x: -x["count"])
    top_repeated_states = top_repeated_states[:15]

    runtime_behavior = run_runtime_behavior_tests()

    artifact_identity = source_meta.get("artifact_identity", {})
    frozen_snapshot = source_meta.get("frozen_upstream_snapshot", {})

    total_rows = int(summary["row_count"])
    decision_counts = summary["decision_counts"]
    hold_count = int(decision_counts.get("Hold", 0))
    seam_count = int(summary["seam_count"])
    seam_symbol_counts = summary["seam_symbol_counts"]
    seam_month_counts = summary["seam_month_counts"]
    symbol_decision_counts = summary["symbol_decision_counts"]

    eval_payload = {
        "generated_at_utc": utc_iso(),
        "source_frozen_csv": str(source_csv),
        "source_frozen_csv_sha256": source_csv_sha,
        "blocker_behavior_status": summary["blocker_behavior_status"],
        "row_violation_count": int(summary["row_violation_count"]),
        "label_counts": decision_counts,
        "topology_occupancy": summary["topology_counts"],
        "trajectory_family_occupancy": summary["trajectory_counts"],
        "schema_exact": bool(summary["schema_exact"]),
        "field_order_exact": bool(summary["field_order_exact"]),
        "runtime_behavior": runtime_behavior,
        "source_metadata": str(source_meta_path),
    }
    eval_json = BACKUPS / f"uf_dynamic_decision_native_rowtrace_eval_production_fixed_snapshot_{stamp}.json"
    write_json(eval_json, eval_payload)

    distribution_payload = {
        "generated_at_utc": utc_iso(),
        "source_frozen_csv": str(source_csv),
        "source_frozen_csv_sha256": source_csv_sha,
        "total_rows": total_rows,
        "decision_counts": decision_counts,
        "decision_shares": {k: (v / total_rows if total_rows else 0.0) for k, v in decision_counts.items()},
        "topology_counts": summary["topology_counts"],
        "topology_shares": {k: (v / total_rows if total_rows else 0.0) for k, v in summary["topology_counts"].items()},
        "trajectory_family_counts": summary["trajectory_counts"],
        "trajectory_family_shares": {k: (v / total_rows if total_rows else 0.0) for k, v in summary["trajectory_counts"].items()},
        "topology_trajectory_counts": summary["topology_trajectory_counts"],
        "topology_trajectory_shares": {
            k: (v / total_rows if total_rows else 0.0) for k, v in summary["topology_trajectory_counts"].items()
        },
        "repeated_state_concentration": {
            "unique_state_count": unique_state_count,
            "rows_in_repeated_states": rows_in_repeated_states,
            "share_in_repeated_states": (rows_in_repeated_states / total_rows if total_rows else 0.0),
            "top_repeated_states": [
                {
                    "count": item["count"],
                    "share": (item["count"] / total_rows if total_rows else 0.0),
                    "state": item["state"],
                }
                for item in top_repeated_states
            ],
        },
        "top_symbols_by_decision": {
            decision: [
                {
                    "symbol": key.split("|", 1)[1],
                    "count": value,
                    "share_of_decision": (value / decision_counts[decision] if decision_counts.get(decision) else 0.0),
                }
                for key, value in sorted(
                    (
                        (key, value)
                        for key, value in symbol_decision_counts.items()
                        if key.startswith(decision + "|")
                    ),
                    key=lambda item: (-item[1], item[0]),
                )[:25]
            ]
            for decision in ["Accumulate", "Hold", "Avoid"]
        },
        "seam_bucket": {
            "count": seam_count,
            "share_of_total_rows": (seam_count / total_rows if total_rows else 0.0),
            "symbol_concentration": {
                "top_symbol_share": (max(seam_symbol_counts.values()) / seam_count if seam_count else 0.0),
                "top_symbols": [
                    {
                        "symbol": symbol,
                        "count": count,
                        "share": (count / seam_count if seam_count else 0.0),
                    }
                    for symbol, count in sorted(seam_symbol_counts.items(), key=lambda item: (-item[1], item[0]))[:25]
                ],
            },
            "month_concentration": {
                "top_month_share": (max(seam_month_counts.values()) / seam_count if seam_count else 0.0),
                "top_months": [
                    {
                        "month": month,
                        "count": count,
                        "share": (count / seam_count if seam_count else 0.0),
                    }
                    for month, count in sorted(seam_month_counts.items(), key=lambda item: (-item[1], item[0]))[:25]
                ],
            },
        },
        "covered_rupture_like_basin_ownership": summary["covered_rupture_ownership"],
        "non_seam_hold_majority": {
            "count": int(summary["non_seam_hold_count"]),
            "share_of_all_hold": (int(summary["non_seam_hold_count"]) / hold_count if hold_count else 0.0),
        },
        "artifact_identity": artifact_identity,
        "frozen_upstream_snapshot": frozen_snapshot,
    }
    distribution_json = BACKUPS / f"dsf_primitive_production_distribution_fixed_snapshot_{stamp}.json"
    write_json(distribution_json, distribution_payload)
    distribution_md = BACKUPS / f"dsf_primitive_production_distribution_fixed_snapshot_{stamp}.md"
    write_markdown(
        distribution_md,
        f"""# Production Primitive Distribution

- generated_at_utc: `{distribution_payload["generated_at_utc"]}`
- source_frozen_csv: `{source_csv}`
- source_frozen_csv_sha256: `{source_csv_sha}`
- total_rows: `{total_rows}`
- decision_counts: `{decision_counts}`
- topology_counts: `{summary["topology_counts"]}`
- trajectory_family_counts: `{summary["trajectory_counts"]}`
- seam_bucket_count: `{seam_count}`
- seam_bucket_share: `{distribution_payload["seam_bucket"]["share_of_total_rows"]:.6f}`
- covered_rupture_like_basin_ownership: `{summary["covered_rupture_ownership"]}`
- non_seam_hold_majority_share_of_all_hold: `{distribution_payload["non_seam_hold_majority"]["share_of_all_hold"]:.6f}`
- repeated_state_share: `{distribution_payload["repeated_state_concentration"]["share_in_repeated_states"]:.6f}`
""",
    )

    cleanup_targets = [summary_path, state_keys_path, sorted_states_path]
    for path in cleanup_targets:
        Path(path).unlink(missing_ok=True)

    print(
        json.dumps(
            {
                "eval_json": str(eval_json),
                "distribution_json": str(distribution_json),
                "distribution_md": str(distribution_md),
                "elapsed_seconds": round((utc_now() - started).total_seconds(), 3),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
