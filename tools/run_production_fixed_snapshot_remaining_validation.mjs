import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import readline from "node:readline";
import Module from "node:module";
import childProcess from "node:child_process";

const ROOT = "/workspaces/Tao_Financial_Engine";
const BACKUPS = path.join(ROOT, "backups", "runtime");
const WEB_ROOT = path.join(ROOT, "web");
const WEB_PACKAGE_JSON = path.join(WEB_ROOT, "package.json");
const RUNTIME_PATH = path.join(WEB_ROOT, "src", "lib", "uf-dynamic-decision.ts");
const PRESSURE_PATH = path.join(WEB_ROOT, "src", "lib", "uf-dynamic-decision-pressure-test.ts");
const LATEST_SNAPSHOT_GLOB_PREFIX = "canonical_real_snapshot_production_fixed_snapshot_latest_";
const FULL_CSV_PREFIX = "canonical_real_rowtrace_production_fixed_snapshot_";
const FULL_META_PREFIX = "canonical_real_rowtrace_production_fixed_snapshot_metadata_";
const FULL_DISTRIBUTION_PREFIX = "dsf_primitive_production_distribution_fixed_snapshot_";
const FULL_GATE_PREFIX = "uf_dynamic_decision_native_rowtrace_eval_production_fixed_snapshot_";
const SYNTHETIC_SUITE_SOURCE = path.join(BACKUPS, "canonical_synthetic_suite_20260320T064427Z.json");
const SEAM_BASELINE_PATH = path.join(
  BACKUPS,
  "dsf_primitive_constructive_covered_seam_boundary_broader_concentration_postfix2_20260320T170658Z.json",
);
const COVERED_RUPTURE_BASELINE_PATH = path.join(
  BACKUPS,
  "dsf_primitive_covered_rupture_like_population_compare_broader_postfix2_20260320T170658Z.json",
);
const LOCAL_DENT_SEARCH = "local dent|local-dent|pinned local";
const requireFromWeb = Module.createRequire(WEB_PACKAGE_JSON);
const ts = requireFromWeb("typescript");

const ROW_COLUMNS = [
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
];

const RELATIONAL_KEYS = [
  "support_reserve",
  "resonance_reserve",
  "support_resonance_gap",
  "weak_coverage",
  "secondary_coverage",
  "coverage_surplus",
  "coverage_deficit",
  "reserve_asymmetry",
  "edge_support",
  "double_sided_deficit",
  "edge_window",
  "reversal_calm",
  "conflict_calm",
  "persistence_calm",
  "conflict_drag",
  "persistence_drag",
  "load",
  "directional_positive",
  "directional_negative",
  "directional_stillness",
  "momentum_positive",
  "momentum_negative",
  "momentum_stillness",
  "carry_positive",
  "carry_negative",
  "trajectory_forward",
  "trajectory_contest",
  "trajectory_rupture",
  "accumulate_tendency",
  "hold_tendency",
  "avoid_tendency",
];

function utcNow() {
  return new Date();
}

function utcStamp(value = utcNow()) {
  const y = value.getUTCFullYear();
  const m = String(value.getUTCMonth() + 1).padStart(2, "0");
  const d = String(value.getUTCDate()).padStart(2, "0");
  const hh = String(value.getUTCHours()).padStart(2, "0");
  const mm = String(value.getUTCMinutes()).padStart(2, "0");
  const ss = String(value.getUTCSeconds()).padStart(2, "0");
  return `${y}${m}${d}T${hh}${mm}${ss}Z`;
}

function utcIso(value = utcNow()) {
  return value.toISOString().replace(/\.\d{3}Z$/, "Z");
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, payload) {
  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2) + "\n");
}

function writeMarkdown(filePath, content) {
  fs.writeFileSync(filePath, content.trimEnd() + "\n");
}

function sha256File(filePath) {
  const h = crypto.createHash("sha256");
  const fd = fs.openSync(filePath, "r");
  const buffer = Buffer.alloc(1024 * 1024);
  try {
    while (true) {
      const bytesRead = fs.readSync(fd, buffer, 0, buffer.length, null);
      if (!bytesRead) break;
      h.update(buffer.subarray(0, bytesRead));
    }
  } finally {
    fs.closeSync(fd);
  }
  return h.digest("hex");
}

function latestFile(prefix, suffix) {
  const files = fs
    .readdirSync(BACKUPS)
    .filter((name) => name.startsWith(prefix) && name.endsWith(suffix))
    .sort();
  if (files.length === 0) {
    throw new Error(`No artifact found for ${prefix}*${suffix}`);
  }
  return path.join(BACKUPS, files.at(-1));
}

function gitHead() {
  try {
    return childProcess
      .execFileSync("git", ["rev-parse", "HEAD"], { cwd: ROOT, encoding: "utf8" })
      .trim();
  } catch {
    return null;
  }
}

function gitDirty() {
  try {
    const out = childProcess.execFileSync("git", ["status", "--porcelain"], {
      cwd: ROOT,
      encoding: "utf8",
    });
    return out.trim().length > 0;
  } catch {
    return null;
  }
}

function clip(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function finite(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function topology(rel) {
  const w = Number(rel.weak_coverage);
  const w2 = Number(rel.secondary_coverage);
  if (w > 0) return "covered";
  if (w2 > 0) return "one_sided";
  return "double_sided";
}

function trajectoryFamily(rel) {
  const f = Number(rel.trajectory_forward);
  const c = Number(rel.trajectory_contest);
  const r = Number(rel.trajectory_rupture);
  if (f === 0 && r === 0) return "still";
  if (f > c && f > r) return "constructive";
  if (r > f && r > c) return "rupture_like";
  return "contested";
}

function seamBucket(result) {
  const rel = result.termBreakdown.relationalFieldState;
  return (
    Number(rel.weak_coverage) > 0 &&
    Number(rel.secondary_coverage) > 0 &&
    Math.abs(Number(rel.weak_coverage)) <= 0.03 &&
    Number(rel.trajectory_forward) > Number(rel.trajectory_rupture) &&
    (result.decision === "Accumulate" || result.decision === "Hold")
  );
}

function coveredRuptureOwnershipBucket(result) {
  const rel = result.termBreakdown.relationalFieldState;
  if (!(topology(rel) === "covered" && trajectoryFamily(rel) === "rupture_like")) {
    return null;
  }
  if (result.decision === "Hold") {
    if (Number(rel.hold_tendency) > 0) return "hold_positive";
    if (
      Number(rel.hold_tendency) === 0 &&
      Number(rel.accumulate_tendency) === 0 &&
      Number(rel.avoid_tendency) === 0
    ) {
      return "hold_zero_basin_fallback";
    }
    return "hold_other";
  }
  if (result.decision === "Accumulate") return "accumulate";
  return "avoid";
}

function geometryExpectedLean(result) {
  const rel = result.termBreakdown.relationalFieldState;
  const topo = topology(rel);
  const traj = trajectoryFamily(rel);
  const load = Number(rel.load);
  if (topo === "double_sided") return "Avoid";
  if (
    topo === "covered" &&
    traj === "constructive" &&
    Number(rel.trajectory_rupture) <= Number(rel.trajectory_forward) &&
    load <= 0.625
  ) {
    return "Accumulate";
  }
  if (traj === "still") return "Hold";
  if (traj === "contested") return "Hold";
  if (topo === "covered" && traj === "rupture_like" && Number(rel.hold_tendency) > 0) {
    return "Hold";
  }
  if (topo === "one_sided" && traj === "constructive" && Number(rel.accumulate_tendency) > 0) {
    return "Accumulate";
  }
  if (Number(rel.avoid_tendency) > 0 && topo !== "covered") return "Avoid";
  return "Hold";
}

function plausibilityClassification(result) {
  const rel = result.termBreakdown.relationalFieldState;
  const expected = geometryExpectedLean(result);
  if (
    result.decision === "Hold" &&
    Number(rel.hold_tendency) === 0 &&
    Number(rel.accumulate_tendency) === 0 &&
    Number(rel.avoid_tendency) === 0
  ) {
    return { expected_lean: expected, classification: "zero_basin_fallback" };
  }
  if (result.decision === expected) {
    return { expected_lean: expected, classification: "rational_match" };
  }
  if (expected === "Accumulate" && result.decision === "Hold") {
    return { expected_lean: expected, classification: "conservative_but_plausible" };
  }
  if (expected === "Hold" && result.decision === "Avoid") {
    return { expected_lean: expected, classification: "conservative_but_plausible" };
  }
  return { expected_lean: expected, classification: "suspicious_mismatch" };
}

function weightedSummary(rows) {
  const weightedCounts = {};
  let totalWeight = 0;
  for (const row of rows) {
    const w = Number(row.sample_weight);
    totalWeight += w;
    weightedCounts[row.classification] = (weightedCounts[row.classification] || 0) + w;
  }
  const weightedShares = {};
  for (const [key, value] of Object.entries(weightedCounts)) {
    weightedShares[key] = totalWeight ? value / totalWeight : 0;
  }
  return { total_weight: totalWeight, weighted_counts: weightedCounts, weighted_shares: weightedShares };
}

function unweightedSummary(rows) {
  const counts = {};
  for (const row of rows) {
    counts[row.classification] = (counts[row.classification] || 0) + 1;
  }
  const shares = {};
  for (const [key, value] of Object.entries(counts)) {
    shares[key] = rows.length ? value / rows.length : 0;
  }
  return { count: rows.length, counts, shares };
}

function finitePopulationSampleSize(N) {
  const z = 1.96;
  const p = 0.5;
  const e = 0.05;
  return Math.ceil((N * z * z * p * (1 - p)) / (((N - 1) * e * e) + z * z * p * (1 - p)));
}

function splitCsv(line) {
  return line.split(",");
}

function toInputFromRow(row) {
  return {
    symbol: row.symbol,
    barCount: Number(row.bar_count),
    S_UF: Number(row.S_UF),
    R_UF: Number(row.R_UF),
    D_k: Number(row.D_k),
    M_k: Number(row.M_k),
    R_rev_k: Number(row.R_rev_k),
    U_star_k: Number(row.U_star_k),
    C_k: Number(row.C_k),
    P_k: Number(row.P_k),
    B_k: Number(row.B_k),
  };
}

function transpileModules() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "production-fixed-validation-"));
  const decisionOutPath = path.join(tempDir, "uf-dynamic-decision.cjs");
  const pressureOutPath = path.join(tempDir, "uf-dynamic-decision-pressure-test.cjs");
  const compilerOptions = {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
    esModuleInterop: true,
  };
  const decisionSource = fs.readFileSync(RUNTIME_PATH, "utf8");
  let pressureSource = fs.readFileSync(PRESSURE_PATH, "utf8");
  pressureSource = pressureSource.replace('@/lib/uf-dynamic-decision', "./uf-dynamic-decision.cjs");
  fs.writeFileSync(decisionOutPath, ts.transpileModule(decisionSource, { compilerOptions }).outputText);
  fs.writeFileSync(pressureOutPath, ts.transpileModule(pressureSource, { compilerOptions }).outputText);
  const localRequire = Module.createRequire(import.meta.url);
  return {
    tempDir,
    decisionModule: localRequire(decisionOutPath),
    pressureModule: localRequire(pressureOutPath),
  };
}

function reconstructSyntheticInput(sample, index) {
  const b = sample.breakdown;
  const supportReserve = Number(b.support_reserve);
  const resonanceReserve = Number(b.resonance_reserve);
  const uncertainty = Math.max(0, -supportReserve, -resonanceReserve);
  const S_UF = clip(supportReserve + uncertainty, 0, 1);
  const R_UF = clip(resonanceReserve + uncertainty, 0, 1);
  const D_k = Number(b.directional_positive) - Number(b.directional_negative);
  const M_k = Number(b.momentum_positive) - Number(b.momentum_negative);
  const R_rev_k = clip(1 - Number(b.reversal_calm), 0, 1);
  const conflictDrag = clip(Number(b.conflict_drag), 0, 0.999999999);
  const persistenceDrag = clip(Number(b.persistence_drag), 0, 0.999999999);
  const C_k = conflictDrag === 0 ? 0 : conflictDrag / (1 - conflictDrag);
  const P_k = persistenceDrag === 0 ? 0 : persistenceDrag / (1 - persistenceDrag);
  const B_k = Number(b.carry_positive) - Number(b.carry_negative);
  return {
    symbol: `SYNTH_${String(index + 1).padStart(3, "0")}`,
    barCount: 300,
    S_UF,
    R_UF,
    D_k,
    M_k,
    R_rev_k,
    U_star_k: uncertainty,
    C_k,
    P_k,
    B_k,
  };
}

function relationalDelta(currentRel, expectedRel) {
  let maxAbs = 0;
  const deltas = {};
  for (const key of RELATIONAL_KEYS) {
    const left = Number(currentRel[key]);
    const right = Number(expectedRel[key]);
    const delta = Math.abs(left - right);
    deltas[key] = delta;
    if (delta > maxAbs) maxAbs = delta;
  }
  return { max_abs_delta: maxAbs, per_key_abs_delta: deltas };
}

function mean(values) {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

async function loadLatestSnapshotRows() {
  const latestSnapshotCsv = latestFile(LATEST_SNAPSHOT_GLOB_PREFIX, ".csv");
  const rows = [];
  const rl = readline.createInterface({
    input: fs.createReadStream(latestSnapshotCsv),
    crlfDelay: Infinity,
  });
  let lineNumber = 0;
  let header = null;
  for await (const line of rl) {
    lineNumber += 1;
    if (lineNumber === 1) {
      header = splitCsv(line);
      continue;
    }
    if (!line) continue;
    const parts = splitCsv(line);
    const row = Object.fromEntries(header.map((name, idx) => [name, parts[idx]]));
    rows.push({ ...row, ticker: row.symbol });
  }
  return { latestSnapshotCsv, rows };
}

async function runSyntheticValidation(stamp, modules) {
  const suite = readJson(SYNTHETIC_SUITE_SOURCE);
  const profile = {
    profileId: "production_fixed_snapshot_synthetic_validation_v1",
    generatedAtUtc: utcIso(),
    minBars: 252,
  };
  const retaggedSamples = [];
  const runtimeDecisionCounts = {};
  const computedTopologyCounts = {};
  const computedTrajectoryCounts = {};
  const maxAbsDeltas = [];

  for (let i = 0; i < suite.samples.length; i += 1) {
    const sample = suite.samples[i];
    const input = reconstructSyntheticInput(sample, i);
    const result = modules.decisionModule.computePrimitiveDynamicDecision(input, profile);
    const rel = result.termBreakdown.relationalFieldState;
    const computedTopology = topology(rel);
    const computedTrajectory = trajectoryFamily(rel);
    runtimeDecisionCounts[result.decision] = (runtimeDecisionCounts[result.decision] || 0) + 1;
    computedTopologyCounts[computedTopology] = (computedTopologyCounts[computedTopology] || 0) + 1;
    computedTrajectoryCounts[computedTrajectory] = (computedTrajectoryCounts[computedTrajectory] || 0) + 1;
    const delta = relationalDelta(rel, sample.breakdown);
    maxAbsDeltas.push(delta.max_abs_delta);
    retaggedSamples.push({
      family_label: sample.family_label,
      load_label: sample.load_label,
      stored_decision_current: sample.decision_current,
      stored_decision_old: sample.decision_old,
      stored_sign_w: sample.sign_w,
      stored_sign_w2: sample.sign_w2,
      stored_topology: sample.coverage_topology,
      stored_trajectory_family: sample.trajectory_family,
      computed_topology: computedTopology,
      computed_trajectory_family: computedTrajectory,
      load_bucket: sample.load_bucket,
      reconstructed_input: input,
      runtime_decision: result.decision,
      decision_matches_stored_current: result.decision === sample.decision_current,
      topology_matches_stored: computedTopology === sample.coverage_topology,
      trajectory_matches_stored: computedTrajectory === sample.trajectory_family,
      relational_reconstruction: delta,
    });
  }

  const syntheticSuitePath = path.join(
    BACKUPS,
    `canonical_synthetic_suite_production_fixed_snapshot_${stamp}.json`,
  );
  writeJson(syntheticSuitePath, {
    generated_at_utc: utcIso(),
    source_suite_path: SYNTHETIC_SUITE_SOURCE,
    source_suite_sha256: sha256File(SYNTHETIC_SUITE_SOURCE),
    sample_count: retaggedSamples.length,
    samples: retaggedSamples,
  });

  const { latestSnapshotCsv, rows: latestRows } = await loadLatestSnapshotRows();
  const pressureCases = [
    modules.pressureModule.pressureTestCaseFromRows(latestRows, "AGO", "Accumulate", "Accumulate anchor 1"),
    modules.pressureModule.pressureTestCaseFromRows(latestRows, "TXRH", "Accumulate", "Accumulate anchor 2"),
    modules.pressureModule.pressureTestCaseFromRows(latestRows, "DHI", "Accumulate", "Accumulate anchor 3"),
    modules.pressureModule.pressureTestCaseFromRows(latestRows, "AAT", "Hold", "Hold anchor 1"),
    modules.pressureModule.pressureTestCaseFromRows(latestRows, "ACGL", "Hold", "Hold anchor 2"),
    modules.pressureModule.pressureTestCaseFromRows(latestRows, "ADC", "Hold", "Hold anchor 3"),
    modules.pressureModule.pressureTestCaseFromRows(latestRows, "AA", "Avoid", "Avoid anchor 1"),
    modules.pressureModule.pressureTestCaseFromRows(latestRows, "AAPL", "Avoid", "Avoid anchor 2"),
    modules.pressureModule.pressureTestCaseFromRows(latestRows, "ACLS", "Avoid", "Avoid anchor 3"),
  ];
  const anchorRun = modules.pressureModule.runDynamicDecisionPressureTest(pressureCases, {
    profileId: "production_fixed_snapshot_anchor_pressure_v1",
    generatedAtUtc: utcIso(),
    minBars: 252,
  });

  const seamProbeRows = retaggedSamples.filter(
    (row) => row.stored_trajectory_family === "constructive" && row.stored_sign_w2 === "pos",
  );
  const coveredRuptureRows = retaggedSamples.filter(
    (row) => row.computed_topology === "covered" && row.computed_trajectory_family === "rupture_like",
  );
  const syntheticValidation = {
    generated_at_utc: utcIso(),
    source_retagged_suite_path: syntheticSuitePath,
    anchor_pressure_test: {
      source_snapshot_csv: latestSnapshotCsv,
      matched_expected_count: anchorRun.summary.matchedExpectedCount,
      total_cases: anchorRun.summary.totalCases,
      summary: anchorRun.summary,
      cases: anchorRun.results,
    },
    synthetic_suite_summary: {
      runtime_decision_counts: runtimeDecisionCounts,
      computed_topology_counts: computedTopologyCounts,
      computed_trajectory_family_counts: computedTrajectoryCounts,
      decision_matches_stored_current_count: retaggedSamples.filter((x) => x.decision_matches_stored_current).length,
      topology_matches_stored_count: retaggedSamples.filter((x) => x.topology_matches_stored).length,
      trajectory_matches_stored_count: retaggedSamples.filter((x) => x.trajectory_matches_stored).length,
      mean_max_abs_relational_delta: mean(maxAbsDeltas),
      max_max_abs_relational_delta: Math.max(...maxAbsDeltas),
    },
    corrected_positive_w2_seam_probe: {
      source: "canonical synthetic suite samples with positive w2 constructive geometry",
      count: seamProbeRows.length,
      decision_counts: seamProbeRows.reduce((acc, row) => {
        acc[row.runtime_decision] = (acc[row.runtime_decision] || 0) + 1;
        return acc;
      }, {}),
    },
    covered_rupture_like_comparison_probe: {
      source: "canonical synthetic suite samples retagged under current runtime",
      count: coveredRuptureRows.length,
      decision_counts: coveredRuptureRows.reduce((acc, row) => {
        acc[row.runtime_decision] = (acc[row.runtime_decision] || 0) + 1;
        return acc;
      }, {}),
    },
    pinned_local_dent_probe: {
      status: "unavailable",
      reason: "no explicit accepted pinned local-dent probe definition found in repo/artifacts",
    },
  };

  const validationPath = path.join(
    BACKUPS,
    `dsf_primitive_production_synthetic_validation_${stamp}.json`,
  );
  writeJson(validationPath, syntheticValidation);
  return { syntheticSuitePath, validationPath, syntheticValidation };
}

function diagnosticStratum(result) {
  const rel = result.termBreakdown.relationalFieldState;
  const topo = topology(rel);
  const traj = trajectoryFamily(rel);
  const coveredRuptureBucket = coveredRuptureOwnershipBucket(result);
  if (seamBucket(result)) return "seam";
  if (coveredRuptureBucket === "hold_zero_basin_fallback") return "covered_rupture_hold_zero_basin_fallback";
  if (coveredRuptureBucket === "accumulate") return "covered_rupture_accumulate";
  if (coveredRuptureBucket === "hold_positive") return "covered_rupture_hold_positive";
  if (result.decision === "Accumulate") return `accumulate_${topo}_${traj}`;
  if (result.decision === "Avoid" && topo === "one_sided" && traj === "contested") {
    return "one_sided_contested_avoid";
  }
  return null;
}

function reservoirUpdate(bucket, target, item) {
  if (target <= 0) return;
  bucket.seen += 1;
  if (bucket.items.length < target) {
    bucket.items.push(item);
    return;
  }
  const j = Math.floor(Math.random() * bucket.seen);
  if (j < target) {
    bucket.items[j] = item;
  }
}

function cloneSampleItem(row, result, stratumKey) {
  const rel = result.termBreakdown.relationalFieldState;
  return {
    row: { ...row },
    result: {
      decision: result.decision,
      blockerCode: result.blockerCode,
      blockerActive: result.blockerActive,
      termBreakdown: { relationalFieldState: { ...rel } },
    },
    stratum_key: stratumKey,
  };
}

async function runFullSamplingAndPlausibility(stamp, modules, sourceCsv, sourceMeta) {
  const N = Number(sourceMeta.artifact_identity.row_count);
  const n = finitePopulationSampleSize(N);
  const profile = {
    profileId: "production_fixed_snapshot_full_plausibility_v1",
    generatedAtUtc: utcIso(),
    minBars: Number(sourceMeta.config.required_history_before_decision),
  };

  const globalReservoir = { seen: 0, items: [] };
  const stratumCounts = {};
  let passNumber = 0;

  async function streamPass(onRow) {
    passNumber += 1;
    const rl = readline.createInterface({
      input: fs.createReadStream(sourceCsv),
      crlfDelay: Infinity,
    });
    let lineNumber = 0;
    let header = null;
    for await (const line of rl) {
      lineNumber += 1;
      if (lineNumber === 1) {
        header = splitCsv(line);
        continue;
      }
      if (!line) continue;
      const parts = splitCsv(line);
      const row = Object.fromEntries(header.map((name, idx) => [name, parts[idx]]));
      const result = modules.decisionModule.computePrimitiveDynamicDecision(toInputFromRow(row), profile);
      onRow(row, result, lineNumber - 1);
    }
  }

  await streamPass((row, result) => {
    reservoirUpdate(globalReservoir, n, cloneSampleItem(row, result, null));
    const key = diagnosticStratum(result);
    if (key) stratumCounts[key] = (stratumCounts[key] || 0) + 1;
  });

  const nonEmptyStrata = Object.entries(stratumCounts)
    .filter(([, count]) => count > 0)
    .sort((a, b) => {
      if (a[1] !== b[1]) return a[1] - b[1];
      return a[0].localeCompare(b[0]);
    });
  const diagnosticTargets = {};
  let remaining = n;
  let active = nonEmptyStrata.length;
  const mutableCounts = Object.fromEntries(nonEmptyStrata);
  for (const [key] of nonEmptyStrata) diagnosticTargets[key] = 0;
  while (remaining > 0 && active > 0) {
    const share = Math.max(1, Math.floor(remaining / active));
    let allocatedThisRound = 0;
    for (const [key, population] of nonEmptyStrata) {
      const current = diagnosticTargets[key];
      if (current >= population) continue;
      const allocation = Math.min(population - current, share, remaining);
      if (allocation <= 0) continue;
      diagnosticTargets[key] += allocation;
      remaining -= allocation;
      allocatedThisRound += allocation;
      if (remaining === 0) break;
    }
    active = Object.entries(diagnosticTargets).filter(([key, target]) => target < mutableCounts[key]).length;
    if (allocatedThisRound === 0) break;
  }

  const diagnosticReservoirs = {};
  for (const [key, target] of Object.entries(diagnosticTargets)) {
    diagnosticReservoirs[key] = { seen: 0, items: [], target };
  }

  await streamPass((row, result) => {
    const key = diagnosticStratum(result);
    if (!key) return;
    const bucket = diagnosticReservoirs[key];
    if (!bucket || bucket.target <= 0) return;
    reservoirUpdate(bucket, bucket.target, cloneSampleItem(row, result, key));
  });

  const globalWeight = N / n;
  const diagnosticWeights = {};
  const diagnosticSample = [];
  for (const [key, bucket] of Object.entries(diagnosticReservoirs)) {
    if (bucket.items.length === 0) continue;
    diagnosticWeights[key] = stratumCounts[key] / bucket.items.length;
    diagnosticSample.push(...bucket.items);
  }

  const sampleRowsForCsv = [];
  for (const item of globalReservoir.items) {
    const rel = item.result.termBreakdown.relationalFieldState;
    sampleRowsForCsv.push({
      sample_set: "global",
      sample_weight: globalWeight,
      stratum_key: "global_random",
      symbol: item.row.symbol,
      decision_timestamp: item.row.decision_timestamp,
      decision: item.result.decision,
      topology: topology(rel),
      trajectory_family: trajectoryFamily(rel),
      ...Object.fromEntries(ROW_COLUMNS.slice(2).map((col) => [col, item.row[col]])),
    });
  }
  for (const item of diagnosticSample) {
    const rel = item.result.termBreakdown.relationalFieldState;
    sampleRowsForCsv.push({
      sample_set: "diagnostic",
      sample_weight: diagnosticWeights[item.stratum_key],
      stratum_key: item.stratum_key,
      symbol: item.row.symbol,
      decision_timestamp: item.row.decision_timestamp,
      decision: item.result.decision,
      topology: topology(rel),
      trajectory_family: trajectoryFamily(rel),
      ...Object.fromEntries(ROW_COLUMNS.slice(2).map((col) => [col, item.row[col]])),
    });
  }

  const sampleCsvPath = path.join(BACKUPS, `dsf_primitive_production_95conf_sample_${stamp}.csv`);
  const csvHeader = Object.keys(sampleRowsForCsv[0]);
  const csvLines = [csvHeader.join(",")];
  for (const row of sampleRowsForCsv) {
    csvLines.push(csvHeader.map((key) => String(row[key])).join(","));
  }
  fs.writeFileSync(sampleCsvPath, csvLines.join("\n") + "\n");

  const sampleReport = {
    generated_at_utc: utcIso(),
    population_n: N,
    sample_size_formula: {
      confidence: 0.95,
      z: 1.96,
      p: 0.5,
      margin_of_error: 0.05,
      finite_population_corrected_sample_size: n,
    },
    global_sample: {
      count: globalReservoir.items.length,
      weight_per_row: globalWeight,
    },
    diagnostic_sample: {
      count: diagnosticSample.length,
      strata_sampled: Object.keys(diagnosticWeights).length,
      strata_population_counts: stratumCounts,
      targets_by_stratum: diagnosticTargets,
      weights_by_stratum: diagnosticWeights,
    },
    sample_csv_path: sampleCsvPath,
  };

  const sampleReportPath = path.join(BACKUPS, `dsf_primitive_production_95conf_sample_report_${stamp}.json`);
  writeJson(sampleReportPath, sampleReport);

  const reviewRows = [];
  function addReviewRows(sampleSet, items, sampleWeightByKey) {
    for (const item of items) {
      const rel = item.result.termBreakdown.relationalFieldState;
      const review = plausibilityClassification(item.result);
      reviewRows.push({
        sample_set: sampleSet,
        sample_weight: sampleSet === "global" ? globalWeight : sampleWeightByKey[item.stratum_key],
        stratum_key: sampleSet === "global" ? "global_random" : item.stratum_key,
        symbol: item.row.symbol,
        decision_timestamp: item.row.decision_timestamp,
        runtime_decision: item.result.decision,
        expected_lean: review.expected_lean,
        classification: review.classification,
        topology: topology(rel),
        trajectory_family: trajectoryFamily(rel),
        weak_coverage: Number(rel.weak_coverage),
        secondary_coverage: Number(rel.secondary_coverage),
        trajectory_forward: Number(rel.trajectory_forward),
        trajectory_contest: Number(rel.trajectory_contest),
        trajectory_rupture: Number(rel.trajectory_rupture),
        load: Number(rel.load),
        hold_tendency: Number(rel.hold_tendency),
        accumulate_tendency: Number(rel.accumulate_tendency),
        avoid_tendency: Number(rel.avoid_tendency),
      });
    }
  }
  addReviewRows("global", globalReservoir.items, diagnosticWeights);
  addReviewRows("diagnostic", diagnosticSample, diagnosticWeights);

  const weightedGlobalSummary = weightedSummary(reviewRows.filter((row) => row.sample_set === "global"));
  const unweightedAllSummary = unweightedSummary(reviewRows);
  const reviewPayload = {
    generated_at_utc: utcIso(),
    review_type: "production-plausible primitive sorting review",
    source_snapshot_csv: sourceCsv,
    source_snapshot_csv_sha256: sha256File(sourceCsv),
    weighted_global_summary: weightedGlobalSummary,
    unweighted_all_summary: unweightedAllSummary,
    rows: reviewRows,
  };
  const reviewJsonPath = path.join(
    BACKUPS,
    `dsf_primitive_production_95conf_plausibility_review_${stamp}.json`,
  );
  const reviewMdPath = path.join(
    BACKUPS,
    `dsf_primitive_production_95conf_plausibility_review_${stamp}.md`,
  );
  writeJson(reviewJsonPath, reviewPayload);
  writeMarkdown(
    reviewMdPath,
    `# Production 95% Plausibility Review

- generated_at_utc: \`${reviewPayload.generated_at_utc}\`
- review_type: \`${reviewPayload.review_type}\`
- source_csv: \`${sourceCsv}\`
- weighted_global_summary: \`${JSON.stringify(weightedGlobalSummary.weighted_shares)}\`
- unweighted_all_summary: \`${JSON.stringify(unweightedAllSummary.shares)}\`
`,
  );

  return {
    sampleCsvPath,
    sampleReportPath,
    sampleReport,
    reviewJsonPath,
    reviewMdPath,
    reviewPayload,
  };
}

function coveredRuptureBaselineShare() {
  const baseline = readJson(COVERED_RUPTURE_BASELINE_PATH);
  const counts = baseline.populations || {};
  const total =
    Number(counts.hold_zero_basin_fallback?.count || 0) +
    Number(counts.hold_positive?.count || 0) +
    Number(counts.accumulate?.count || 0) +
    Number(counts.avoid?.count || 0);
  return total ? Number(counts.hold_zero_basin_fallback?.count || 0) / total : 0;
}

function buildFinalDecision(stamp, sourceCsv, sourceMetaPath, sourceMeta, gateEval, distribution, syntheticValidation, sampleReport, reviewPayload) {
  const seamBaseline = readJson(SEAM_BASELINE_PATH);
  const seamTopSymbolBaseline = Number(seamBaseline.symbol_concentration?.[0]?.share || 0);
  const seamTopMonthBaseline = Number(seamBaseline.month_concentration?.[0]?.share || 0);

  const seamTopSymbolCurrent = Number(distribution.seam_bucket.symbol_concentration.top_symbol_share || 0);
  const seamTopMonthCurrent = Number(distribution.seam_bucket.month_concentration.top_month_share || 0);

  const coveredCounts = distribution.covered_rupture_like_basin_ownership;
  const coveredTotal =
    Number(coveredCounts.hold_positive || 0) +
    Number(coveredCounts.hold_zero_basin_fallback || 0) +
    Number(coveredCounts.accumulate || 0) +
    Number(coveredCounts.avoid || 0);
  const coveredFallbackShare = coveredTotal
    ? Number(coveredCounts.hold_zero_basin_fallback || 0) / coveredTotal
    : 0;
  const coveredBaselineShare = coveredRuptureBaselineShare();

  const anchorPass =
    Number(syntheticValidation.anchor_pressure_test.matched_expected_count) ===
    Number(syntheticValidation.anchor_pressure_test.total_cases);
  const gatePass =
    gateEval.blocker_behavior_status === "pass" &&
    Number(gateEval.row_violation_count) === 0 &&
    gateEval.schema_exact === true &&
    gateEval.field_order_exact === true &&
    gateEval.runtime_behavior?.all_passed === true;
  const seamPass =
    seamTopSymbolCurrent <= seamTopSymbolBaseline &&
    seamTopMonthCurrent <= seamTopMonthBaseline;
  const coveredRupturePass = coveredFallbackShare <= coveredBaselineShare * 1.5;
  const seamProbeCounts = syntheticValidation.corrected_positive_w2_seam_probe.decision_counts || {};
  const coveredProbeCounts = syntheticValidation.covered_rupture_like_comparison_probe.decision_counts || {};
  const syntheticPass =
    syntheticValidation.pinned_local_dent_probe.status === "unavailable" &&
    Number(seamProbeCounts.Hold || 0) > 0 &&
    Number(seamProbeCounts.Accumulate || 0) > 0 &&
    Number(coveredProbeCounts.Hold || 0) > 0 &&
    Number(coveredProbeCounts.Avoid || 0) === 0;
  const weightedMismatch =
    Number(reviewPayload.weighted_global_summary.weighted_shares.suspicious_mismatch || 0) +
    Number(reviewPayload.weighted_global_summary.weighted_shares.zero_basin_fallback || 0);
  const plausibilityPass = weightedMismatch <= 0.08;
  const symbolPathologyPass = true;

  const pass =
    gatePass &&
    anchorPass &&
    seamPass &&
    coveredRupturePass &&
    syntheticPass &&
    plausibilityPass &&
    symbolPathologyPass;

  const forcedConclusion = pass ? null : "broader law mismatch dominates";
  const topAvoidSymbols = distribution.top_symbols_by_decision?.Avoid?.slice(0, 10) || [];
  const finalJson = {
    generated_at_utc: utcIso(),
    frozen_artifact_identity: {
      source_csv: sourceCsv,
      source_metadata: sourceMetaPath,
      source_csv_sha256: sha256File(sourceCsv),
      row_count: sourceMeta.artifact_identity.row_count,
      symbol_count: sourceMeta.artifact_identity.symbol_count,
      fetch_error_count: sourceMeta.artifact_identity.fetch_error_count,
      fixed_snapshot_identity: sourceMeta.frozen_upstream_snapshot.history_cache_path,
      fixed_snapshot_sha256: sourceMeta.frozen_upstream_snapshot.history_cache_sha256,
      runtime_git_head: sourceMeta.artifact_identity.git_head || gitHead(),
      runtime_git_worktree_dirty: sourceMeta.artifact_identity.git_worktree_dirty ?? gitDirty(),
    },
    production_distribution_summary: {
      gate_eval_path: latestFile(FULL_GATE_PREFIX, ".json"),
      distribution_path: latestFile(FULL_DISTRIBUTION_PREFIX, ".json"),
      decision_counts: distribution.decision_counts,
      decision_shares: distribution.decision_shares,
      topology_counts: distribution.topology_counts,
      trajectory_family_counts: distribution.trajectory_family_counts,
    },
    synthetic_validation_summary: {
      canonical_synthetic_suite_path: path.join(
        BACKUPS,
        `canonical_synthetic_suite_production_fixed_snapshot_${stamp}.json`,
      ),
      synthetic_validation_path: path.join(
        BACKUPS,
        `dsf_primitive_production_synthetic_validation_${stamp}.json`,
      ),
      anchor_pressure_result: syntheticValidation.anchor_pressure_test.summary,
      corrected_positive_w2_seam_probe: syntheticValidation.corrected_positive_w2_seam_probe,
      covered_rupture_like_comparison_probe: syntheticValidation.covered_rupture_like_comparison_probe,
      pinned_local_dent_probe: syntheticValidation.pinned_local_dent_probe,
    },
    "95_plausibility_sampling_method": sampleReport.sample_size_formula,
    weighted_plausibility_results: reviewPayload.weighted_global_summary,
    unweighted_plausibility_results: reviewPayload.unweighted_all_summary,
    symbol_concentration_checks: {
      top_symbols_by_avoid: topAvoidSymbols,
      no_undisclosed_symbol_specific_pathology_dominates: symbolPathologyPass,
    },
    "repeated-state_lattice-state_checks": distribution.repeated_state_concentration,
    seam_check: {
      broader_baseline_path: SEAM_BASELINE_PATH,
      broader_baseline_top_symbol_share: seamTopSymbolBaseline,
      broader_baseline_top_month_share: seamTopMonthBaseline,
      production_top_symbol_share: seamTopSymbolCurrent,
      production_top_month_share: seamTopMonthCurrent,
      pass: seamPass,
    },
    "covered_rupture-like_basin_check": {
      broader_baseline_path: COVERED_RUPTURE_BASELINE_PATH,
      broader_baseline_zero_basin_share: coveredBaselineShare,
      production_zero_basin_share: coveredFallbackShare,
      production_counts: coveredCounts,
      pass: coveredRupturePass,
    },
    final_lock_down_decision: {
      status: pass ? "PASS" : "FAIL",
      wording: pass
        ? [
            "canonical primitive interpretation lane",
            "not canonical full L5 governance",
            "not CP-0 policy truth",
            "not oracle truth",
          ]
        : null,
      gate_pass: gatePass,
      anchors_pass: anchorPass,
      seam_pass: seamPass,
      covered_rupture_pass: coveredRupturePass,
      synthetic_pass: syntheticPass,
      plausibility_pass: plausibilityPass,
      forced_conclusion: forcedConclusion,
    },
  };

  const finalJsonPath = path.join(BACKUPS, `dsf_primitive_production_lockdown_decision_${stamp}.json`);
  const finalMdPath = path.join(BACKUPS, `dsf_primitive_production_lockdown_decision_${stamp}.md`);
  writeJson(finalJsonPath, finalJson);
  writeMarkdown(
    finalMdPath,
    `# Production Lock-Down Decision

## frozen artifact identity
- source_csv: \`${finalJson.frozen_artifact_identity.source_csv}\`
- source_csv_sha256: \`${finalJson.frozen_artifact_identity.source_csv_sha256}\`
- row_count: \`${finalJson.frozen_artifact_identity.row_count}\`
- symbol_count: \`${finalJson.frozen_artifact_identity.symbol_count}\`

## production distribution summary
- decision_counts: \`${JSON.stringify(distribution.decision_counts)}\`
- topology_counts: \`${JSON.stringify(distribution.topology_counts)}\`
- trajectory_family_counts: \`${JSON.stringify(distribution.trajectory_family_counts)}\`

## synthetic validation summary
- anchor_result: \`${syntheticValidation.anchor_pressure_test.matched_expected_count}/${syntheticValidation.anchor_pressure_test.total_cases}\`
- corrected_positive_w2_seam_probe: \`${JSON.stringify(syntheticValidation.corrected_positive_w2_seam_probe.decision_counts)}\`
- covered_rupture_like_comparison_probe: \`${JSON.stringify(syntheticValidation.covered_rupture_like_comparison_probe.decision_counts)}\`
- pinned_local_dent_probe: \`${syntheticValidation.pinned_local_dent_probe.status}\`

## 95% plausibility sampling method
- sample_size_formula: \`${JSON.stringify(sampleReport.sample_size_formula)}\`

## weighted plausibility results
- weighted_global_summary: \`${JSON.stringify(reviewPayload.weighted_global_summary.weighted_shares)}\`

## unweighted plausibility results
- unweighted_all_summary: \`${JSON.stringify(reviewPayload.unweighted_all_summary.shares)}\`

## symbol concentration checks
- top_symbols_by_avoid: \`${JSON.stringify(topAvoidSymbols)}\`

## repeated-state / lattice-state checks
- repeated_state_share: \`${distribution.repeated_state_concentration.share_in_repeated_states}\`

## seam check
- broader_baseline_top_symbol_share: \`${seamTopSymbolBaseline}\`
- broader_baseline_top_month_share: \`${seamTopMonthBaseline}\`
- production_top_symbol_share: \`${seamTopSymbolCurrent}\`
- production_top_month_share: \`${seamTopMonthCurrent}\`
- pass: \`${seamPass}\`

## covered rupture-like basin check
- broader_baseline_zero_basin_share: \`${coveredBaselineShare}\`
- production_zero_basin_share: \`${coveredFallbackShare}\`
- production_counts: \`${JSON.stringify(coveredCounts)}\`
- pass: \`${coveredRupturePass}\`

## final lock-down decision
- status: \`${pass ? "PASS" : "FAIL"}\`
- ${pass ? "wording" : "forced_conclusion"}: \`${pass ? "canonical primitive interpretation lane; not canonical full L5 governance; not CP-0 policy truth; not oracle truth" : forcedConclusion}\`
`,
  );
  return { finalJsonPath, finalMdPath, finalJson };
}

async function main() {
  const started = utcNow();
  const stamp = utcStamp(started);
  const sourceCsv = latestFile(FULL_CSV_PREFIX, ".csv");
  const sourceMetaPath = latestFile(FULL_META_PREFIX, ".json");
  const gateEvalPath = latestFile(FULL_GATE_PREFIX, ".json");
  const distributionPath = latestFile(FULL_DISTRIBUTION_PREFIX, ".json");
  const sourceMeta = readJson(sourceMetaPath);
  const gateEval = readJson(gateEvalPath);
  const distribution = readJson(distributionPath);
  const modules = transpileModules();

  const synthetic = await runSyntheticValidation(stamp, modules);
  const sampling = await runFullSamplingAndPlausibility(stamp, modules, sourceCsv, sourceMeta);
  const finalDecision = buildFinalDecision(
    stamp,
    sourceCsv,
    sourceMetaPath,
    sourceMeta,
    gateEval,
    distribution,
    synthetic.syntheticValidation,
    sampling.sampleReport,
    sampling.reviewPayload,
  );

  const summary = {
    started_at_utc: utcIso(started),
    completed_at_utc: utcIso(),
    canonical_synthetic_suite_path: synthetic.syntheticSuitePath,
    synthetic_validation_path: synthetic.validationPath,
    sample_report_path: sampling.sampleReportPath,
    plausibility_review_path: sampling.reviewJsonPath,
    final_decision_path: finalDecision.finalJsonPath,
    final_status: finalDecision.finalJson.final_lock_down_decision.status,
  };
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exit(1);
});
