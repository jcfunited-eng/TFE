import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import Module from "node:module";

import ts from "typescript";

const ROOT = "/workspaces/Tao_Financial_Engine";
const RUNTIME_DIR = path.join(ROOT, "backups", "runtime");

function utcStamp() {
  const now = new Date();
  const y = now.getUTCFullYear();
  const m = String(now.getUTCMonth() + 1).padStart(2, "0");
  const d = String(now.getUTCDate()).padStart(2, "0");
  const hh = String(now.getUTCHours()).padStart(2, "0");
  const mm = String(now.getUTCMinutes()).padStart(2, "0");
  const ss = String(now.getUTCSeconds()).padStart(2, "0");
  return `${y}${m}${d}T${hh}${mm}${ss}Z`;
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function loadSnapshotRows() {
  const candidates = [
    path.join(ROOT, "uf_snapshot.json"),
    path.join(ROOT, "uf_snapshot.dev_current_eval.json"),
    path.join(ROOT, "uf_snapshot.dev_live12.json"),
  ];

  for (const candidate of candidates) {
    if (!fs.existsSync(candidate)) continue;
    const raw = JSON.parse(fs.readFileSync(candidate, "utf8"));
    const rows = Array.isArray(raw) ? raw : Array.isArray(raw?.rows) ? raw.rows : [];
    if (rows.length > 0) {
      return { rows, sourcePath: candidate };
    }
  }

  throw new Error("No usable snapshot rows found for oracle evaluation.");
}

function transpilePressureModule() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "uf-dynamic-oracle-"));

  const decisionSrcPath = path.join(ROOT, "web", "src", "lib", "uf-dynamic-decision.ts");
  const pressureSrcPath = path.join(ROOT, "web", "src", "lib", "uf-dynamic-decision-pressure-test.ts");

  const decisionOutPath = path.join(tempDir, "uf-dynamic-decision.cjs");
  const pressureOutPath = path.join(tempDir, "uf-dynamic-decision-pressure-test.cjs");

  const decisionSource = fs.readFileSync(decisionSrcPath, "utf8");
  let pressureSource = fs.readFileSync(pressureSrcPath, "utf8");
  pressureSource = pressureSource.replace("@/lib/uf-dynamic-decision", "./uf-dynamic-decision.cjs");

  const compilerOptions = {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  };

  const transpiledDecision = ts.transpileModule(decisionSource, { compilerOptions });
  const transpiledPressure = ts.transpileModule(pressureSource, { compilerOptions });

  fs.writeFileSync(decisionOutPath, transpiledDecision.outputText);
  fs.writeFileSync(pressureOutPath, transpiledPressure.outputText);

  const localRequire = Module.createRequire(import.meta.url);
  return localRequire(pressureOutPath);
}

function clip(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function centeredUnit(value) {
  return clip(2 * value - 1, -1, 1);
}

function normalizedSigned(value, scale) {
  return clip(value / scale, -1, 1);
}

function median(values) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[mid];
  return (sorted[mid - 1] + sorted[mid]) / 2;
}

function quantile(values, q) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = (sorted.length - 1) * q;
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  const weight = idx - lo;
  return sorted[lo] * (1 - weight) + sorted[hi] * weight;
}

function normalizeInput(input, profile) {
  return {
    D_k: clip(Number(input.D_k ?? 0), -1, 1),
    M_k: clip(Number(input.M_k ?? 0), -1, 1),
    R_UF_centered: centeredUnit(Number(input.R_UF ?? 0)),
    S_UF_centered: centeredUnit(Number(input.S_UF ?? 0)),
    stability_centered: centeredUnit(Number(input.stabilityScore ?? 0)),
    B_k: clip(Number(input.B_k ?? 0), -1, 1),
    U_star_k: clip(Number(input.U_star_k ?? 0), 0, 1),
    R_rev_k: clip(Number(input.R_rev_k ?? 0), 0, 1),
    C_k_normalized: normalizedSigned(Number(input.C_k ?? 0), profile.thresholds.cScale),
    P_k_normalized: normalizedSigned(Number(input.P_k ?? 0), profile.thresholds.pScale),
  };
}

function calculateCandidates(n) {
  const supportField =
    0.25 +
    n.S_UF_centered +
    0.7 * n.R_UF_centered +
    0.65 * n.M_k +
    0.35 * n.B_k;

  const destabilizationField =
    0.5 * n.U_star_k +
    0.9 * n.R_rev_k +
    0.35 * Math.max(0, n.P_k_normalized) +
    0.2 * Math.max(0, n.C_k_normalized) +
    0.05 * Math.max(0, -n.stability_centered);

  const directionalSupport = n.D_k * supportField;
  const netDirectionalContinuation = directionalSupport - destabilizationField;
  const neutralDrift = supportField - destabilizationField;
  const continuationDominance = supportField / Math.max(0.25, destabilizationField);

  return {
    support_field_v1: supportField,
    destabilization_field_v1: destabilizationField,
    directional_support_v1: directionalSupport,
    net_directional_continuation_v1: netDirectionalContinuation,
    neutral_drift_v1: neutralDrift,
    continuation_dominance_v1: continuationDominance,
  };
}

function evaluateCandidate(anchorRows, candidateName) {
  const groups = {
    Accumulate: [],
    Hold: [],
    Avoid: [],
  };

  for (const row of anchorRows) {
    groups[row.expectedDecision].push(row.candidates[candidateName]);
  }

  const medians = {
    Accumulate: median(groups.Accumulate),
    Hold: median(groups.Hold),
    Avoid: median(groups.Avoid),
  };

  const highGoodMinGap = Math.min(
    medians.Accumulate - medians.Hold,
    medians.Hold - medians.Avoid,
  );
  const lowGoodMinGap = Math.min(
    medians.Avoid - medians.Hold,
    medians.Hold - medians.Accumulate,
  );

  const highGoodSumGap =
    (medians.Accumulate - medians.Hold) + (medians.Hold - medians.Avoid);
  const lowGoodSumGap =
    (medians.Avoid - medians.Hold) + (medians.Hold - medians.Accumulate);

  if (highGoodMinGap >= lowGoodMinGap) {
    return {
      preferredOrientation: "higher_is_more_accumulate_like",
      separationScore: highGoodMinGap,
      totalSpread: highGoodSumGap,
      medians,
    };
  }

  return {
    preferredOrientation: "lower_is_more_accumulate_like",
    separationScore: lowGoodMinGap,
    totalSpread: lowGoodSumGap,
    medians,
  };
}

function summarizeBroad(rows, candidateName) {
  const values = rows.map((row) => row.candidates[candidateName]);
  return {
    q05: quantile(values, 0.05),
    q25: quantile(values, 0.25),
    q50: quantile(values, 0.5),
    q75: quantile(values, 0.75),
    q95: quantile(values, 0.95),
  };
}

function main() {
  ensureDir(RUNTIME_DIR);

  const snapshot = loadSnapshotRows();
  const pressureModule = transpilePressureModule();
  const profile = pressureModule.PRESSURE_TEST_PROFILE_EXAMPLE_V1;

  const anchors = [
    ["AGO", "Accumulate"],
    ["TXRH", "Accumulate"],
    ["DHI", "Accumulate"],
    ["AAT", "Hold"],
    ["ACGL", "Hold"],
    ["ADC", "Hold"],
    ["AA", "Avoid"],
    ["AAPL", "Avoid"],
    ["ACLS", "Avoid"],
  ];

  const anchorRows = anchors.map(([symbol, expectedDecision]) => {
    const input = pressureModule.pressureTestCaseFromRows(
      snapshot.rows,
      symbol,
      expectedDecision,
      "oracle_eval_anchor",
    ).input;
    const normalized = normalizeInput(input, profile);
    return {
      symbol,
      expectedDecision,
      normalized,
      candidates: calculateCandidates(normalized),
    };
  });

  const broadRows = [];
  for (const row of snapshot.rows) {
    const symbol = String(row.ticker ?? "").trim().toUpperCase();
    const input = pressureModule.dynamicDecisionInputFromRow(row, symbol);
    if (!input) continue;
    if (input.barCount < profile.thresholds.minBars) continue;
    const required = [
      input.S_UF,
      input.R_UF,
      input.stabilityScore,
      input.D_k,
      input.M_k,
      input.R_rev_k,
      input.U_star_k,
      input.C_k,
      input.P_k,
      input.B_k,
    ];
    if (required.some((value) => value === null || Number.isNaN(Number(value)))) continue;

    const normalized = normalizeInput(input, profile);
    broadRows.push({
      symbol,
      regime: input.regime,
      normalized,
      candidates: calculateCandidates(normalized),
    });
  }

  const candidateNames = Object.keys(anchorRows[0].candidates);
  const candidateEvaluations = {};
  for (const candidateName of candidateNames) {
    candidateEvaluations[candidateName] = {
      anchorEvaluation: evaluateCandidate(anchorRows, candidateName),
      broadQuantiles: summarizeBroad(broadRows, candidateName),
    };
  }

  const rankedCandidates = candidateNames
    .map((candidateName) => ({
      candidateName,
      separationScore: candidateEvaluations[candidateName].anchorEvaluation.separationScore,
      totalSpread: candidateEvaluations[candidateName].anchorEvaluation.totalSpread,
    }))
    .sort((a, b) => {
      if (b.separationScore !== a.separationScore) {
        return b.separationScore - a.separationScore;
      }
      return b.totalSpread - a.totalSpread;
    });

  const outPath = path.join(
    RUNTIME_DIR,
    `uf_dynamic_decision_oracle_eval_${utcStamp()}.json`,
  );

  const report = {
    generated_at_utc: new Date().toISOString(),
    snapshot_source_path: snapshot.sourcePath,
    method: {
      type: "offline_dynamic_field_property_oracle_eval",
      note: "Offline reduced-approximation comparison of candidate field-property calculations. This is not runtime architecture.",
      anchor_symbols: anchors,
    },
    broad_sample_size: broadRows.length,
    ranked_candidates: rankedCandidates,
    candidate_evaluations: candidateEvaluations,
    anchor_values: anchorRows,
  };

  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ report_path: outPath, ranked_candidates: rankedCandidates }, null, 2));
}

main();
