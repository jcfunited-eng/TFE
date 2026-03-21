#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine")
WEB_ROOT = REPO_ROOT / "web"
SRC_ROOT = WEB_ROOT / "src"
BACKUPS_ROOT = REPO_ROOT / "backups" / "runtime"
TSC_BIN = WEB_ROOT / "node_modules" / ".bin" / "tsc"
ROUTE_PATH = SRC_ROOT / "app" / "api" / "admin" / "refresh" / "route.ts"


@dataclass(frozen=True)
class Paths:
    temp_root: Path
    route_typecheck_tsconfig_path: Path
    route_runtime_tsconfig_path: Path
    step1_runtime_tsconfig_path: Path
    route_emit_root: Path
    step1_emit_root: Path
    route_harness_path: Path
    route_harness_result_path: Path
    route_stub_capture_path: Path
    step1_harness_path: Path
    step1_harness_result_path: Path
    proof_store_path: Path
    artifact_path: Path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_token(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_paths(now: datetime) -> Paths:
    token = timestamp_token(now)
    temp_root = Path(tempfile.mkdtemp(prefix=f"step1-cutover-authority-repair-{token}-", dir=str(BACKUPS_ROOT)))
    return Paths(
        temp_root=temp_root,
        route_typecheck_tsconfig_path=temp_root / "tsconfig.route-typecheck.json",
        route_runtime_tsconfig_path=temp_root / "tsconfig.route-runtime.json",
        step1_runtime_tsconfig_path=temp_root / "tsconfig.step1-runtime.json",
        route_emit_root=temp_root / "route-emit",
        step1_emit_root=temp_root / "step1-emit",
        route_harness_path=temp_root / "run-route-proof.js",
        route_harness_result_path=temp_root / "route-harness-result.json",
        route_stub_capture_path=temp_root / "route-stub-capture.json",
        step1_harness_path=temp_root / "run-step1-proof.js",
        step1_harness_result_path=temp_root / "step1-harness-result.json",
        proof_store_path=temp_root / "step1-proof-store.json",
        artifact_path=BACKUPS_ROOT / f"step1-cutover-authority-repair-proof-{token}.json",
    )


def write_route_typecheck_tsconfig(paths: Paths) -> None:
    config = {
        "compilerOptions": {
            "target": "ES2022",
            "lib": ["dom", "dom.iterable", "esnext"],
            "allowJs": True,
            "skipLibCheck": True,
            "strict": True,
            "noEmit": True,
            "esModuleInterop": True,
            "module": "esnext",
            "moduleResolution": "bundler",
            "resolveJsonModule": True,
            "isolatedModules": True,
            "jsx": "react-jsx",
            "baseUrl": str(WEB_ROOT),
            "paths": {"@/*": ["./src/*"]},
            "types": ["node"],
            "typeRoots": [str(WEB_ROOT / "node_modules" / "@types")],
        },
        "include": [
            str(WEB_ROOT / "next-env.d.ts"),
            str(ROUTE_PATH),
            str(SRC_ROOT / "lib" / "step1" / "schema.ts"),
            str(SRC_ROOT / "lib" / "step1" / "run-request.ts"),
            str(SRC_ROOT / "lib" / "step1" / "candidate-bundle.ts"),
            str(SRC_ROOT / "lib" / "step1" / "assessment-report.ts"),
            str(SRC_ROOT / "lib" / "step1" / "publication-commit.ts"),
            str(SRC_ROOT / "lib" / "step1" / "followup-ticket.ts"),
            str(SRC_ROOT / "lib" / "step1" / "orchestrator.ts"),
        ],
    }
    write_json(paths.route_typecheck_tsconfig_path, config)


def write_route_runtime_tsconfig(paths: Paths) -> None:
    config = {
        "compilerOptions": {
            "target": "ES2022",
            "module": "commonjs",
            "moduleResolution": "node",
            "esModuleInterop": True,
            "strict": True,
            "skipLibCheck": True,
            "resolveJsonModule": True,
            "outDir": str(paths.route_emit_root),
            "rootDir": str(SRC_ROOT),
            "baseUrl": str(WEB_ROOT),
            "paths": {"@/*": ["./src/*"]},
            "types": ["node"],
            "typeRoots": [str(WEB_ROOT / "node_modules" / "@types")],
        },
        "include": [str(ROUTE_PATH)],
    }
    write_json(paths.route_runtime_tsconfig_path, config)


def write_step1_runtime_tsconfig(paths: Paths) -> None:
    config = {
        "compilerOptions": {
            "target": "ES2022",
            "module": "commonjs",
            "moduleResolution": "node",
            "esModuleInterop": True,
            "strict": True,
            "skipLibCheck": True,
            "resolveJsonModule": True,
            "outDir": str(paths.step1_emit_root),
            "rootDir": str(SRC_ROOT),
            "baseUrl": str(WEB_ROOT),
            "paths": {"@/*": ["./src/*"]},
            "types": ["node"],
            "typeRoots": [str(WEB_ROOT / "node_modules" / "@types")],
        },
        "include": [
            str(SRC_ROOT / "lib" / "runtime-db.ts"),
            str(SRC_ROOT / "lib" / "workspace-root.ts"),
            str(SRC_ROOT / "lib" / "publication-state.ts"),
            str(SRC_ROOT / "lib" / "runtime-publication-bundle.ts"),
            str(SRC_ROOT / "lib" / "step1" / "schema.ts"),
            str(SRC_ROOT / "lib" / "step1" / "run-request.ts"),
            str(SRC_ROOT / "lib" / "step1" / "candidate-bundle.ts"),
            str(SRC_ROOT / "lib" / "step1" / "assessment-report.ts"),
            str(SRC_ROOT / "lib" / "step1" / "publication-commit.ts"),
            str(SRC_ROOT / "lib" / "step1" / "followup-ticket.ts"),
            str(SRC_ROOT / "lib" / "step1" / "orchestrator.ts"),
        ],
    }
    write_json(paths.step1_runtime_tsconfig_path, config)


def run_tsc(project_path: Path) -> None:
    env = os.environ.copy()
    env["NODE_PATH"] = str(WEB_ROOT / "node_modules")
    subprocess.run(
        [str(TSC_BIN), "-p", str(project_path)],
        cwd=str(REPO_ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def build_route_source_proof() -> dict[str, object]:
    source = ROUTE_PATH.read_text(encoding="utf-8")
    branch_text = "if (cutoverMode && modeInput.mode === STEP1_EXISTING_ADMIN_REFRESH_MODE)"
    dispatch_text = 'requestedMode: STEP1_EXISTING_ADMIN_REFRESH_MODE'
    spawn_text = "const child = spawn(pythonBin, args, {"
    branch_index = source.find(branch_text)
    dispatch_index = source.find(dispatch_text)
    spawn_index = source.find(spawn_text)
    if branch_index < 0:
        raise AssertionError("route.ts is missing the enabled snapshot cutover branch.")
    if dispatch_index < 0:
        raise AssertionError("route.ts is missing the snapshot cutover dispatch payload.")
    if spawn_index < 0:
        raise AssertionError("route.ts is missing the legacy Python spawn block.")
    if branch_index > spawn_index:
        raise AssertionError("route.ts routes the snapshot cutover branch after the legacy Python spawn block.")
    return {
        "route_path": str(ROUTE_PATH),
        "enabled_snapshot_cutover_branch_present": True,
        "enabled_snapshot_cutover_dispatch_present": True,
        "enabled_snapshot_cutover_branch_before_spawn": True,
    }


def write_route_runtime_stubs(paths: Paths) -> None:
    node_modules_root = paths.temp_root / "node_modules"
    write_text(
        node_modules_root / "next" / "server.js",
        """exports.NextResponse = {
  json(payload, init) {
    return new Response(JSON.stringify(payload), {
      status: init && typeof init.status === "number" ? init.status : 200,
      headers: { "content-type": "application/json" },
    });
  },
};
""",
    )
    write_text(
        node_modules_root / "pg" / "index.js",
        """class Pool {}
module.exports = { Pool };
""",
    )
    write_text(
        node_modules_root / "@" / "lib" / "auth-session.js",
        """exports.readSessionUserFromRequest = async function readSessionUserFromRequest() {
  return null;
};
""",
    )
    write_text(
        node_modules_root / "@" / "lib" / "publication-state.js",
        """exports.loadCanonicalPublicationState = async function loadCanonicalPublicationState() {
  return {
    activationState: "activated",
    servingState: "allowed",
    blockingReasonCode: null,
    blockingReasonDetail: null,
  };
};
exports.loadRuntimeRefreshRunById = async function loadRuntimeRefreshRunById() { return null; };
exports.persistPublicationStateForRun = async function persistPublicationStateForRun() {};
exports.publicationCandidateIsValid = function publicationCandidateIsValid() { return true; };
exports.setActivePublicationRun = async function setActivePublicationRun() { return true; };
""",
    )
    write_text(
        node_modules_root / "@" / "lib" / "refresh-terminal-truth.js",
        """exports.assessPreActivationPublicationCriticalTruth = function assessPreActivationPublicationCriticalTruth() {
  return { ok: true, failureReasons: [] };
};
exports.buildTerminalFailurePhaseTruthReconciliation = function buildTerminalFailurePhaseTruthReconciliation() {
  return {};
};
exports.phaseSummary = function phaseSummary() { return ""; };
exports.PRE_ACTIVATION_PUBLICATION_CRITICAL_PHASES = [];
exports.publicationCriticalPhaseSucceeded = function publicationCriticalPhaseSucceeded() { return true; };
""",
    )
    write_text(
        node_modules_root / "@" / "lib" / "runtime-postgres.js",
        """exports.loadRuntimeQuoteCacheFromPostgres = async function loadRuntimeQuoteCacheFromPostgres() {
  return { sourcePath: null, quotes: {}, runId: null };
};
exports.loadRuntimeSnapshotRowsFromPostgres = async function loadRuntimeSnapshotRowsFromPostgres() {
  return { sourcePath: null, rows: [], runId: null, generatedAtUtc: null };
};
""",
    )
    write_text(
        node_modules_root / "@" / "lib" / "admin-refresh-persist.js",
        """exports.ADMIN_REFRESH_PERSIST_KEYS = [];
exports.appendAdminRefreshHistorySnapshotLine = async function appendAdminRefreshHistorySnapshotLine() {};
exports.readAdminRefreshPersist = async function readAdminRefreshPersist() { return null; };
exports.writeAdminRefreshPersist = async function writeAdminRefreshPersist() {};
""",
    )
    write_text(
        node_modules_root / "@" / "lib" / "workspace-root.js",
        f"""exports.resolveWorkspaceRoot = function resolveWorkspaceRoot() {{
  return {json.dumps(str(REPO_ROOT))};
}};
""",
    )
    write_text(
        node_modules_root / "@" / "lib" / "step1" / "orchestrator.js",
        """const fs = require("node:fs");

const CAPTURE_PATH = String(process.env.TFE_STEP1_ROUTE_STUB_CAPTURE_PATH || "");
const CONTRACT_ENV = "TFE_STEP1_CUTOVER_REQUEST_CONTRACT_JSON";

function readCapture() {
  if (!CAPTURE_PATH || !fs.existsSync(CAPTURE_PATH)) {
    return { resolutionCalls: [], dispatchCalls: [] };
  }
  return JSON.parse(fs.readFileSync(CAPTURE_PATH, "utf8"));
}

function writeCapture(payload) {
  if (!CAPTURE_PATH) return;
  fs.writeFileSync(CAPTURE_PATH, JSON.stringify(payload, null, 2) + "\\n");
}

function readEnvContract() {
  const raw = String(process.env[CONTRACT_ENV] || "").trim();
  if (!raw) return {};
  return JSON.parse(raw);
}

exports.STEP1_CUTOVER_REQUEST_MODE = "step1_cutover";
exports.STEP1_EXISTING_ADMIN_REFRESH_MODE = "snapshot";
exports.STEP1_CUTOVER_EXECUTION_PATH = "step1_orchestrator";
exports.STEP1_LEGACY_PATH_STATUS = "read_only_history_only";
exports.STEP1_CUTOVER_MODE_ENV = "TFE_STEP1_CUTOVER_MODE";
exports.STEP1_CUTOVER_PROOF_STORE_ENV = "TFE_STEP1_FILE_PROOF_STORE_PATH";

exports.resolveStep1OrchestratorInputFromAdminRefreshRequest = function resolveStep1OrchestratorInputFromAdminRefreshRequest(params) {
  const requestBody = params && params.requestBody && typeof params.requestBody === "object" ? params.requestBody : {};
  const envContract = readEnvContract();
  const merged = { ...envContract, ...requestBody };
  const requestKeys = Object.keys(requestBody).filter((key) => key !== "mode");
  const envKeys = Object.keys(envContract);
  const contractSource = requestKeys.length > 0 && envKeys.length > 0
    ? "merged"
    : requestKeys.length > 0
      ? "request_body"
      : "env_contract";
  const resolution = {
    contractSource,
    input: {
      runId: merged.runId || undefined,
      normalizedPackageId: merged.normalizedPackageId,
      policySetId: merged.policySetId,
      modelSetId: merged.modelSetId,
      configSetId: merged.configSetId,
      bundleClass: merged.bundleClass,
      dependencyClassificationRegister: merged.dependencyClassificationRegister,
      targetEnvironment: merged.targetEnvironment,
      requestedBy: params.requestedBy,
      requestedAtUtc: merged.requestedAtUtc || undefined,
      assessmentRuleSetId: merged.assessmentRuleSetId,
      followupDesiredStatus: merged.followupDesiredStatus || "deferred",
      mode: params.requestedMode,
      triggerSource: params.executionMode === "readonly"
        ? "step1_admin_refresh_snapshot_readonly"
        : "step1_admin_refresh_snapshot_enabled",
    },
  };
  const capture = readCapture();
  capture.resolutionCalls.push({
    requestedMode: params.requestedMode,
    executionMode: params.executionMode,
    requestedBy: params.requestedBy,
    requestBody,
    contractSource,
    resolvedInput: resolution.input,
  });
  writeCapture(capture);
  return resolution;
};

exports.dispatchStep1Orchestrator = async function dispatchStep1Orchestrator(input, options) {
  const capture = readCapture();
  capture.dispatchCalls.push({ input, options });
  writeCapture(capture);
  return {
    executionPath: "step1_orchestrator",
    legacyStep1PathStatus: "read_only_history_only",
    legacyRunnerDispatched: false,
    cutoverMode: options.executionMode,
    persistenceKind: "file-proof",
    runId: input.runId || "step1-route-stub-run",
    requestArtifactPath: "/tmp/request.json",
    candidateBundleManifestPath: "/tmp/candidate-manifest.json",
    candidateBundleId: "candidate_bundle_stub",
    assessmentReportPath: "/tmp/assessment-report.json",
    assessmentReportId: "assessment_report_stub",
    publicationManifestPath: "/tmp/publication-manifest.json",
    publicationBundleId: "publication_bundle_stub",
    followupTicketPath: "/tmp/followup-ticket.json",
    followupJobId: "followup_job_stub",
    followupStatus: "deferred",
  };
};
""",
    )


def write_step1_runtime_aliases(paths: Paths) -> None:
    node_modules_root = paths.temp_root / "node_modules"
    write_text(
        node_modules_root / "@" / "lib" / "runtime-db.js",
        f"""const path = require("node:path");
module.exports = require(path.join({json.dumps(str(paths.step1_emit_root))}, "lib", "runtime-db.js"));
""",
    )
    write_text(
        node_modules_root / "@" / "lib" / "publication-state.js",
        f"""const path = require("node:path");
module.exports = require(path.join({json.dumps(str(paths.step1_emit_root))}, "lib", "publication-state.js"));
""",
    )
    write_text(
        node_modules_root / "@" / "lib" / "runtime-publication-bundle.js",
        f"""const path = require("node:path");
module.exports = require(path.join({json.dumps(str(paths.step1_emit_root))}, "lib", "runtime-publication-bundle.js"));
""",
    )


def write_route_harness(paths: Paths) -> None:
    contract_json = {
        "runId": "step1-route-cutover-enabled-proof",
        "normalizedPackageId": "normalized-package-demo",
        "policySetId": "policy-set-demo",
        "modelSetId": "model-set-demo",
        "configSetId": "config-set-demo",
        "bundleClass": "publication_candidate",
        "dependencyClassificationRegister": {
            "normalized_package": "classified",
            "policy_bundle": "classified",
            "model_bundle": "classified",
            "config_bundle": "classified",
        },
        "targetEnvironment": "production",
        "assessmentRuleSetId": "assessment-rules-v1",
        "followupDesiredStatus": "deferred",
    }
    harness = f"""const fs = require("node:fs");
const childProcess = require("node:child_process");

const routeModulePath = {json.dumps(str(paths.route_emit_root / "app" / "api" / "admin" / "refresh" / "route.js"))};
const harnessResultPath = {json.dumps(str(paths.route_harness_result_path))};
const capturePath = {json.dumps(str(paths.route_stub_capture_path))};

async function main() {{
  const spawnCalls = [];
  const originalSpawn = childProcess.spawn;
  childProcess.spawn = function patchedSpawn(...args) {{
    spawnCalls.push(args.map((entry) => {{
      if (Array.isArray(entry)) return entry;
      if (entry && typeof entry === "object") return Object.keys(entry);
      return String(entry);
    }}));
    throw new Error("spawn_should_not_be_called_for_snapshot_cutover");
  }};

  process.env.TFE_INTERNAL_REFRESH_TOKEN = "proof-token";
  process.env.TFE_STEP1_CUTOVER_MODE = "enabled";
  process.env.TFE_STEP1_CUTOVER_REQUEST_CONTRACT_JSON = {json.dumps(json.dumps(contract_json))};
  process.env.TFE_STEP1_ROUTE_STUB_CAPTURE_PATH = capturePath;
  fs.writeFileSync(capturePath, JSON.stringify({{ resolutionCalls: [], dispatchCalls: [] }}, null, 2) + "\\n");

  try {{
    const route = require(routeModulePath);
    const request = new Request("http://localhost/api/admin/refresh", {{
      method: "POST",
      headers: {{
        "content-type": "application/json",
        "x-tfe-internal-refresh-token": "proof-token"
      }},
      body: JSON.stringify({{ mode: "snapshot" }})
    }});
    const response = await route.POST(request);
    const payload = await response.json();
    const capture = JSON.parse(fs.readFileSync(capturePath, "utf8"));
    fs.writeFileSync(harnessResultPath, JSON.stringify({{
      responseStatus: response.status,
      responsePayload: payload,
      spawnCallCount: spawnCalls.length,
      capture
    }}, null, 2) + "\\n");
  }} catch (error) {{
    fs.writeFileSync(harnessResultPath, JSON.stringify({{
      error: error instanceof Error ? error.message : String(error)
    }}, null, 2) + "\\n");
    process.exitCode = 1;
  }} finally {{
    childProcess.spawn = originalSpawn;
  }}
}}

main();
"""
    write_text(paths.route_harness_path, harness)


def write_step1_harness(paths: Paths, now: datetime) -> None:
    run_id = f"step1-cutover-authority-repair-{timestamp_token(now).lower()}"
    requested_at = iso_z(now)
    harness = f"""const fs = require("node:fs");
const path = require("node:path");

const repoRoot = {json.dumps(str(REPO_ROOT))};
const emitRoot = {json.dumps(str(paths.step1_emit_root))};
const proofStorePath = {json.dumps(str(paths.proof_store_path))};
const harnessResultPath = {json.dumps(str(paths.step1_harness_result_path))};

async function main() {{
  const schema = require(path.join(emitRoot, "lib", "step1", "schema.js"));
  const orchestrator = require(path.join(emitRoot, "lib", "step1", "orchestrator.js"));
  const publicationState = require(path.join(emitRoot, "lib", "publication-state.js"));
  const runtimePublicationBundle = require(path.join(emitRoot, "lib", "runtime-publication-bundle.js"));

  process.env.TFE_STEP1_ACTIVE_POINTER_SOURCE = "cutover";
  process.env.TFE_STEP1_FILE_PROOF_STORE_PATH = proofStorePath;
  process.env.TFE_STEP1_TARGET_ENVIRONMENT = "production";

  const result = await orchestrator.dispatchStep1Orchestrator(
    {{
      runId: {json.dumps(run_id)},
      normalizedPackageId: "normalized-package-demo",
      policySetId: "policy-set-demo",
      modelSetId: "model-set-demo",
      configSetId: "config-set-demo",
      bundleClass: "publication_candidate",
      dependencyClassificationRegister: {{
        normalized_package: "classified",
        policy_bundle: "classified",
        model_bundle: "classified",
        config_bundle: "classified"
      }},
      targetEnvironment: "production",
      requestedBy: "codex",
      requestedAtUtc: {json.dumps(requested_at)},
      assessmentRuleSetId: "assessment-rules-v1",
      followupDesiredStatus: "deferred",
      mode: "snapshot",
      triggerSource: "step1_admin_refresh_snapshot_readonly_proof"
    }},
    {{
      executionMode: "readonly",
      proofStorePath,
      workspaceRoot: repoRoot
    }}
  );

  const store = await schema.readStep1ProofStore(proofStorePath);
  const runRow = store.runtime_refresh_runs.find((row) => row.run_id === result.runId) || null;
  const phaseRows = store.runtime_refresh_run_phases
    .filter((row) => row.run_id === result.runId)
    .sort((left, right) => left.phase_name.localeCompare(right.phase_name));
  const activePointer = schema.selectStep1ActivePublicationPointerRow(store, "production");
  const deferredFollowup = store.deferred_followup_jobs.find((row) => row.run_id === result.runId) || null;
  const cutoverPublicationState = await publicationState.loadCanonicalPublicationState({{
    snapshot: {{
      available: true,
      runId: result.runId,
      generatedAtUtc: null,
    }},
    quote: {{
      available: true,
      runId: result.runId,
    }},
  }});
  const cutoverServingBundleMeta = await runtimePublicationBundle.loadServingRuntimePublicationBundleMeta();
  const legacyRuntimeValidityMirror = runRow
    ? {{
        validation_status: Object.prototype.hasOwnProperty.call(runRow, "validation_status") ? runRow.validation_status ?? null : null,
        snapshot_publication_id: Object.prototype.hasOwnProperty.call(runRow, "snapshot_publication_id") ? runRow.snapshot_publication_id ?? null : null,
        quote_publication_id: Object.prototype.hasOwnProperty.call(runRow, "quote_publication_id") ? runRow.quote_publication_id ?? null : null,
        quote_binding_status: Object.prototype.hasOwnProperty.call(runRow, "quote_binding_status") ? runRow.quote_binding_status ?? null : null,
        is_active_publication: Object.prototype.hasOwnProperty.call(runRow, "is_active_publication") ? runRow.is_active_publication ?? null : null,
      }}
    : null;

  fs.writeFileSync(harnessResultPath, JSON.stringify({{
    result,
    runRow,
    phaseRows,
    activePointer,
    deferredFollowup,
    cutoverPublicationState,
    cutoverServingBundleMeta,
    legacyRuntimeValidityMirror,
    requestArtifactExists: fs.existsSync(result.requestArtifactPath),
    candidateManifestExists: fs.existsSync(result.candidateBundleManifestPath),
    assessmentReportExists: fs.existsSync(result.assessmentReportPath),
    publicationManifestExists: fs.existsSync(result.publicationManifestPath),
    followupTicketExists: fs.existsSync(result.followupTicketPath)
  }}, null, 2) + "\\n");
}}

main().catch((error) => {{
  fs.writeFileSync(harnessResultPath, JSON.stringify({{
    error: error instanceof Error ? error.message : String(error)
  }}, null, 2) + "\\n");
  process.exitCode = 1;
}});
"""
    write_text(paths.step1_harness_path, harness)


def run_route_harness(paths: Paths) -> dict[str, object]:
    env = os.environ.copy()
    env["NODE_PATH"] = os.pathsep.join([str(paths.temp_root / "node_modules"), str(WEB_ROOT / "node_modules")])
    subprocess.run(
        ["node", str(paths.route_harness_path)],
        cwd=str(paths.temp_root),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(paths.route_harness_result_path.read_text(encoding="utf-8"))


def run_step1_harness(paths: Paths) -> dict[str, object]:
    env = os.environ.copy()
    env["NODE_PATH"] = os.pathsep.join([str(paths.temp_root / "node_modules"), str(WEB_ROOT / "node_modules")])
    subprocess.run(
        ["node", str(paths.step1_harness_path)],
        cwd=str(REPO_ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(paths.step1_harness_result_path.read_text(encoding="utf-8"))


def build_route_runtime_proof(harness_result: dict[str, object]) -> dict[str, object]:
    if "error" in harness_result:
        raise AssertionError(f"Enabled snapshot route harness failed: {harness_result['error']}")
    response_payload = harness_result.get("responsePayload")
    capture = harness_result.get("capture")
    if not isinstance(response_payload, dict):
        raise AssertionError("Enabled snapshot route harness did not return a JSON payload.")
    if not isinstance(capture, dict):
        raise AssertionError("Enabled snapshot route harness did not capture orchestrator calls.")

    resolution_calls = capture.get("resolutionCalls")
    dispatch_calls = capture.get("dispatchCalls")
    if not isinstance(resolution_calls, list) or len(resolution_calls) != 1:
        raise AssertionError("Enabled snapshot route harness did not resolve exactly one Step 1 cutover input.")
    if not isinstance(dispatch_calls, list) or len(dispatch_calls) != 1:
        raise AssertionError("Enabled snapshot route harness did not dispatch exactly one orchestrator call.")
    if harness_result.get("spawnCallCount") != 0:
        raise AssertionError("Enabled snapshot route harness still reached child_process.spawn for Step 1.")

    resolution_call = resolution_calls[0]
    dispatch_call = dispatch_calls[0]
    if not isinstance(resolution_call, dict) or not isinstance(dispatch_call, dict):
        raise AssertionError("Enabled snapshot route harness captured malformed orchestrator calls.")
    if response_payload.get("dispatchPath") != "step1_orchestrator":
        raise AssertionError("Enabled snapshot route harness did not report the Step 1 orchestrator dispatch path.")
    if response_payload.get("requestedMode") != "snapshot":
        raise AssertionError("Enabled snapshot route harness did not stay on the existing snapshot request path.")
    if response_payload.get("legacyRunnerDispatched") is not False:
        raise AssertionError("Enabled snapshot route harness reported a legacy Step 1 runner dispatch.")
    if response_payload.get("step1Cutover") is not True:
        raise AssertionError("Enabled snapshot route harness did not mark the request as Step 1 cutover.")
    if response_payload.get("step1ContractSource") != "env_contract":
        raise AssertionError("Enabled snapshot route harness did not use the explicit env contract for the existing request path.")
    if resolution_call.get("requestedMode") != "snapshot":
        raise AssertionError("Enabled snapshot route harness resolved the wrong requested mode.")
    resolved_input = resolution_call.get("resolvedInput")
    dispatched_input = dispatch_call.get("input")
    if not isinstance(resolved_input, dict) or not isinstance(dispatched_input, dict):
        raise AssertionError("Enabled snapshot route harness did not capture resolved/dispatched input payloads.")
    if resolved_input.get("mode") != "snapshot" or dispatched_input.get("mode") != "snapshot":
        raise AssertionError("Enabled snapshot route harness did not dispatch the existing snapshot Step 1 mode.")
    if dispatched_input.get("normalizedPackageId") != "normalized-package-demo":
        raise AssertionError("Enabled snapshot route harness did not dispatch the accepted Step 1 contract values.")
    return {
        "request_path": "POST /api/admin/refresh body={mode:snapshot}",
        "cutover_mode": "enabled",
        "response_status": harness_result.get("responseStatus"),
        "dispatch_path": response_payload.get("dispatchPath"),
        "requested_mode": response_payload.get("requestedMode"),
        "step1_contract_source": response_payload.get("step1ContractSource"),
        "legacy_runner_dispatched": response_payload.get("legacyRunnerDispatched"),
        "python_spawn_call_count": harness_result.get("spawnCallCount"),
        "orchestrator_resolution_call_count": len(resolution_calls),
        "orchestrator_dispatch_call_count": len(dispatch_calls),
        "resolved_input_mode": resolved_input.get("mode"),
        "dispatched_input_mode": dispatched_input.get("mode"),
    }


def build_step1_runtime_proof(harness_result: dict[str, object], proof_store_path: Path) -> dict[str, object]:
    if "error" in harness_result:
        raise AssertionError(f"Readonly Step 1 orchestrator harness failed: {harness_result['error']}")
    result = harness_result.get("result")
    run_row = harness_result.get("runRow")
    phase_rows = harness_result.get("phaseRows")
    active_pointer = harness_result.get("activePointer")
    deferred_followup = harness_result.get("deferredFollowup")
    cutover_publication_state = harness_result.get("cutoverPublicationState")
    cutover_serving_bundle_meta = harness_result.get("cutoverServingBundleMeta")
    legacy_runtime_validity_mirror = harness_result.get("legacyRuntimeValidityMirror")
    if not isinstance(result, dict):
        raise AssertionError("Readonly Step 1 harness did not return an orchestrator result.")
    if not isinstance(run_row, dict):
        raise AssertionError("Readonly Step 1 harness did not persist a runtime_refresh_runs row.")
    if not isinstance(phase_rows, list):
        raise AssertionError("Readonly Step 1 harness did not persist runtime_refresh_run_phases rows.")
    if not isinstance(active_pointer, dict):
        raise AssertionError("Readonly Step 1 harness did not persist an active publication pointer row.")
    if not isinstance(deferred_followup, dict):
        raise AssertionError("Readonly Step 1 harness did not persist a deferred follow-up row.")
    if not isinstance(cutover_publication_state, dict):
        raise AssertionError("Readonly Step 1 harness did not resolve canonical publication state under cutover.")
    if not isinstance(cutover_serving_bundle_meta, dict):
        raise AssertionError("Readonly Step 1 harness did not resolve serving publication bundle metadata under cutover.")
    if not isinstance(legacy_runtime_validity_mirror, dict):
        raise AssertionError("Readonly Step 1 harness did not capture legacy runtime validity mirror fields.")

    phase_names = [str(row.get("phase_name")) for row in phase_rows if isinstance(row, dict)]
    required_phases = ["candidate_build", "assessment_gate", "publication_commit", "quote_cache_refresh"]
    missing_phases = [name for name in required_phases if name not in phase_names]
    if missing_phases:
        raise AssertionError(f"Readonly Step 1 harness is missing phases: {missing_phases}")
    if result.get("executionPath") != "step1_orchestrator":
        raise AssertionError("Readonly Step 1 harness did not execute through the orchestrator.")
    if result.get("followupStatus") not in {"deferred", "launched"}:
        raise AssertionError("Readonly Step 1 harness did not reach a successful follow-up ticket outcome.")
    if run_row.get("mode") != "snapshot":
        raise AssertionError("Readonly Step 1 harness did not persist snapshot mode for the existing Step 1 path.")
    if active_pointer.get("publication_bundle_id") != result.get("publicationBundleId"):
        raise AssertionError("Readonly Step 1 harness active pointer does not match the committed publication bundle.")
    if deferred_followup.get("publication_bundle_id") != result.get("publicationBundleId"):
        raise AssertionError("Readonly Step 1 harness follow-up row does not match the committed publication bundle.")
    if run_row.get("report_status") != "ok":
        raise AssertionError("Readonly Step 1 harness did not finalize runtime_refresh_runs as an operator-summary success row.")
    if run_row.get("completed_at") in {None, ""}:
        raise AssertionError("Readonly Step 1 harness did not finalize runtime_refresh_runs.completed_at.")
    if run_row.get("current_phase") != "quote_cache_refresh":
        raise AssertionError("Readonly Step 1 harness did not mirror the deferred follow-up phase onto runtime_refresh_runs.")
    if run_row.get("current_phase_process_status") != result.get("followupStatus"):
        raise AssertionError("Readonly Step 1 harness did not mirror the follow-up status onto runtime_refresh_runs.")
    if run_row.get("activation_state") != "activated" or run_row.get("serving_state") != "allowed":
        raise AssertionError("Readonly Step 1 harness did not finalize mirror activation/serving summary fields.")
    if cutover_publication_state.get("activationState") != "activated":
        raise AssertionError("Cutover canonical publication state did not activate from active_publication_pointer.")
    if cutover_publication_state.get("servingState") != "allowed":
        raise AssertionError("Cutover canonical publication state did not allow serving from pointer-owned truth.")
    if cutover_publication_state.get("candidateValid") is not True:
        raise AssertionError("Cutover canonical publication state still requires legacy runtime validity fields.")
    if cutover_publication_state.get("runId") != result.get("runId"):
        raise AssertionError("Cutover canonical publication state resolved the wrong active run.")
    if cutover_publication_state.get("snapshotPublicationId") != result.get("publicationBundleId"):
        raise AssertionError("Cutover canonical publication state did not derive publication identity from publication_bundles.")
    if cutover_publication_state.get("quotePublicationId") != result.get("publicationBundleId"):
        raise AssertionError("Cutover canonical publication state did not mirror the pointer-owned publication identity.")
    if cutover_publication_state.get("quoteBindingStatus") != "aligned":
        raise AssertionError("Cutover canonical publication state did not derive aligned validity from Step 1 authorities.")
    if cutover_serving_bundle_meta.get("runId") != result.get("runId"):
        raise AssertionError("Cutover serving bundle metadata resolved the wrong active run.")
    if cutover_serving_bundle_meta.get("validationStatus") != "pass":
        raise AssertionError("Cutover serving bundle metadata did not derive pass validity from assessment/publication truth.")
    if cutover_serving_bundle_meta.get("snapshotPublicationId") != result.get("publicationBundleId"):
        raise AssertionError("Cutover serving bundle metadata did not resolve the pointer-owned publication bundle id.")
    if cutover_serving_bundle_meta.get("quoteBindingStatus") != "aligned":
        raise AssertionError("Cutover serving bundle metadata did not derive aligned validity from Step 1 authorities.")
    if cutover_serving_bundle_meta.get("activeRuntimeBundleValid") is not True:
        raise AssertionError("Cutover serving bundle metadata still requires legacy runtime validity fields.")
    if legacy_runtime_validity_mirror.get("validation_status") is not None:
        raise AssertionError("Readonly Step 1 harness unexpectedly required runtime_refresh_runs.validation_status.")
    if legacy_runtime_validity_mirror.get("snapshot_publication_id") is not None:
        raise AssertionError("Readonly Step 1 harness unexpectedly required runtime_refresh_runs.snapshot_publication_id.")
    if legacy_runtime_validity_mirror.get("quote_publication_id") is not None:
        raise AssertionError("Readonly Step 1 harness unexpectedly required runtime_refresh_runs.quote_publication_id.")
    if legacy_runtime_validity_mirror.get("quote_binding_status") is not None:
        raise AssertionError("Readonly Step 1 harness unexpectedly required runtime_refresh_runs.quote_binding_status.")
    if legacy_runtime_validity_mirror.get("is_active_publication") not in {None, False}:
        raise AssertionError("Readonly Step 1 harness unexpectedly required runtime_refresh_runs.is_active_publication.")
    for key in [
        "requestArtifactExists",
        "candidateManifestExists",
        "assessmentReportExists",
        "publicationManifestExists",
        "followupTicketExists",
    ]:
        if harness_result.get(key) is not True:
            raise AssertionError(f"Readonly Step 1 harness is missing expected artifact: {key}")
    return {
        "proof_store_path": str(proof_store_path),
        "run_id": result.get("runId"),
        "runtime_refresh_runs_mode": run_row.get("mode"),
        "runtime_refresh_runs_report_status": run_row.get("report_status"),
        "runtime_refresh_runs_completed_at": run_row.get("completed_at"),
        "runtime_refresh_runs_current_phase": run_row.get("current_phase"),
        "runtime_refresh_runs_current_phase_process_status": run_row.get("current_phase_process_status"),
        "execution_path": result.get("executionPath"),
        "legacy_step1_path_status": result.get("legacyStep1PathStatus"),
        "legacy_runner_dispatched": result.get("legacyRunnerDispatched"),
        "followup_status": result.get("followupStatus"),
        "phase_names": phase_names,
        "publication_bundle_id": result.get("publicationBundleId"),
        "followup_job_id": result.get("followupJobId"),
        "cutover_publication_state": cutover_publication_state,
        "cutover_serving_bundle_meta": cutover_serving_bundle_meta,
        "legacy_runtime_validity_mirror": legacy_runtime_validity_mirror,
        "request_artifact_path": result.get("requestArtifactPath"),
        "candidate_bundle_manifest_path": result.get("candidateBundleManifestPath"),
        "assessment_report_path": result.get("assessmentReportPath"),
        "publication_manifest_path": result.get("publicationManifestPath"),
        "followup_ticket_path": result.get("followupTicketPath"),
    }


def build_artifact(paths: Paths, now: datetime) -> dict[str, object]:
    write_route_typecheck_tsconfig(paths)
    write_route_runtime_tsconfig(paths)
    write_step1_runtime_tsconfig(paths)
    run_tsc(paths.route_typecheck_tsconfig_path)
    run_tsc(paths.route_runtime_tsconfig_path)
    run_tsc(paths.step1_runtime_tsconfig_path)
    route_source_proof = build_route_source_proof()
    write_route_runtime_stubs(paths)
    write_route_harness(paths)
    route_harness_result = run_route_harness(paths)
    route_runtime_proof = build_route_runtime_proof(route_harness_result)
    write_step1_runtime_aliases(paths)
    write_step1_harness(paths, now)
    step1_harness_result = run_step1_harness(paths)
    readonly_execution_proof = build_step1_runtime_proof(step1_harness_result, paths.proof_store_path)
    return {
        "proof_generated_at_utc": iso_z(utc_now()),
        "proof_status": "ok",
        "proof_scope": "step1_cutover_authority_repair_readonly",
        "route_source_proof": route_source_proof,
        "route_enabled_snapshot_seam_proof": route_runtime_proof,
        "readonly_orchestrator_execution_proof": readonly_execution_proof,
    }


def main() -> int:
    now = utc_now()
    paths = build_paths(now)
    try:
        artifact = build_artifact(paths, now)
        write_json(paths.artifact_path, artifact)
    except Exception as error:  # noqa: BLE001
        write_json(
            paths.artifact_path,
            {
                "proof_generated_at_utc": iso_z(utc_now()),
                "proof_status": "error",
                "proof_scope": "step1_cutover_authority_repair_readonly",
                "error": str(error),
            },
        )
        print(str(paths.artifact_path))
        return 1

    print(str(paths.artifact_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
