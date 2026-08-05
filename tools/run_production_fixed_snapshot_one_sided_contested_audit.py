#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
WEB_ROOT = REPO_ROOT / "web"
RUNTIME_SOURCE = WEB_ROOT / "src" / "lib" / "uf-dynamic-decision.ts"

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

MEDIAN_FIELDS = [
    "S_UF",
    "R_UF",
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
    "weak_coverage",
    "secondary_coverage",
    "edge_support",
    "trajectory_forward",
    "trajectory_contest",
    "trajectory_rupture",
    "load",
    "hold_tendency",
    "accumulate_tendency",
    "avoid_tendency",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.strftime("%Y%m%dT%H%M%SZ")


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


def main() -> int:
    started = utc_now()
    stamp = utc_stamp(started)
    source_csv, source_meta_path = latest_paths()
    source_meta = load_json(source_meta_path)

    summary_path = BACKUPS / f"tmp_one_sided_contested_full_summary_{stamp}.json"

    node_script = f"""
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");
const ts = require("typescript");

const sourceCsv = {json.dumps(str(source_csv))};
const runtimePath = {json.dumps(str(RUNTIME_SOURCE))};
const summaryPath = {json.dumps(str(summary_path))};
const EXPECTED_COLUMNS = {json.dumps(EXPECTED_COLUMNS)};
const MEDIAN_FIELDS = {json.dumps(MEDIAN_FIELDS)};

const runtimeSource = fs.readFileSync(runtimePath, "utf8");
const transpiled = ts.transpileModule(runtimeSource, {{
  compilerOptions: {{
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  }},
}}).outputText;
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "uf-dynamic-one-sided-contested-"));
const tempModulePath = path.join(tempDir, "uf-dynamic-decision.cjs");
fs.writeFileSync(tempModulePath, transpiled);
const mod = require(tempModulePath);

const profile = {{
  profileId: "production_fixed_snapshot_one_sided_contested_audit_v1",
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

function pushMedian(target, key, value) {{
  if (!Number.isFinite(value)) return;
  if (!target[key]) target[key] = [];
  target[key].push(value);
}}

const rl = readline.createInterface({{
  input: fs.createReadStream(sourceCsv),
  crlfDelay: Infinity,
}});

let lineIndex = 0;
let header = null;
let totalOneSidedContested = 0;
const byDecision = {{}};
const byDecisionCounts = {{}};
const topSymbols = {{}};
const sampleRows = [];

rl.on("line", (line) => {{
  lineIndex += 1;
  if (lineIndex === 1) {{
    header = splitCsv(line);
    return;
  }}
  if (!line) return;
  const parts = splitCsv(line);
  if (parts.length !== EXPECTED_COLUMNS.length) return;
  const row = Object.fromEntries(EXPECTED_COLUMNS.map((col, i) => [col, parts[i]]));
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
  const rel = result.termBreakdown.relationalFieldState;
  if (topology(rel) !== "one_sided" || trajectoryFamily(rel) !== "contested") {{
    return;
  }}
  totalOneSidedContested += 1;
  const decision = result.decision;
  byDecisionCounts[decision] = (byDecisionCounts[decision] || 0) + 1;
  if (!byDecision[decision]) byDecision[decision] = {{}};
  if (!topSymbols[decision]) topSymbols[decision] = {{}};
  topSymbols[decision][row.symbol] = (topSymbols[decision][row.symbol] || 0) + 1;

  pushMedian(byDecision[decision], "S_UF", Number(row.S_UF));
  pushMedian(byDecision[decision], "R_UF", Number(row.R_UF));
  pushMedian(byDecision[decision], "D_k", Number(row.D_k));
  pushMedian(byDecision[decision], "M_k", Number(row.M_k));
  pushMedian(byDecision[decision], "R_rev_k", Number(row.R_rev_k));
  pushMedian(byDecision[decision], "U_star_k", Number(row.U_star_k));
  pushMedian(byDecision[decision], "C_k", Number(row.C_k));
  pushMedian(byDecision[decision], "P_k", Number(row.P_k));
  pushMedian(byDecision[decision], "B_k", Number(row.B_k));
  pushMedian(byDecision[decision], "weak_coverage", Number(rel.weak_coverage));
  pushMedian(byDecision[decision], "secondary_coverage", Number(rel.secondary_coverage));
  pushMedian(byDecision[decision], "edge_support", Number(rel.edge_support));
  pushMedian(byDecision[decision], "trajectory_forward", Number(rel.trajectory_forward));
  pushMedian(byDecision[decision], "trajectory_contest", Number(rel.trajectory_contest));
  pushMedian(byDecision[decision], "trajectory_rupture", Number(rel.trajectory_rupture));
  pushMedian(byDecision[decision], "load", Number(rel.load));
  pushMedian(byDecision[decision], "hold_tendency", Number(rel.hold_tendency));
  pushMedian(byDecision[decision], "accumulate_tendency", Number(rel.accumulate_tendency));
  pushMedian(byDecision[decision], "avoid_tendency", Number(rel.avoid_tendency));

  if (sampleRows.length < 30) {{
    sampleRows.push({{
      symbol: row.symbol,
      decision_timestamp: row.decision_timestamp,
      decision,
      S_UF: Number(row.S_UF),
      R_UF: Number(row.R_UF),
      D_k: Number(row.D_k),
      M_k: Number(row.M_k),
      R_rev_k: Number(row.R_rev_k),
      U_star_k: Number(row.U_star_k),
      C_k: Number(row.C_k),
      P_k: Number(row.P_k),
      B_k: Number(row.B_k),
      weak_coverage: Number(rel.weak_coverage),
      secondary_coverage: Number(rel.secondary_coverage),
      trajectory_forward: Number(rel.trajectory_forward),
      trajectory_contest: Number(rel.trajectory_contest),
      trajectory_rupture: Number(rel.trajectory_rupture),
      hold_tendency: Number(rel.hold_tendency),
      accumulate_tendency: Number(rel.accumulate_tendency),
      avoid_tendency: Number(rel.avoid_tendency),
    }});
  }}
}});

function median(values) {{
  if (!values || values.length === 0) return null;
  values.sort((a, b) => a - b);
  const mid = Math.floor(values.length / 2);
  if (values.length % 2 === 1) return values[mid];
  return 0.5 * (values[mid - 1] + values[mid]);
}}

rl.on("close", () => {{
  const populations = {{}};
  for (const [decision, fields] of Object.entries(byDecision)) {{
    populations[decision.toLowerCase()] = {{ count: byDecisionCounts[decision] }};
    for (const field of MEDIAN_FIELDS) {{
      populations[decision.toLowerCase()][`median_${{field}}`] = median(fields[field]);
    }}
  }}
  const top = {{}};
  for (const [decision, symbolCounts] of Object.entries(topSymbols)) {{
    const total = byDecisionCounts[decision] || 0;
    top[decision] = Object.entries(symbolCounts)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, 20)
      .map(([symbol, count]) => ({{
        symbol,
        count,
        share: total ? count / total : 0,
      }}));
  }}
  const payload = {{
    generated_at_utc: {json.dumps(utc_iso())},
    source_frozen_csv: sourceCsv,
    requested_measurement: "full production fixed-snapshot exact one-sided contested boundary audit under baseline runtime",
    totals: {{
      all_one_sided_contested_rows: totalOneSidedContested,
      avoid: byDecisionCounts.Avoid || 0,
      hold: byDecisionCounts.Hold || 0,
      accumulate: byDecisionCounts.Accumulate || 0,
      non_avoid_combined: (byDecisionCounts.Hold || 0) + (byDecisionCounts.Accumulate || 0),
      avoid_share: totalOneSidedContested ? (byDecisionCounts.Avoid || 0) / totalOneSidedContested : 0,
    }},
    decision_counts: byDecisionCounts,
    populations,
    top_symbols: top,
    sample_rows: sampleRows,
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
        raise SystemExit(proc.stderr or proc.stdout or "one-sided contested audit failed")

    payload = load_json(summary_path)

    out_json = BACKUPS / f"dsf_primitive_production_one_sided_contested_full_audit_fixed_snapshot_{stamp}.json"
    out_md = BACKUPS / f"dsf_primitive_production_one_sided_contested_full_audit_fixed_snapshot_{stamp}.md"
    write_json(out_json, payload)
    write_markdown(
        out_md,
        f"""# Full Production One-Sided Contested Audit

- generated_at_utc: `{payload["generated_at_utc"]}`
- source_frozen_csv: `{source_csv}`
- all_one_sided_contested_rows: `{payload["totals"]["all_one_sided_contested_rows"]}`
- decision_counts: `{payload["decision_counts"]}`
- avoid_share: `{payload["totals"]["avoid_share"]:.6f}`
""",
    )

    summary_path.unlink(missing_ok=True)

    print(
        json.dumps(
            {
                "audit_json": str(out_json),
                "audit_md": str(out_md),
                "elapsed_seconds": round((utc_now() - started).total_seconds(), 3),
                "source_metadata": str(source_meta_path),
                "source_row_count": source_meta["artifact_identity"]["row_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
