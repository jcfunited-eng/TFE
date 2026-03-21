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

  throw new Error("No usable snapshot rows found for anchor neighborhood scan.");
}

function transpileSupportModules() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "uf-anchor-neighborhood-"));

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

function inEnvelope(value, envelope) {
  return value >= envelope.min && value <= envelope.max;
}

function matchClassEnvelope(result, classSummary) {
  const normalized = result?.provenance?.normalizedInput;
  const direct = result?.termBreakdown?.directFieldState;
  if (!normalized || !direct) return false;

  for (const [field, envelope] of Object.entries(classSummary.normalized_field_envelope)) {
    if (!inEnvelope(normalized[field], envelope)) {
      return false;
    }
  }

  for (const [field, envelope] of Object.entries(classSummary.direct_field_state_envelope)) {
    if (!inEnvelope(direct[field], envelope)) {
      return false;
    }
  }

  return true;
}

function main() {
  ensureDir(RUNTIME_DIR);

  const anchor = JSON.parse(fs.readFileSync(ANCHOR_PATH, "utf8"));
  const snapshot = loadSnapshotRows();
  const { decisionModule, pressureModule } = transpileSupportModules();

  const classSummaries = anchor.class_summaries;
  const classOrder = ["Accumulate", "Hold", "Avoid"];
  const summary = {};

  for (const className of classOrder) {
    summary[className] = {
      envelopeMatchedCount: 0,
      matchedDecisionCount: 0,
      mismatchedDecisionCount: 0,
      sampleSymbols: [],
    };
  }

  for (const row of snapshot.rows) {
    const symbol = String(row.ticker ?? "").trim().toUpperCase();
    if (!symbol) continue;

    const input = pressureModule.dynamicDecisionInputFromRow(row, symbol);
    const result = decisionModule.computePrimitiveDynamicDecision(
      input,
      pressureModule.PRESSURE_TEST_PROFILE_EXAMPLE_V1,
    );

    if (result.blockerCode !== "NONE") continue;

    for (const className of classOrder) {
      const classSummary = classSummaries[className];
      if (!matchClassEnvelope(result, classSummary)) continue;

      const bucket = summary[className];
      bucket.envelopeMatchedCount += 1;
      if (result.decision === className) {
        bucket.matchedDecisionCount += 1;
      } else {
        bucket.mismatchedDecisionCount += 1;
      }

      if (bucket.sampleSymbols.length < 12) {
        bucket.sampleSymbols.push({
          symbol,
          decision: result.decision,
          continuation_state: result.termBreakdown.directFieldState.continuation_state,
          instability_state: result.termBreakdown.directFieldState.instability_state,
          admissibility_state: result.termBreakdown.directFieldState.admissibility_state,
        });
      }
    }
  }

  const outPath = path.join(
    RUNTIME_DIR,
    `uf_dynamic_decision_anchor_neighborhood_scan_${utcStamp()}.json`,
  );

  const report = {
    generated_at_utc: new Date().toISOString(),
    method: {
      type: "primitive_anchor_neighborhood_scan",
      note: "Scans snapshot rows for exact membership inside the verified 9-case anchor envelopes and checks whether the current primitive preserves the same class ordering. This is not runtime architecture.",
      anchor_report_path: ANCHOR_PATH,
      snapshot_source_path: snapshot.sourcePath,
    },
    summary,
  };

  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ report_path: outPath, summary }, null, 2));
}

main();
