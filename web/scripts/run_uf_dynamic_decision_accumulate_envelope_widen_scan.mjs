import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import Module from "node:module";

import ts from "typescript";

const ROOT = "/workspaces/Tao_Financial_Engine";
const RUNTIME_DIR = path.join(ROOT, "backups", "runtime");
const ANCHOR_PATH = path.join(
  ROOT,
  "backups",
  "runtime",
  "uf_dynamic_decision_anchor_structure_extract_20260318T082522Z.json",
);

const NORMALIZED_FIELDS = [
  "D_k",
  "M_k",
  "R_UF_centered",
  "S_UF_centered",
  "stability_centered",
  "B_k",
  "U_star_k",
  "R_rev_k",
  "C_k_normalized",
  "P_k_normalized",
];

const DIRECT_FIELDS = [
  "continuation_state",
  "instability_state",
  "admissibility_state",
];

const WIDEN_STEPS = [0.0, 0.02, 0.05, 0.08, 0.1, 0.12, 0.15, 0.18, 0.2, 0.25, 0.3];

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

  throw new Error("No usable snapshot rows found for accumulate envelope widen scan.");
}

function transpileSupportModules() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "uf-acc-envelope-"));

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
  return {
    decisionModule: localRequire(decisionOutPath),
    pressureModule: localRequire(pressureOutPath),
  };
}

function inWidenedEnvelope(value, envelope, widenBy) {
  return value >= envelope.min - widenBy && value <= envelope.max + widenBy;
}

function matchAccumulateEnvelope(result, accumulateSummary, widenBy) {
  const normalized = result?.provenance?.normalizedInput;
  const direct = result?.termBreakdown?.directFieldState;
  if (!normalized || !direct) return false;

  for (const field of NORMALIZED_FIELDS) {
    if (!inWidenedEnvelope(normalized[field], accumulateSummary.normalized_field_envelope[field], widenBy)) {
      return false;
    }
  }

  for (const field of DIRECT_FIELDS) {
    if (!inWidenedEnvelope(direct[field], accumulateSummary.direct_field_state_envelope[field], widenBy)) {
      return false;
    }
  }

  return true;
}

function scanStep(rows, accumulateSummary, pressureModule, decisionModule, widenBy) {
  const out = {
    widenBy,
    envelopeMatchedCount: 0,
    matchedDecisionCount: 0,
    mismatchedDecisionCount: 0,
    mismatchSamples: [],
    matchedSamples: [],
  };

  for (const row of rows) {
    const symbol = String(row.ticker ?? "").trim().toUpperCase();
    if (!symbol) continue;

    const input = pressureModule.dynamicDecisionInputFromRow(row, symbol);
    const result = decisionModule.computePrimitiveDynamicDecision(
      input,
      pressureModule.PRESSURE_TEST_PROFILE_EXAMPLE_V1,
    );

    if (result.blockerCode !== "NONE") continue;
    if (!matchAccumulateEnvelope(result, accumulateSummary, widenBy)) continue;

    out.envelopeMatchedCount += 1;

    const sample = {
      symbol,
      decision: result.decision,
      continuation_state: result.termBreakdown.directFieldState.continuation_state,
      instability_state: result.termBreakdown.directFieldState.instability_state,
      admissibility_state: result.termBreakdown.directFieldState.admissibility_state,
    };

    if (result.decision === "Accumulate") {
      out.matchedDecisionCount += 1;
      if (out.matchedSamples.length < 12) {
        out.matchedSamples.push(sample);
      }
    } else {
      out.mismatchedDecisionCount += 1;
      if (out.mismatchSamples.length < 12) {
        out.mismatchSamples.push(sample);
      }
    }
  }

  return out;
}

function main() {
  ensureDir(RUNTIME_DIR);

  const anchor = JSON.parse(fs.readFileSync(ANCHOR_PATH, "utf8"));
  const accumulateSummary = anchor.class_summaries.Accumulate;
  const snapshot = loadSnapshotRows();
  const { decisionModule, pressureModule } = transpileSupportModules();

  const steps = WIDEN_STEPS.map((widenBy) =>
    scanStep(snapshot.rows, accumulateSummary, pressureModule, decisionModule, widenBy),
  );

  let firstNonExactStep = null;
  for (const step of steps) {
    if (step.mismatchedDecisionCount > 0) {
      firstNonExactStep = step.widenBy;
      break;
    }
  }

  const outPath = path.join(
    RUNTIME_DIR,
    `uf_dynamic_decision_accumulate_envelope_widen_scan_${utcStamp()}.json`,
  );

  const report = {
    generated_at_utc: new Date().toISOString(),
    method: {
      type: "primitive_accumulate_envelope_widen_scan",
      note: "Widens only the verified Accumulate anchor envelope by small uniform amounts and checks the first point where class-preserving snapshot matches stop being exact. This is not runtime architecture.",
      anchor_report_path: ANCHOR_PATH,
      snapshot_source_path: snapshot.sourcePath,
      widen_steps: WIDEN_STEPS,
    },
    first_non_exact_widen_step: firstNonExactStep,
    steps,
  };

  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ report_path: outPath, first_non_exact_widen_step: firstNonExactStep, steps }, null, 2));
}

main();
