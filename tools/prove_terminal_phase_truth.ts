import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import {
  buildTerminalFailurePhaseTruthReconciliation,
  type RefreshPhaseLedgerTruthRow,
  type RunCurrentPhaseMirrorTruth,
} from "../web/src/lib/refresh-terminal-truth";

type ScenarioResult = {
  name: string;
  reconciliation: ReturnType<typeof buildTerminalFailurePhaseTruthReconciliation>;
  before: {
    phaseRows: RefreshPhaseLedgerTruthRow[];
    currentPhase: RunCurrentPhaseMirrorTruth;
  };
  after: {
    phaseRows: RefreshPhaseLedgerTruthRow[];
    currentPhase: RunCurrentPhaseMirrorTruth;
  };
  checks: Record<string, boolean>;
};

function utcStamp(): string {
  return new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
}

function clonePhaseRows(rows: RefreshPhaseLedgerTruthRow[]): RefreshPhaseLedgerTruthRow[] {
  return rows.map((row) => ({
    ...row,
    input_contract: row.input_contract ? { ...row.input_contract } : row.input_contract,
    output_contract: row.output_contract ? { ...row.output_contract } : row.output_contract,
  }));
}

function applyReconciliation(params: {
  phaseRows: RefreshPhaseLedgerTruthRow[];
  currentPhase: RunCurrentPhaseMirrorTruth;
  reconciliation: ReturnType<typeof buildTerminalFailurePhaseTruthReconciliation>;
}): {
  phaseRows: RefreshPhaseLedgerTruthRow[];
  currentPhase: RunCurrentPhaseMirrorTruth;
} {
  const phaseRows = clonePhaseRows(params.phaseRows);
  const currentPhase = { ...params.currentPhase };
  const reconciliation = params.reconciliation;

  if (!reconciliation.shouldPersist || !reconciliation.phaseName || !reconciliation.processStatus) {
    return { phaseRows, currentPhase };
  }

  const existingIndex = phaseRows.findIndex((row) => row.phase_name === reconciliation.phaseName);
  const nextPhaseRow: RefreshPhaseLedgerTruthRow = {
    phase_name: reconciliation.phaseName,
    input_contract: reconciliation.inputContract,
    process_status: reconciliation.processStatus,
    output_contract: reconciliation.outputContract,
    failure_code: reconciliation.failureCode,
    failure_detail: reconciliation.failureDetail,
    started_at: reconciliation.startedAtIso,
    completed_at: reconciliation.completedAtIso,
    last_heartbeat_at: reconciliation.lastHeartbeatAtIso,
  };

  if (existingIndex >= 0) {
    phaseRows[existingIndex] = nextPhaseRow;
  } else {
    phaseRows.push(nextPhaseRow);
  }

  currentPhase.current_phase = reconciliation.phaseName;
  currentPhase.current_phase_process_status = reconciliation.processStatus;
  currentPhase.current_phase_started_at = reconciliation.startedAtIso;
  currentPhase.current_phase_completed_at = reconciliation.completedAtIso;
  currentPhase.current_phase_last_heartbeat_at = reconciliation.lastHeartbeatAtIso;
  currentPhase.current_phase_failure_code = reconciliation.failureCode;
  currentPhase.current_phase_failure_detail = reconciliation.failureDetail;

  return { phaseRows, currentPhase };
}

function anyRunningSnapshotRebuild(rows: RefreshPhaseLedgerTruthRow[]): boolean {
  return rows.some((row) => row.phase_name === "snapshot_rebuild" && row.process_status === "running");
}

function scenarioRunningPhaseForcedFailed(): ScenarioResult {
  const beforePhaseRows: RefreshPhaseLedgerTruthRow[] = [
    {
      phase_name: "snapshot_rebuild",
      input_contract: { mode: "snapshot" },
      process_status: "running",
      output_contract: { status: "running" },
      failure_code: null,
      failure_detail: null,
      started_at: "2026-03-14T23:28:00.000Z",
      completed_at: null,
      last_heartbeat_at: "2026-03-14T23:31:57.822Z",
    },
  ];
  const beforeCurrentPhase: RunCurrentPhaseMirrorTruth = {
    current_phase: "snapshot_rebuild",
    current_phase_process_status: "running",
    current_phase_started_at: "2026-03-14T23:28:00.000Z",
    current_phase_completed_at: null,
    current_phase_last_heartbeat_at: "2026-03-14T23:31:57.822Z",
    current_phase_failure_code: null,
    current_phase_failure_detail: null,
  };
  const reconciliation = buildTerminalFailurePhaseTruthReconciliation({
    phaseRows: beforePhaseRows,
    currentPhase: beforeCurrentPhase,
    completedAtIso: "2026-03-14T23:32:20.360Z",
    failureCode: "RUN_TERMINAL_ERROR_LEFT_ACTIVE_PHASE_NON_TERMINAL",
    failureDetail: "Refresh terminalized error while snapshot_rebuild remained running.",
    contextLabel: "proof_running_phase_forced_failed",
  });
  const after = applyReconciliation({
    phaseRows: beforePhaseRows,
    currentPhase: beforeCurrentPhase,
    reconciliation,
  });
  const snapshotRow = after.phaseRows.find((row) => row.phase_name === "snapshot_rebuild");
  return {
    name: "running_phase_forced_failed",
    reconciliation,
    before: {
      phaseRows: beforePhaseRows,
      currentPhase: beforeCurrentPhase,
    },
    after,
    checks: {
      reconciliation_requested_persist: reconciliation.shouldPersist,
      snapshot_rebuild_not_running_after_terminalization: !anyRunningSnapshotRebuild(after.phaseRows),
      snapshot_rebuild_failed_after_terminalization: snapshotRow?.process_status === "failed",
      current_phase_mirror_matches_phase_name: after.currentPhase.current_phase === snapshotRow?.phase_name,
      current_phase_mirror_matches_phase_status: after.currentPhase.current_phase_process_status === snapshotRow?.process_status,
      current_phase_failure_code_matches_phase_row: after.currentPhase.current_phase_failure_code === snapshotRow?.failure_code,
      current_phase_failure_detail_matches_phase_row: after.currentPhase.current_phase_failure_detail === snapshotRow?.failure_detail,
    },
  };
}

function scenarioMirrorResyncedToTerminalPhase(): ScenarioResult {
  const beforePhaseRows: RefreshPhaseLedgerTruthRow[] = [
    {
      phase_name: "snapshot_rebuild",
      input_contract: { mode: "snapshot" },
      process_status: "failed",
      output_contract: {
        status: "error",
        failure_code: "SNAPSHOT_REBUILD_FAILED",
        failure_detail: "RuntimeError: example failure",
      },
      failure_code: "SNAPSHOT_REBUILD_FAILED",
      failure_detail: "RuntimeError: example failure",
      started_at: "2026-03-14T23:28:00.000Z",
      completed_at: "2026-03-14T23:30:20.360Z",
      last_heartbeat_at: "2026-03-14T23:30:20.360Z",
    },
  ];
  const beforeCurrentPhase: RunCurrentPhaseMirrorTruth = {
    current_phase: "snapshot_rebuild",
    current_phase_process_status: "running",
    current_phase_started_at: "2026-03-14T23:28:00.000Z",
    current_phase_completed_at: null,
    current_phase_last_heartbeat_at: "2026-03-14T23:31:57.822Z",
    current_phase_failure_code: null,
    current_phase_failure_detail: null,
  };
  const reconciliation = buildTerminalFailurePhaseTruthReconciliation({
    phaseRows: beforePhaseRows,
    currentPhase: beforeCurrentPhase,
    completedAtIso: "2026-03-14T23:32:20.360Z",
    failureCode: "RUN_TERMINAL_ERROR_LEFT_ACTIVE_PHASE_NON_TERMINAL",
    failureDetail: "Refresh terminalized error while snapshot_rebuild remained running.",
    contextLabel: "proof_mirror_resync_to_terminal_child",
  });
  const after = applyReconciliation({
    phaseRows: beforePhaseRows,
    currentPhase: beforeCurrentPhase,
    reconciliation,
  });
  const snapshotRow = after.phaseRows.find((row) => row.phase_name === "snapshot_rebuild");
  return {
    name: "mirror_resynced_to_terminal_child",
    reconciliation,
    before: {
      phaseRows: beforePhaseRows,
      currentPhase: beforeCurrentPhase,
    },
    after,
    checks: {
      reconciliation_requested_persist: reconciliation.shouldPersist,
      snapshot_rebuild_terminal_status_preserved: snapshotRow?.process_status === "failed",
      current_phase_mirror_matches_phase_name: after.currentPhase.current_phase === snapshotRow?.phase_name,
      current_phase_mirror_matches_phase_status: after.currentPhase.current_phase_process_status === snapshotRow?.process_status,
      current_phase_failure_code_matches_phase_row: after.currentPhase.current_phase_failure_code === snapshotRow?.failure_code,
      current_phase_failure_detail_matches_phase_row: after.currentPhase.current_phase_failure_detail === snapshotRow?.failure_detail,
      no_running_phase_left_after_resync: !after.phaseRows.some((row) => row.process_status === "running"),
    },
  };
}

function main(): number {
  const repoRoot = process.cwd();
  const evidenceDir = path.join(repoRoot, "backups", "runtime", `terminal-phase-truth-proof-${utcStamp()}`);
  mkdirSync(evidenceDir, { recursive: true });

  const scenarios = [
    scenarioRunningPhaseForcedFailed(),
    scenarioMirrorResyncedToTerminalPhase(),
  ];
  const allChecksPassed = scenarios.every((scenario) => Object.values(scenario.checks).every(Boolean));

  for (const scenario of scenarios) {
    writeFileSync(
      path.join(evidenceDir, `${scenario.name}.json`),
      `${JSON.stringify(scenario, null, 2)}\n`,
      "utf-8",
    );
  }

  const summary = {
    generated_at_utc: new Date().toISOString(),
    status: allChecksPassed ? "pass" : "fail",
    proof: {
      no_terminal_run_leaves_snapshot_rebuild_running:
        scenarios[0]?.checks.snapshot_rebuild_not_running_after_terminalization ?? false,
      current_phase_mirror_matches_ledger_after_terminalization:
        Boolean(
          scenarios[0]?.checks.current_phase_mirror_matches_phase_status
          && scenarios[0]?.checks.current_phase_failure_code_matches_phase_row
          && scenarios[1]?.checks.current_phase_mirror_matches_phase_status
          && scenarios[1]?.checks.current_phase_failure_code_matches_phase_row,
        ),
    },
    scenarios: scenarios.map((scenario) => ({
      name: scenario.name,
      reconciliation_reason: scenario.reconciliation.reason,
      checks: scenario.checks,
      artifact_json: path.join(evidenceDir, `${scenario.name}.json`),
    })),
  };

  writeFileSync(path.join(evidenceDir, "summary.json"), `${JSON.stringify(summary, null, 2)}\n`, "utf-8");
  console.log(path.join(evidenceDir, "summary.json"));
  return allChecksPassed ? 0 : 1;
}

process.exit(main());
