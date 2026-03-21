#!/usr/bin/env python3
from __future__ import annotations

import glob
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
WEB_ROOT = REPO_ROOT / "web"
RUNTIME_SOURCE = WEB_ROOT / "src" / "lib" / "uf-dynamic-decision-unified-field.ts"

BASELINE_SYNTHETIC_VALIDATION = BACKUPS / "dsf_primitive_production_synthetic_validation_20260321T044121Z.json"
BASELINE_FULL_DISTRIBUTION = BACKUPS / "dsf_primitive_production_distribution_fixed_snapshot_20260321T035659Z.json"
BASELINE_LATEST_SNAPSHOT_DECISION = BACKUPS / "dsf_primitive_production_latest_snapshot_decision_20260321T013943Z.json"
BASELINE_ONE_SIDED_CONTESTED = BACKUPS / "dsf_primitive_production_one_sided_contested_full_audit_fixed_snapshot_20260321T055330Z.json"

ANCHORS = [
    ("AGO", "Accumulate", "Accumulate anchor 1"),
    ("TXRH", "Accumulate", "Accumulate anchor 2"),
    ("DHI", "Accumulate", "Accumulate anchor 3"),
    ("AAT", "Hold", "Hold anchor 1"),
    ("ACGL", "Hold", "Hold anchor 2"),
    ("ADC", "Hold", "Hold anchor 3"),
    ("AA", "Avoid", "Avoid anchor 1"),
    ("AAPL", "Avoid", "Avoid anchor 2"),
    ("ACLS", "Avoid", "Avoid anchor 3"),
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


def latest_file(prefix: str, suffix: str) -> Path:
    matches = sorted(glob.glob(str(BACKUPS / f"{prefix}*{suffix}")))
    if not matches:
        raise SystemExit(f"missing artifact for {prefix}*{suffix}")
    return Path(matches[-1])


def run_node_validation(
    summary_path: Path,
    source_csv: Path,
    latest_snapshot_csv: Path,
    synthetic_suite_path: Path,
) -> dict:
    node_script = f"""
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");
const Module = require("module");

const ROOT = {json.dumps(str(REPO_ROOT))};
const WEB_ROOT = {json.dumps(str(WEB_ROOT))};
const WEB_PACKAGE_JSON = path.join(WEB_ROOT, "package.json");
const requireFromWeb = Module.createRequire(WEB_PACKAGE_JSON);
const ts = requireFromWeb("typescript");

const runtimePath = {json.dumps(str(RUNTIME_SOURCE))};
const sourceCsv = {json.dumps(str(source_csv))};
const latestSnapshotCsv = {json.dumps(str(latest_snapshot_csv))};
const syntheticSuitePath = {json.dumps(str(synthetic_suite_path))};
const summaryPath = {json.dumps(str(summary_path))};

const runtimeSource = fs.readFileSync(runtimePath, "utf8");
const transpiled = ts.transpileModule(runtimeSource, {{
  compilerOptions: {{
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  }},
}}).outputText;
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "uf-unified-field-v3-"));
const tempModulePath = path.join(tempDir, "uf-dynamic-decision-unified-field.cjs");
fs.writeFileSync(tempModulePath, transpiled);
const mod = require(tempModulePath);

const anchorCases = {json.dumps(ANCHORS)};

function splitCsv(line) {{
  return line.split(",");
}}

function toInputFromRow(row) {{
  return {{
    symbol: row.symbol,
    barCount: Number(row.bar_count),
    S_UF: row.S_UF,
    R_UF: row.R_UF,
    D_k: row.D_k,
    M_k: row.M_k,
    R_rev_k: row.R_rev_k,
    U_star_k: row.U_star_k,
    C_k: row.C_k,
    P_k: row.P_k,
    B_k: row.B_k,
  }};
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

function coveredRuptureBucket(result) {{
  const rel = result.termBreakdown.relationalFieldState;
  if (!(topology(rel) === "covered" && trajectoryFamily(rel) === "rupture_like")) {{
    return null;
  }}
  if (result.decision === "Hold") {{
    if (Number(rel.hold_tendency) > 0) return "hold_positive";
    if (
      Number(rel.hold_tendency) === 0 &&
      Number(rel.accumulate_tendency) === 0 &&
      Number(rel.avoid_tendency) === 0
    ) {{
      return "hold_zero_basin_fallback";
    }}
    return "hold_other";
  }}
  if (result.decision === "Accumulate") return "accumulate";
  return "avoid";
}}

function inc(map, key, delta = 1) {{
  map[key] = (map[key] || 0) + delta;
}}

async function loadLatestRows() {{
  const rows = [];
  const rl = readline.createInterface({{
    input: fs.createReadStream(latestSnapshotCsv),
    crlfDelay: Infinity,
  }});
  let lineNumber = 0;
  let header = null;
  for await (const line of rl) {{
    lineNumber += 1;
    if (lineNumber === 1) {{
      header = splitCsv(line);
      continue;
    }}
    if (!line) continue;
    const parts = splitCsv(line);
    rows.push(Object.fromEntries(header.map((name, idx) => [name, parts[idx]])));
  }}
  return rows;
}}

async function main() {{
  const latestRows = await loadLatestRows();
  const latestBySymbol = Object.fromEntries(
    latestRows.map((row) => [String(row.symbol).trim().toUpperCase(), row]),
  );
  const latestProfile = {{
    profileId: "unified_field_tensor_latest_snapshot_v3",
    generatedAtUtc: {json.dumps(utc_iso())},
    minBars: 252,
  }};

  const anchorResults = [];
  let matchedExpectedCount = 0;
  for (const [symbol, expectedDecision, note] of anchorCases) {{
    const row = latestBySymbol[symbol] || null;
    const result = mod.computePrimitiveDynamicDecision(row ? toInputFromRow(row) : null, latestProfile);
    const matched = result.decision === expectedDecision;
    if (matched) matchedExpectedCount += 1;
    anchorResults.push({{
      symbol,
      expected_decision: expectedDecision,
      matched_expected: matched,
      note,
      result,
    }});
  }}

  const latestDistribution = {{
    counts: {{}},
    topology_counts: {{}},
    trajectory_family_counts: {{}},
    topology_trajectory_counts: {{}},
  }};
  for (const row of latestRows) {{
    const result = mod.computePrimitiveDynamicDecision(toInputFromRow(row), latestProfile);
    const rel = result.termBreakdown.relationalFieldState;
    const topo = topology(rel);
    const traj = trajectoryFamily(rel);
    inc(latestDistribution.counts, result.decision);
    inc(latestDistribution.topology_counts, topo);
    inc(latestDistribution.trajectory_family_counts, traj);
    inc(latestDistribution.topology_trajectory_counts, `${{topo}}|${{traj}}`);
  }}

  const syntheticSuite = JSON.parse(fs.readFileSync(syntheticSuitePath, "utf8"));
  const syntheticProfile = {{
    profileId: "unified_field_tensor_synthetic_validation_v3",
    generatedAtUtc: {json.dumps(utc_iso())},
    minBars: 252,
  }};
  const seamProbe = {{ count: 0, decision_counts: {{}} }};
  const coveredProbe = {{ count: 0, decision_counts: {{}} }};
  for (const sample of syntheticSuite.samples) {{
    const input = sample.reconstructed_input;
    const result = mod.computePrimitiveDynamicDecision(input, syntheticProfile);
    const rel = result.termBreakdown.relationalFieldState;
    if (sample.stored_trajectory_family === "constructive" && sample.stored_sign_w2 === "pos") {{
      seamProbe.count += 1;
      inc(seamProbe.decision_counts, result.decision);
    }}
    if (topology(rel) === "covered" && trajectoryFamily(rel) === "rupture_like") {{
      coveredProbe.count += 1;
      inc(coveredProbe.decision_counts, result.decision);
    }}
  }}

  const fullProfile = {{
    profileId: "unified_field_tensor_full_fixed_snapshot_v3",
    generatedAtUtc: {json.dumps(utc_iso())},
    minBars: 252,
  }};
  const coveredRupture = {{}};
  const oneSidedContested = {{ total: 0, decision_counts: {{}} }};
  const fullDecisionCounts = {{}};
  const rl = readline.createInterface({{
    input: fs.createReadStream(sourceCsv),
    crlfDelay: Infinity,
  }});
  let lineNumber = 0;
  let header = null;
  for await (const line of rl) {{
    lineNumber += 1;
    if (lineNumber === 1) {{
      header = splitCsv(line);
      continue;
    }}
    if (!line) continue;
    const parts = splitCsv(line);
    const row = Object.fromEntries(header.map((name, idx) => [name, parts[idx]]));
    const result = mod.computePrimitiveDynamicDecision(toInputFromRow(row), fullProfile);
    inc(fullDecisionCounts, result.decision);
    const rel = result.termBreakdown.relationalFieldState;
    const topo = topology(rel);
    const traj = trajectoryFamily(rel);
    const coveredBucket = coveredRuptureBucket(result);
    if (coveredBucket) {{
      inc(coveredRupture, coveredBucket);
    }}
    if (topo === "one_sided" && traj === "contested") {{
      oneSidedContested.total += 1;
      inc(oneSidedContested.decision_counts, result.decision);
    }}
  }}

  const oneSidedAvoid = oneSidedContested.decision_counts.Avoid || 0;
  const summary = {{
    generated_at_utc: {json.dumps(utc_iso())},
    experimental_runtime_path: runtimePath,
    anchors: {{
      matched_expected_count: matchedExpectedCount,
      total_cases: anchorCases.length,
      cases: anchorResults,
    }},
    seam_probe: seamProbe,
    covered_rupture_compare: {{
      counts: coveredRupture,
      full_decision_counts: fullDecisionCounts,
    }},
    latest_snapshot_distribution: latestDistribution,
    one_sided_contested_compare: {{
      total: oneSidedContested.total,
      decision_counts: oneSidedContested.decision_counts,
      avoid_share: oneSidedContested.total ? oneSidedAvoid / oneSidedContested.total : 0,
    }},
  }};

  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2) + "\\n");
}}

main().catch((error) => {{
  console.error(error);
  process.exit(1);
}});
"""

    proc = subprocess.run(
        ["node", "-e", node_script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(
            "unified field tensor v3 validation execution failed\n"
            + "\n".join(proc.stderr.splitlines()[-80:])
        )
    return load_json(summary_path)


def main() -> int:
    started = utc_now()
    stamp = utc_stamp(started)

    source_csv = latest_file("canonical_real_rowtrace_production_fixed_snapshot_", ".csv")
    latest_snapshot_csv = latest_file("canonical_real_snapshot_production_fixed_snapshot_latest_", ".csv")
    synthetic_suite_path = latest_file("canonical_synthetic_suite_production_fixed_snapshot_", ".json")

    with tempfile.TemporaryDirectory(prefix="unified-field-tensor-v3-") as temp_dir:
        summary_path = Path(temp_dir) / "unified-field-summary-v3.json"
        summary = run_node_validation(summary_path, source_csv, latest_snapshot_csv, synthetic_suite_path)

    baseline_synthetic = load_json(BASELINE_SYNTHETIC_VALIDATION)
    baseline_distribution = load_json(BASELINE_FULL_DISTRIBUTION)
    baseline_latest = load_json(BASELINE_LATEST_SNAPSHOT_DECISION)
    baseline_one_sided = load_json(BASELINE_ONE_SIDED_CONTESTED)

    anchor_report = {
        "generated_at_utc": utc_iso(),
        "baseline_artifact": str(BASELINE_SYNTHETIC_VALIDATION),
        "candidate_runtime_path": str(RUNTIME_SOURCE),
        "baseline_matched_expected_count": baseline_synthetic["anchor_pressure_test"]["summary"]["matchedExpectedCount"],
        "candidate_matched_expected_count": summary["anchors"]["matched_expected_count"],
        "total_cases": summary["anchors"]["total_cases"],
        "cases": summary["anchors"]["cases"],
    }

    seam_probe = {
        "generated_at_utc": utc_iso(),
        "baseline_artifact": str(BASELINE_SYNTHETIC_VALIDATION),
        "candidate_runtime_path": str(RUNTIME_SOURCE),
        "baseline": baseline_synthetic["corrected_positive_w2_seam_probe"],
        "candidate": summary["seam_probe"],
    }

    covered_rupture_compare = {
        "generated_at_utc": utc_iso(),
        "baseline_artifact": str(BASELINE_FULL_DISTRIBUTION),
        "candidate_runtime_path": str(RUNTIME_SOURCE),
        "baseline_counts": baseline_distribution["covered_rupture_like_basin_ownership"],
        "candidate_counts": summary["covered_rupture_compare"]["counts"],
        "candidate_full_decision_counts": summary["covered_rupture_compare"]["full_decision_counts"],
    }

    latest_snapshot_distribution = {
        "generated_at_utc": utc_iso(),
        "baseline_artifact": str(BASELINE_LATEST_SNAPSHOT_DECISION),
        "candidate_runtime_path": str(RUNTIME_SOURCE),
        "baseline_counts": baseline_latest["latest_snapshot_decision_distribution"]["counts"],
        "candidate_counts": summary["latest_snapshot_distribution"]["counts"],
        "candidate_topology_counts": summary["latest_snapshot_distribution"]["topology_counts"],
        "candidate_trajectory_family_counts": summary["latest_snapshot_distribution"]["trajectory_family_counts"],
        "candidate_topology_trajectory_counts": summary["latest_snapshot_distribution"]["topology_trajectory_counts"],
    }

    one_sided_contested_compare = {
        "generated_at_utc": utc_iso(),
        "baseline_artifact": str(BASELINE_ONE_SIDED_CONTESTED),
        "candidate_runtime_path": str(RUNTIME_SOURCE),
        "baseline_totals": baseline_one_sided["totals"],
        "baseline_decision_counts": baseline_one_sided["decision_counts"],
        "candidate_total": summary["one_sided_contested_compare"]["total"],
        "candidate_decision_counts": summary["one_sided_contested_compare"]["decision_counts"],
        "candidate_avoid_share": summary["one_sided_contested_compare"]["avoid_share"],
    }

    baseline_anchor = anchor_report["baseline_matched_expected_count"]
    candidate_anchor = anchor_report["candidate_matched_expected_count"]
    baseline_seam = seam_probe["baseline"]["decision_counts"]
    candidate_seam = seam_probe["candidate"]["decision_counts"]
    baseline_covered = covered_rupture_compare["baseline_counts"]
    candidate_covered = covered_rupture_compare["candidate_counts"]
    baseline_latest_counts = latest_snapshot_distribution["baseline_counts"]
    candidate_latest_counts = latest_snapshot_distribution["candidate_counts"]
    baseline_one_sided_avoid_share = baseline_one_sided["totals"]["avoid_share"]
    candidate_one_sided_avoid_share = one_sided_contested_compare["candidate_avoid_share"]

    baseline_seam_hold = baseline_seam.get("Hold", 0)
    candidate_seam_hold = candidate_seam.get("Hold", 0)
    baseline_covered_accumulate = baseline_covered.get("accumulate", 0)
    candidate_covered_accumulate = candidate_covered.get("accumulate", 0)

    verdict_label = "mixed / not ready"
    if (
        candidate_anchor >= baseline_anchor
        and candidate_seam_hold >= baseline_seam_hold
        and candidate_covered_accumulate <= baseline_covered_accumulate * 2
        and candidate_one_sided_avoid_share < baseline_one_sided_avoid_share
    ):
        verdict_label = "better than baseline"
    elif (
        candidate_anchor < baseline_anchor
        or candidate_seam_hold == 0
        or candidate_covered_accumulate > baseline_covered_accumulate * 4
    ):
        verdict_label = "worse than baseline"

    forced_conclusion = "unified-field tensor candidate improves some surfaces but is not yet safer than baseline"
    if verdict_label == "better than baseline":
        forced_conclusion = "unified-field tensor candidate dominates baseline"
    elif verdict_label == "worse than baseline":
        forced_conclusion = "unified-field tensor candidate fails and should not replace baseline"

    verdict = {
        "generated_at_utc": utc_iso(),
        "candidate_runtime_path": str(RUNTIME_SOURCE),
        "candidate_runtime_sha256": sha256_file(RUNTIME_SOURCE),
        "baseline_runtime_path": str(REPO_ROOT / "web" / "src" / "lib" / "uf-dynamic-decision.ts"),
        "baseline_reference_artifacts": {
            "synthetic_validation": str(BASELINE_SYNTHETIC_VALIDATION),
            "full_distribution": str(BASELINE_FULL_DISTRIBUTION),
            "latest_snapshot_decision": str(BASELINE_LATEST_SNAPSHOT_DECISION),
            "one_sided_contested_audit": str(BASELINE_ONE_SIDED_CONTESTED),
        },
        "anchor comparison versus current baseline": {
            "baseline_matched_expected_count": baseline_anchor,
            "candidate_matched_expected_count": candidate_anchor,
            "total_cases": summary["anchors"]["total_cases"],
        },
        "seam behavior versus current baseline": {
            "baseline": baseline_seam,
            "candidate": candidate_seam,
            "baseline_hold": baseline_seam_hold,
            "candidate_hold": candidate_seam_hold,
        },
        "covered-rupture ownership versus current baseline": {
            "baseline": baseline_covered,
            "candidate": candidate_covered,
            "baseline_accumulate": baseline_covered_accumulate,
            "candidate_accumulate": candidate_covered_accumulate,
        },
        "latest fixed-snapshot decision distribution versus current baseline": {
            "baseline": baseline_latest_counts,
            "candidate": candidate_latest_counts,
        },
        "one-sided contested boundary versus current baseline": {
            "baseline_avoid_share": baseline_one_sided_avoid_share,
            "candidate_avoid_share": candidate_one_sided_avoid_share,
            "baseline_decision_counts": baseline_one_sided["decision_counts"],
            "candidate_decision_counts": one_sided_contested_compare["candidate_decision_counts"],
        },
        "required verdict question": (
            "does indefiniteness-aware extraction preserve the tensor idea while restoring seam Hold "
            "where appropriate, preventing covered-rupture Accumulate explosion, and keeping one-sided "
            "contested Avoid lower than baseline without redefining the whole surface?"
        ),
        "explicit statement": verdict_label,
        "forced_conclusion": forced_conclusion,
    }

    verdict_md = f"""
# Unified-Field Tensor V3 Verdict

## Anchor Comparison Versus Current Baseline
- baseline matched anchors: `{baseline_anchor} / {summary["anchors"]["total_cases"]}`
- candidate matched anchors: `{candidate_anchor} / {summary["anchors"]["total_cases"]}`

## Seam Behavior Versus Current Baseline
- baseline seam counts: `{baseline_seam}`
- candidate seam counts: `{candidate_seam}`

## Covered-Rupture Ownership Versus Current Baseline
- baseline covered-rupture counts: `{baseline_covered}`
- candidate covered-rupture counts: `{candidate_covered}`

## Latest Fixed-Snapshot Decision Distribution Versus Current Baseline
- baseline latest counts: `{baseline_latest_counts}`
- candidate latest counts: `{candidate_latest_counts}`

## One-Sided Contested Boundary Versus Current Baseline
- baseline avoid share: `{baseline_one_sided_avoid_share}`
- candidate avoid share: `{candidate_one_sided_avoid_share}`
- baseline decision counts: `{baseline_one_sided["decision_counts"]}`
- candidate decision counts: `{one_sided_contested_compare["candidate_decision_counts"]}`

## Required Verdict Question
- does indefiniteness-aware extraction preserve the tensor idea while restoring seam Hold where appropriate, preventing covered-rupture Accumulate explosion, and keeping one-sided contested Avoid lower than baseline without redefining the whole surface?
- answer: `{forced_conclusion}`

## Explicit Statement
- `{verdict_label}`
""".strip()

    anchor_path = BACKUPS / f"dsf_primitive_unified_field_tensor_v3_anchor_report_{stamp}.json"
    seam_path = BACKUPS / f"dsf_primitive_unified_field_tensor_v3_seam_probe_{stamp}.json"
    covered_path = BACKUPS / f"dsf_primitive_unified_field_tensor_v3_covered_rupture_compare_{stamp}.json"
    latest_path = BACKUPS / f"dsf_primitive_unified_field_tensor_v3_latest_snapshot_distribution_{stamp}.json"
    one_sided_path = BACKUPS / f"dsf_primitive_unified_field_tensor_v3_one_sided_contested_compare_{stamp}.json"
    verdict_path = BACKUPS / f"dsf_primitive_unified_field_tensor_v3_verdict_{stamp}.json"
    verdict_md_path = BACKUPS / f"dsf_primitive_unified_field_tensor_v3_verdict_{stamp}.md"

    write_json(anchor_path, anchor_report)
    write_json(seam_path, seam_probe)
    write_json(covered_path, covered_rupture_compare)
    write_json(latest_path, latest_snapshot_distribution)
    write_json(one_sided_path, one_sided_contested_compare)
    write_json(verdict_path, verdict)
    write_markdown(verdict_md_path, verdict_md)

    print(
        json.dumps(
            {
                "anchor_report": str(anchor_path),
                "seam_probe": str(seam_path),
                "covered_rupture_compare": str(covered_path),
                "latest_snapshot_distribution": str(latest_path),
                "one_sided_contested_compare": str(one_sided_path),
                "verdict_json": str(verdict_path),
                "verdict_md": str(verdict_md_path),
                "forced_conclusion": forced_conclusion,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
