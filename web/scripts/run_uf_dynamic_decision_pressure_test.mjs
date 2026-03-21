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

  throw new Error("No usable snapshot rows found for dynamic pressure test.");
}

function transpileSupportModules() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "uf-dynamic-pressure-"));

  const decisionSrcPath = path.join(ROOT, "web", "src", "lib", "uf-dynamic-decision.ts");
  const pressureSrcPath = path.join(ROOT, "web", "src", "lib", "uf-dynamic-decision-pressure-test.ts");

  const decisionOutPath = path.join(tempDir, "uf-dynamic-decision.cjs");
  const pressureOutPath = path.join(tempDir, "uf-dynamic-decision-pressure-test.cjs");

  const decisionSource = fs.readFileSync(decisionSrcPath, "utf8");
  let pressureSource = fs.readFileSync(pressureSrcPath, "utf8");
  pressureSource = pressureSource.replace('@/lib/uf-dynamic-decision', "./uf-dynamic-decision.cjs");

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

function sampleCases(rows, pressureModule) {
  const cases = [
    pressureModule.pressureTestCaseFromRows(
      rows,
      "AGO",
      "Accumulate",
      "Positive D, positive M, decent R/S, moderate uncertainty; primitive accumulate plausibility sample.",
    ),
    pressureModule.pressureTestCaseFromRows(
      rows,
      "TXRH",
      "Accumulate",
      "Positive D with strong S and moderate U; second accumulate plausibility sample.",
    ),
    pressureModule.pressureTestCaseFromRows(
      rows,
      "DHI",
      "Accumulate",
      "Positive D with favorable R and low P; third accumulate plausibility sample.",
    ),
    pressureModule.pressureTestCaseFromRows(
      rows,
      "AAT",
      "Hold",
      "Neutral D/M with mid-range R and no directional stress; primitive hold sample.",
    ),
    pressureModule.pressureTestCaseFromRows(
      rows,
      "ACGL",
      "Hold",
      "Neutral D/M and no reversal; second hold sample.",
    ),
    pressureModule.pressureTestCaseFromRows(
      rows,
      "ADC",
      "Hold",
      "Neutral directional state with no obvious avoid trigger; third hold sample.",
    ),
    pressureModule.pressureTestCaseFromRows(
      rows,
      "AA",
      "Avoid",
      "Negative D, negative M, weak R/S, high drag terms; primitive avoid sample.",
    ),
    pressureModule.pressureTestCaseFromRows(
      rows,
      "AAPL",
      "Avoid",
      "Negative D, negative M, high U and reversal active; second avoid sample.",
    ),
    pressureModule.pressureTestCaseFromRows(
      rows,
      "ACLS",
      "Avoid",
      "Negative D, low R/S, strong drag and reversal pressure; third avoid sample.",
    ),
  ];

  return cases;
}

function main() {
  ensureDir(RUNTIME_DIR);

  const snapshot = loadSnapshotRows();
  const pressureModule = transpileSupportModules();
  const cases = sampleCases(snapshot.rows, pressureModule);
  const run = pressureModule.runDynamicDecisionPressureTest(
    cases,
    pressureModule.PRESSURE_TEST_PROFILE_EXAMPLE_V1,
  );

  const stamp = utcStamp();
  const outPath = path.join(RUNTIME_DIR, `uf_dynamic_decision_pressure_test_report_${stamp}.json`);

  const report = {
    generated_at_utc: new Date().toISOString(),
    snapshot_source_path: snapshot.sourcePath,
    sample_case_count: cases.length,
    profile_id: run.profileId,
    method: {
      type: "primitive_dynamic_runtime_pressure_test",
      note: "Expected labels are inspection anchors for primitive plausibility, not market-truth labels.",
      sample_selection: [
        "Accumulate candidates chosen from real snapshot rows with positive D and comparatively stronger support terms.",
        "Hold candidates chosen from real snapshot rows with neutral D/M and low directional stress.",
        "Avoid candidates chosen from real snapshot rows with negative D and materially adverse drag terms.",
      ],
    },
    cases: run.results,
    summary: run.summary,
  };

  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ report_path: outPath, summary: run.summary }, null, 2));
}

main();
